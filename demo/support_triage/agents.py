"""客訴工單分流的 agent 定義。

    triage_agent      讀客訴原文 → **結構化** 工單（output_schema）
         ↓ output_key="triage"
    policy_agent      查訂單、查物流、查退貨政策（FunctionTool）
         ↓ output_key="policy_result"
    reply_agent       擬客服回覆草稿
         ↓ output_key="reply_draft"
    ── 到這裡 agent 的工作就結束了 ──
    needs_human_review()   純 Python 的閘門，決定草稿能不能直接寄出

三個 agent 各自對應一件事實：**分類要可被程式讀**、**查證要靠工具**、
**寫字才是 LLM 的強項**。硬把三件事塞進一個 agent 會得到一個「看起來
什麼都做了、但每件都做不深」的黑箱。
"""

from __future__ import annotations

from typing import Literal

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field

from shared import get_model
from shared.config import Settings
from tools import check_return_policy, check_shipping_status, lookup_order

AGENT_META = {
    "triage_agent": {"icon": "🏷️", "title": "工單分類", "color": "#9B59B6"},
    "policy_agent": {"icon": "📚", "title": "政策查證", "color": "#3498DB"},
    "reply_agent":  {"icon": "✍️", "title": "回覆草稿", "color": "#E67E22"},
}

TICKET_CATEGORIES = ("商品瑕疵", "尺寸不符", "物流延誤", "客服態度", "退換貨詢問", "其他")


class Triage(BaseModel):
    """工單分類結果。

    這個 schema 存在的理由：分類結果**下游要用程式讀**——`needs_human_review()`
    要看 urgency、UI 要看 category 上色。如果讓 agent 用自然語言回「我認為
    這比較緊急」，程式就得反過來用字串比對去猜它的意思，那是最脆弱的接法。
    """

    category: Literal[TICKET_CATEGORIES] = Field(description="工單類型")  # type: ignore[valid-type]
    urgency: Literal["高", "中", "低"] = Field(description="急迫度")
    order_id: str = Field(description="客訴中提到的訂單編號；沒提到就填空字串")
    mentions_authority: bool = Field(
        description="客戶是否提到消保官、申訴、爆料、法律途徑等升級訊號"
    )
    customer_emotion: str = Field(description="客戶情緒，10 字內")
    summary: str = Field(description="客訴重點摘要，40 字內")
    suggested_action: str = Field(description="建議處理方式，30 字內")


def build_pipeline(settings: Settings) -> SequentialAgent:
    """組出 分類 → 查證 → 擬稿 的工單處理流程。"""

    # output_schema 一設下去，這個 agent 就**不能有工具、也不能 transfer**——
    # ADK 的限制，因為它必須把整個回應變成一份 JSON。這反而逼出乾淨的分工：
    # 分類只做分類，要查資料是下一站的事。
    triage_agent = LlmAgent(
        name="triage_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是電商客服的工單分類員。讀客戶的訊息，判斷類型、急迫度、"
            "有沒有提到訂單編號、有沒有升級訊號（消保官／申訴／爆料／提告）。\n"
            "判斷急迫度的原則：\n"
            "- 高：安全疑慮、已經在生氣、提到申訴管道、時效性強（例如禮物要送人）\n"
            "- 中：有實質損失但語氣平和\n"
            "- 低：單純詢問，還沒有損失發生\n"
            "只輸出 JSON，不要多加任何說明文字。"
        ),
        output_schema=Triage,
        output_key="triage",
    )

    policy_agent = LlmAgent(
        name="policy_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是客服後台查證員。以下是這張工單的分類結果：\n\n{triage}\n\n"
            "請照這個順序查證：\n"
            "1. 若有訂單編號，**呼叫 lookup_order 工具**取得訂單詳情。\n"
            "2. 若工單類型跟物流有關，**呼叫 check_shipping_status 工具**。\n"
            "3. 若涉及退換貨或商品瑕疵，用訂單編號**呼叫 check_return_policy 工具**"
            "（天數與品類規則由工具自己算，你不要自己推算日期）。\n\n"
            "然後用繁體中文寫一段查證結論，必須包含：\n"
            "- 查到的事實（訂單金額、送達日期、狀態）\n"
            "- 依政策客戶「可以」得到什麼、「不能」得到什麼\n"
            "- 若查無訂單，直接說明查無並建議向客戶要編號\n"
            "**不要編造查不到的資料。**工具沒回傳的東西就說沒有。"
        ),
        tools=[
            FunctionTool(func=lookup_order),
            FunctionTool(func=check_shipping_status),
            FunctionTool(func=check_return_policy),
        ],
        output_key="policy_result",
    )

    reply_agent = LlmAgent(
        name="reply_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是資深客服，負責擬回覆草稿。\n\n"
            "【工單分類】\n{triage}\n\n"
            "【查證結論】\n{policy_result}\n\n"
            "寫一封給客戶的回覆，要求：\n"
            "- 繁體中文，150 字以內，稱謂用「您」\n"
            "- 開頭先同理客戶的處境，不要制式罐頭開場\n"
            "- 中間講**具體**能做什麼（依查證結論，不要加碼承諾）\n"
            "- 結尾給一個明確的下一步（例如：請提供照片／已為您查件，預計X天）\n"
            "- 政策不允許的事，要說清楚但語氣要軟\n"
            "只輸出信件內容本身，不要加「以下是草稿」這類前言。"
        ),
        output_key="reply_draft",
    )

    return SequentialAgent(
        name="support_pipeline",
        sub_agents=[triage_agent, policy_agent, reply_agent],
        description="客訴分類 → 政策查證 → 回覆草稿",
    )
