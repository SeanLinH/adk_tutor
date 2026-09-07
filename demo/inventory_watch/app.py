"""多平台庫存異常監控日報 — Python 算數字、LLM 做判讀。

跑法：streamlit run demo/inventory_watch/app.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent.parent
for _p in (str(PROJECT_ROOT), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from google.genai import types

from agents import AGENT_META, build_pipeline, build_request
from demo.common import (
    STREAM,
    StreamPainter,
    make_runner,
    model_sidebar,
    render_card,
    render_tool_call,
    typing,
)
from shared import final_text
from shared.config import Settings
from warehouse import (
    PLATFORMS,
    days_of_cover,
    detect_anomalies,
    digest,
    load_snapshot,
    set_current_snapshot,
    totals,
)

APP_NAME = "inventory_watch"
STAGES = ["report_agent", "action_agent"]

KIND_ICON = {
    "賣超": "🔴", "平台數量不一致": "🟠", "斷貨風險": "🟡",
    "呆滯庫存": "🔵", "庫存過高": "🟣",
}


def card(placeholder, agent_name: str, status: str, body: str = ""):
    meta = AGENT_META[agent_name]
    render_card(
        placeholder, icon=meta["icon"], title=meta["title"], color=meta["color"],
        status=status, body=body, min_height=240,
    )


async def run_pipeline_live(settings: Settings, request: str, placeholders: dict,
                            tool_box) -> dict:
    """跑一次日報流程。回傳兩段輸出，UI 再組成可下載的日報。"""
    runner, session_id = await make_runner(build_pipeline(settings), APP_NAME)

    card(placeholders["report_agent"], "report_agent", "running")
    card(placeholders["action_agent"], "action_agent", "waiting")

    msg = types.Content(role="user", parts=[types.Part(text=request)])
    painter = StreamPainter()
    texts: dict[str, str] = {}

    async for ev in runner.run_async(user_id="user", session_id=session_id,
                                     new_message=msg, run_config=STREAM):
        if getattr(ev, "partial", False):
            live = painter.add(ev)
            if live is not None and ev.author in placeholders:
                card(placeholders[ev.author], ev.author, "running", typing(live))
            continue

        # 只在非 partial 事件收工具呼叫：串流下同一個 call 會出現兩次。
        for call in ev.get_function_calls():
            with tool_box:
                render_tool_call(st.empty(), author=ev.author, tool_name=call.name,
                                 args=dict(call.args or {}))
        if not ev.is_final_response():
            continue
        text = final_text(ev)
        if not text or ev.author not in placeholders:
            continue
        texts[ev.author] = text
        card(placeholders[ev.author], ev.author, "done", text)
        painter.reset(ev.author)
        if ev.author == "report_agent":
            card(placeholders["action_agent"], "action_agent", "running")

    return texts


# ─── Streamlit UI ───────────────────────────────────────────────────

st.set_page_config(page_title="庫存異常監控日報", page_icon="📦", layout="wide")

st.title("📦 多平台庫存異常監控日報")
st.caption(
    "規則引擎（純 Python）先算出異常 → ADK `SequentialAgent` 判讀並產出行動建議。"
    "**模型不算數字，只解釋數字。**"
)

with st.sidebar:
    st.header("⚙️ 設定")
    settings = model_sidebar(key_prefix="inv_")

    st.subheader("🎲 資料快照")
    seed = st.number_input(
        "隨機種子", min_value=1, max_value=999, value=42,
        help="同一個種子一定產生同一份庫存資料；換一個就換一組異常組合。",
    )
    top_n = st.slider("送給模型的異常條數", 5, 20, 12,
                      help="送越多不代表越準——雜訊會稀釋判斷品質，也更花錢。")
    run_btn = st.button("▶️ 產出今日日報", type="primary", width="stretch")

# 資料與異常偵測都在畫面第一次載入時就跑完了——完全不需要模型。
rows = load_snapshot(int(seed))
set_current_snapshot(rows)
anomalies = detect_anomalies(rows)
stat = totals(rows, anomalies)

m = st.columns(5)
m[0].metric("監控 SKU", stat["sku_count"])
m[1].metric("異常條數", stat["anomaly_count"])
m[2].metric("嚴重（≥4）", stat["critical_count"])
m[3].metric("預估影響", f"NT$ {stat['impact_twd']:,}")
m[4].metric("庫存總成本", f"NT$ {stat['stock_value']:,}")

tab_anomaly, tab_stock = st.tabs(["🚨 異常清單（規則引擎產出）", "📋 庫存快照"])

with tab_anomaly:
    st.dataframe(
        [
            {
                "": KIND_ICON.get(a.kind, "⚪"),
                "類型": a.kind,
                "嚴重度": a.severity,
                "影響金額": a.impact_twd,
                "SKU": a.sku,
                "商品": a.name,
                "說明": a.detail,
            }
            for a in anomalies
        ],
        width="stretch", hide_index=True,
    )
    st.caption("這張表沒有經過任何模型——它是 `warehouse.detect_anomalies()` 的輸出。")

with tab_stock:
    st.dataframe(
        [
            {
                "SKU": r["sku"], "商品": r["name"], "類別": r["category"],
                "倉庫": r["on_hand"], "平台合計": r["listed_total"],
                **{p: r["listed"][p] for p in PLATFORMS},
                "待出貨": r["pending_orders"], "在途": r["in_transit"],
                "近7日銷量": r["sold_7d"],
                # 沒有銷量的 SKU 可售天數是無限大。這裡填 None（表格顯示空白）
                # 而不是「—」，否則整欄變成混合型別，Arrow 轉換會噴一整串警告。
                "可售天數": (
                    None if days_of_cover(r) == float("inf") else days_of_cover(r)
                ),
            }
            for r in rows
        ],
        width="stretch", hide_index=True,
    )

st.divider()
st.subheader("🤖 Agent 判讀")
cols = st.columns(2)
placeholders = {name: cols[i].empty() for i, name in enumerate(STAGES)}
for _n in STAGES:
    card(placeholders[_n], _n, "waiting")

st.subheader("🔧 工具呼叫軌跡")
tool_box = st.container()
st.caption("`action_agent` 不會照著日報的敘述就下單，它會自己查一次 SKU 細節再決定。")

if run_btn:
    digest_text = digest(anomalies, top_n=int(top_n))
    request = build_request(digest_text, stat)
    with st.expander("📨 送進 pipeline 的內容（注意：是結論，不是整個資料庫）"):
        st.code(request, language="text")

    texts = asyncio.run(run_pipeline_live(settings, request, placeholders, tool_box))

    if texts:
        report_md = (
            f"# 庫存日報 {date.today().isoformat()}\n\n"
            f"- 監控 SKU：{stat['sku_count']}　異常：{stat['anomaly_count']} 條"
            f"（嚴重 {stat['critical_count']} 條）\n"
            f"- 預估影響金額：NT$ {stat['impact_twd']:,}\n\n"
            f"{texts.get('report_agent', '')}\n\n"
            f"## 今天要做的事\n\n{texts.get('action_agent', '')}\n"
        )
        st.download_button(
            "📥 下載今日日報 markdown",
            data=report_md,
            file_name=f"inventory_{date.today().isoformat()}.md",
            mime="text/markdown",
        )
