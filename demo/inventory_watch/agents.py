"""庫存異常日報的 agent 定義。

    （Python 規則引擎先算完異常，見 warehouse.py）
              ↓  digest() 壓成一段文字
    report_agent      判讀：今天最該處理的三件事，為什麼
              ↓  output_key="daily_report"
    action_agent      對前幾條異常查細節、擬補貨單（FunctionTool）
              ↓  output_key="action_plan"

只有兩個 agent，因為這個應用的重點本來就不在多 agent，而在**分界線畫在哪**：
數字全部在進入 agent 之前就算完了，模型拿到的是結論，不是原始資料。
"""

from __future__ import annotations

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from shared import get_model
from shared.config import Settings
from warehouse import draft_restock_order, get_sku_detail

AGENT_META = {
    "report_agent": {"icon": "📊", "title": "日報判讀", "color": "#3498DB"},
    "action_agent": {"icon": "🛒", "title": "行動建議", "color": "#27AE60"},
}


def build_pipeline(settings: Settings) -> SequentialAgent:
    """組出 判讀 → 行動 的日報流程。"""

    report_agent = LlmAgent(
        name="report_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是電商營運主管的助理。使用者會給你一份**已經算好的**庫存異常清單。\n\n"
            "寫一份今天的庫存日報，用繁體中文，結構如下：\n"
            "## 今天最該處理的三件事\n"
            "  每件一段：發生什麼、為什麼急、不處理會怎樣。要引用清單上的數字。\n"
            "## 可以先放著的\n"
            "  一句話帶過其餘異常，說明為什麼可以晚點再說。\n\n"
            "規則：\n"
            "- **只能用清單上出現的數字**，不要自己算新的、更不要估計。\n"
            "- 排序看「影響金額」與「嚴重度」，但你可以說明為什麼某條該提前。\n"
            "- 不要複述整份清單，主管要的是判斷，不是清單的翻譯。\n"
            "- 全文 350 字以內。"
        ),
        output_key="daily_report",
    )

    action_agent = LlmAgent(
        name="action_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是採購助理。以下是今天的庫存日報：\n\n{daily_report}\n\n"
            "針對日報點名的前 2~3 個 SKU，做這幾件事：\n"
            "1. **呼叫 get_sku_detail 工具**確認該 SKU 的實際數字"
            "（不要憑日報的敘述就下單）。\n"
            "2. 判斷需不需要補貨；需要的話**呼叫 draft_restock_order 工具**"
            "開一張補貨草稿，數量抓「補到約 30 天可售」。\n"
            "3. 平台數量不一致這類問題不需要補貨，改成寫一句要人去做的動作。\n\n"
            "最後用繁體中文列出一份『今天要做的事』清單，每條格式：\n"
            "`- [SKU] 動作 → 預期結果`\n"
            "補貨草稿要標明數量與預估金額。全文 250 字以內。"
        ),
        tools=[
            FunctionTool(func=get_sku_detail),
            FunctionTool(func=draft_restock_order),
        ],
        output_key="action_plan",
    )

    return SequentialAgent(
        name="inventory_pipeline",
        sub_agents=[report_agent, action_agent],
        description="異常判讀 → 行動建議",
    )


def build_request(digest_text: str, totals: dict) -> str:
    """組出送進 pipeline 的第一句話：一份算好的異常摘要。

    這裡送的是**結論**（27 條異常、影響金額多少、前 12 條是什麼），不是
    12 個 SKU 的完整明細。原始資料留在 Python 這側，模型要細節時再用工具查。
    """
    return (
        f"今天的庫存盤點結果：\n"
        f"- 監控 SKU：{totals['sku_count']} 個\n"
        f"- 偵測到異常：{totals['anomaly_count']} 條（其中嚴重度 4 以上：{totals['critical_count']} 條）\n"
        f"- 預估影響金額：NT$ {totals['impact_twd']:,}\n"
        f"- 目前庫存總成本：NT$ {totals['stock_value']:,}\n\n"
        f"異常清單（已依嚴重度與影響金額排序）：\n{digest_text}"
    )
