"""新品上架內容產線的 agent 定義。

架構（`SequentialAgent` 裡面包一個 `ParallelAgent`）：

    spec_agent            萃取賣點           ─┐ 一定要先跑完
                                              ↓  （後面三個都要吃它的輸出）
    ┌─────────── ParallelAgent ───────────┐
    │ seo_agent    desc_agent   social_agent │ 三路同時跑，彼此看不到對方
    └──────────────────┬─────────────────┘
                       ↓
    assemble_agent        組成上架包

為什麼中間那段要用 ParallelAgent 而不是繼續串 Sequential：
關鍵字、商品描述、社群貼文三件事**都只依賴賣點**，彼此沒有先後關係。
串成 Sequential 只是白白多等兩輪模型回應；而且後面的 agent 會看到前面的
輸出，反而容易寫出「三份內容長得很像」的結果。並行除了快，也保住了三個
視角的獨立性。

代價是：並行的分支之間**讀不到彼此的 output_key**（它們是同時開始的），
所以任何需要「A 的結果餵給 B」的關係，都必須拆到不同 stage。
"""

from __future__ import annotations

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

from shared import get_model
from shared.config import Settings

# UI 用的顯示資訊。key 對齊 agent name，事件串流回來時可以直接查表。
AGENT_META = {
    "spec_agent":     {"icon": "🔍", "title": "賣點分析",   "color": "#9B59B6"},
    "seo_agent":      {"icon": "🔑", "title": "SEO 關鍵字", "color": "#3498DB"},
    "desc_agent":     {"icon": "📝", "title": "商品描述",   "color": "#E67E22"},
    "social_agent":   {"icon": "📣", "title": "社群貼文",   "color": "#E84393"},
    "assemble_agent": {"icon": "📦", "title": "上架包整合", "color": "#27AE60"},
}

# 並行的那三個，UI 要同時把它們切成「執行中」
PARALLEL_AGENTS = ["seo_agent", "desc_agent", "social_agent"]


def build_pipeline(settings: Settings) -> SequentialAgent:
    """組出完整的上架內容產線。每次執行都重建，避免沿用上一輪的內部狀態。"""

    spec_agent = LlmAgent(
        name="spec_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是電商商品企劃。讀使用者提供的商品資料，整理出這個商品的\n"
            "1. **三個核心賣點**（每個一句話，要具體，不要『品質優良』這種空話）\n"
            "2. **目標客群**（一句話描述誰會買、為什麼買）\n"
            "3. **主要競品差異**（一句話）\n\n"
            "資料不足的地方就依商品類別做合理推斷，但要標註「（推斷）」。\n"
            "用繁體中文、條列式輸出，控制在 200 字以內。"
        ),
        output_key="selling_points",
    )

    # 三個分支都只讀 {selling_points}，彼此不互相參照——這是它們能並行的前提。
    seo_agent = LlmAgent(
        name="seo_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是電商 SEO 專員。根據以下賣點分析：\n\n{selling_points}\n\n"
            "產出：\n"
            "1. **8 個搜尋關鍵字**（台灣消費者實際會打的字，長短尾混合）\n"
            "2. **3 個商品標題**（各 30 字內，關鍵字前置，符合蝦皮/momo 的標題習慣）\n"
            "用繁體中文條列輸出，不要解釋你的思路。"
        ),
        output_key="seo_pack",
    )
    desc_agent = LlmAgent(
        name="desc_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是商品文案寫手。根據以下賣點分析：\n\n{selling_points}\n\n"
            "產出：\n"
            "1. **一段 150 字的商品描述**（先講痛點、再講解法、最後推一把）\n"
            "2. **5 條規格重點 bullet**（每條 20 字內）\n"
            "用繁體中文，語氣親切但不浮誇，不要用「震撼」「絕對」這類誇大詞。"
        ),
        output_key="desc_pack",
    )
    social_agent = LlmAgent(
        name="social_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是社群小編。根據以下賣點分析：\n\n{selling_points}\n\n"
            "產出：\n"
            "1. **一則 IG 貼文**（100 字內，開頭要能停住滑動的手）\n"
            "2. **一則 FB 貼文**（150 字內，可以多一點情境描述）\n"
            "3. **10 個 hashtag**\n"
            "用繁體中文，符合台灣社群語感。"
        ),
        output_key="social_pack",
    )

    content_squad = ParallelAgent(
        name="content_squad",
        sub_agents=[seo_agent, desc_agent, social_agent],
        description="關鍵字、商品描述、社群貼文三路並行產出。",
    )

    assemble_agent = LlmAgent(
        name="assemble_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是上架負責人。把以下三份素材整合成一份可以直接照著上架的\n"
            "**Markdown 上架包**：\n\n"
            "【SEO】\n{seo_pack}\n\n"
            "【描述】\n{desc_pack}\n\n"
            "【社群】\n{social_pack}\n\n"
            "格式要求：\n"
            "- 用 `## 商品標題（建議）` / `## 商品描述` / `## 規格重點` / "
            "`## 關鍵字` / `## 社群貼文` 五個區塊\n"
            "- 標題只留**最推薦的那一個**，並用一句話說明為什麼選它\n"
            "- 三份素材若有矛盾（例如描述講的賣點沒出現在關鍵字裡），"
            "在最後加一個 `## ⚠️ 待確認` 區塊指出來\n"
            "不要重新創作內容，你的工作是整合與挑選。"
        ),
        output_key="listing_pack",
    )

    return SequentialAgent(
        name="listing_pipeline",
        sub_agents=[spec_agent, content_squad, assemble_agent],
        description="賣點分析 → (SEO / 描述 / 社群 並行) → 上架包整合",
    )


def build_request(
    name: str, category: str, price: int, notes: str, platforms: list[str]
) -> str:
    """把表單欄位組成給 pipeline 的第一句話。

    刻意組成自然語言而不是 JSON：這條產線的第一站是 LLM，讓它讀人話比讀
    結構化欄位更貼近真實使用情境（賣家腦中的商品資訊本來就是散的）。
    """
    platform_text = "、".join(platforms) if platforms else "未指定"
    return (
        f"我要上架一個新商品。\n"
        f"商品名稱：{name}\n"
        f"類別：{category}\n"
        f"售價：NT$ {price}\n"
        f"上架平台：{platform_text}\n"
        f"我自己的筆記：{notes or '（無）'}"
    )
