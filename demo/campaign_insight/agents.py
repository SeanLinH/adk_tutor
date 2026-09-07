"""檔期成效交叉分析 —— 示範「把 agent 當工具呼叫」的協作方式。

                    strategist（營運策略／mode 預設 chat）
                          │  sub_agents，三個都是 mode="single_turn"
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
   ads_analyst      sales_analyst      stock_analyst
   get_ad_metrics   get_sales_metrics  get_stock_levels

ADK 有三種把 agent 接在一起的方式，差別只有一句話：**控制權會不會回來**。

| 寫法 | 呼叫後控制權 | 像什麼 |
|---|---|---|
| `sub_agents`（預設 `mode="chat"`）+ `transfer_to_agent` | **交出去，不回來** | 把案子轉給別的部門 |
| `sub_agents` + `mode="single_turn"` | 對方答完就**回到 caller** | 打電話問專家，掛掉繼續做自己的事 |
| `AgentTool(agent=...)` | 同上，但跑在**獨立的 runner/session** | 外包給另一家公司 |

這個應用要的是「問完三個分析師，自己交叉比對出結論」，所以用 single_turn。
`demo/app_coordination.py` 要的是「大綱寫完換寫手接手」，所以用 transfer。

為什麼不用 `AgentTool`：ADK 2.x 的 `AgentTool` docstring 已經明講
「Direct usage of AgentTool is discouraged」，建議改用 `mode="single_turn"`。
差別在 `AgentTool` 會另外開一個 Runner 與 session 去跑子 agent，子 agent 的
事件**不會**回到外層串流（畫面上只看得到一次工具呼叫與一段回傳文字）；
single_turn 則是用 `run_node` 跑在同一個 invocation 裡，所以三位分析師自己
呼叫了哪些工具，在畫面上是看得到的。
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from datasets import get_ad_metrics, get_sales_metrics, get_stock_levels
from shared import get_model
from shared.config import Settings

AGENT_META = {
    "strategist":    {"icon": "🧭", "title": "營運策略",   "color": "#9B59B6"},
    "ads_analyst":   {"icon": "📈", "title": "廣告分析師", "color": "#3498DB"},
    "sales_analyst": {"icon": "💰", "title": "銷售分析師", "color": "#E67E22"},
    "stock_analyst": {"icon": "📦", "title": "庫存分析師", "color": "#27AE60"},
}

ANALYSTS = ["ads_analyst", "sales_analyst", "stock_analyst"]

DEFAULT_QUESTION = "這波雙 11 檔期到底有沒有賺？接下來一週的廣告預算該怎麼調？"


def build_team(settings: Settings) -> LlmAgent:
    """組出 strategist + 三個分析師（以 single_turn sub-agent 的形式掛上去）。"""

    # 每個分析師只拿得到自己領域的工具。這個限制是設計的一部分：
    # 它們不可能「順便」評論別人的數字，跨領域的結論只能由 strategist 做。
    # description 很重要——它會變成 strategist 看到的工具說明，決定它什麼
    # 時候會想呼叫誰。
    ads_analyst = LlmAgent(
        name="ads_analyst",
        model=get_model(settings=settings),
        mode="single_turn",
        description="回答廣告投放成效問題：花費、CTR、CPC、CPA、ROAS、各渠道表現。",
        instruction=(
            "你是廣告投放分析師。**先呼叫 get_ad_metrics 工具**拿數據，再回答。\n"
            "回答要求：條列式、繁體中文、150 字以內，一定要附具體數字。\n"
            "只談廣告數據。銷售毛利、庫存不是你的領域，"
            "被問到就說「這要問銷售/庫存分析師」。"
        ),
        tools=[FunctionTool(func=get_ad_metrics)],
    )
    sales_analyst = LlmAgent(
        name="sales_analyst",
        model=get_model(settings=settings),
        mode="single_turn",
        description="回答銷售與獲利問題：營收、客單價、折扣、毛利率、主力 SKU、回購率。",
        instruction=(
            "你是銷售分析師。**先呼叫 get_sales_metrics 工具**拿數據，再回答。\n"
            "回答要求：條列式、繁體中文、150 字以內，一定要附具體數字。\n"
            "**務必點出毛利率與折扣的關係**，以及各 SKU 的毛利差異——"
            "營收成長不等於賺錢。只談銷售面，不要評論廣告或庫存。"
        ),
        tools=[FunctionTool(func=get_sales_metrics)],
    )
    stock_analyst = LlmAgent(
        name="stock_analyst",
        model=get_model(settings=settings),
        mode="single_turn",
        description="回答庫存問題：現有庫存、可售天數、在途補貨、補貨前置期。",
        instruction=(
            "你是庫存分析師。**先呼叫 get_stock_levels 工具**拿數據，再回答。\n"
            "回答要求：條列式、繁體中文、150 字以內，一定要附具體數字。\n"
            "**特別標出可售天數少於補貨前置期的 SKU**——那代表一定會斷貨。"
            "只談庫存，不要評論廣告成效。"
        ),
        tools=[FunctionTool(func=get_stock_levels)],
    )

    strategist = LlmAgent(
        name="strategist",
        model=get_model(settings=settings),
        instruction=(
            "你是電商營運負責人。你手上有三位專業分析師可以呼叫："
            "ads_analyst（廣告）、sales_analyst（銷售獲利）、stock_analyst（庫存）。\n\n"
            "回答使用者問題時，照這個順序做：\n"
            "1. **一定要把三位分析師都問過一次**（呼叫三個工具），"
            "不要只問一個就下結論。問的時候要說清楚你想知道什麼。\n"
            "2. 把三份回答**交叉比對**，特別注意彼此矛盾或互相牽動的地方，例如：\n"
            "   - ROAS 好看，但毛利率是否撐得住廣告費？\n"
            "   - 廣告在推的商品，庫存撐不撐得到補貨到貨？\n"
            "3. 用繁體中文輸出，結構如下：\n"
            "   ## 結論（一句話回答使用者的問題）\n"
            "   ## 交叉比對看到什麼（每點都要引用具體數字，並說明是哪兩份資料對照出來的）\n"
            "   ## 接下來一週怎麼做（3 個具體行動，含金額或數量）\n\n"
            "**只能使用分析師回報的數字，不要自己編造或推算新數字。**"
            "全文 400 字以內。"
        ),
        sub_agents=[ads_analyst, sales_analyst, stock_analyst],
    )
    return strategist
