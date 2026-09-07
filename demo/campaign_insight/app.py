"""檔期成效交叉分析 — 策略長諮詢三位分析師（single_turn sub-agent）。

跑法：streamlit run demo/campaign_insight/app.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent.parent
for _p in (str(PROJECT_ROOT), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from google.genai import types

from agents import AGENT_META, ANALYSTS, DEFAULT_QUESTION, build_team
from datasets import CAMPAIGN, raw_tables
from demo.common import (
    STREAM,
    StreamPainter,
    make_runner,
    model_sidebar,
    render_bubble,
    render_tool_call,
    typing,
)
from shared import final_text
from shared.config import Settings

APP_NAME = "campaign_insight"


USER_META = {"icon": "🙋", "title": "你", "color": "#888888"}


def bubble(container, author: str, body: str):
    meta = USER_META if author == "user" else AGENT_META.get(
        author, {"icon": "🤖", "title": author, "color": "#777"}
    )
    render_bubble(container, icon=meta["icon"], title=meta["title"],
                  color=meta["color"], body=body)


async def run_team_live(settings: Settings, question: str, log_box, trace_box) -> dict:
    """跑一次交叉分析，邊跑邊把「誰被問了、誰查了什麼」畫出來。

    因為三位分析師是 `mode="single_turn"` 的 sub-agent，它們跑在**同一個
    invocation** 裡，所以它們自己的工具呼叫也會出現在這個事件串流上。
    （若改用 `AgentTool`，子 agent 會在獨立的 runner 裡跑，這裡就只看得到
    一次工具呼叫跟一段回傳文字。）

    串流的氣泡跟前三個 demo 的卡片不一樣：卡片的位置是固定的，氣泡卻是
    「誰開口才長出一個」。所以這裡在某個 agent 送出第一個 partial 事件時
    才建立它的 placeholder，之後逐字更新同一個氣泡，講完再換下一個。
    """
    runner, session_id = await make_runner(build_team(settings), APP_NAME)

    with log_box:
        bubble(st.empty(), "user", question)

    msg = types.Content(role="user", parts=[types.Part(text=question)])
    painter = StreamPainter()
    live_bubbles: dict[str, Any] = {}
    consulted: list[str] = []
    final_answer = ""

    async for ev in runner.run_async(user_id="user", session_id=session_id,
                                     new_message=msg, run_config=STREAM):
        if getattr(ev, "partial", False):
            live = painter.add(ev)
            if live is None:
                continue
            if ev.author not in live_bubbles:
                with log_box:
                    live_bubbles[ev.author] = st.empty()
            bubble(live_bubbles[ev.author], ev.author, typing(live))
            continue

        # 只在非 partial 事件收工具呼叫：串流下同一個 call 會出現兩次。
        for call in ev.get_function_calls():
            if call.name in ANALYSTS:
                # 策略長「打電話問專家」——這是 single_turn sub-agent 的呼叫。
                consulted.append(call.name)
                meta = AGENT_META[call.name]
                req = str((call.args or {}).get("request", ""))[:80]
                with trace_box:
                    st.markdown(
                        f"<div style='font-size:12px;color:{meta['color']};margin:4px 0;'>"
                        f"🧭 ➔ {meta['icon']} <b>{meta['title']}</b><br/>"
                        f"<span style='color:#888'>「{req}…」</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                # 分析師自己查資料的工具呼叫
                with trace_box:
                    render_tool_call(st.empty(), author=ev.author, tool_name=call.name,
                                     args=dict(call.args or {}))

        text = final_text(ev)
        if not text:
            continue
        # 這一輪講完了：拿回串流時用的那個氣泡，換成完整內容（沒有游標）。
        placeholder = live_bubbles.pop(ev.author, None)
        if placeholder is None:
            with log_box:
                placeholder = st.empty()
        bubble(placeholder, ev.author, text)
        painter.reset(ev.author)
        if ev.author == "strategist":
            final_answer = text

    return {"consulted": consulted, "final": final_answer}


# ─── Streamlit UI ───────────────────────────────────────────────────

st.set_page_config(page_title="檔期成效交叉分析", page_icon="🧭", layout="wide")

st.title("🧭 檔期成效交叉分析")
st.caption(
    "ADK `sub_agents` + `mode=\"single_turn\"`：策略長把三位分析師**當工具呼叫**，"
    "問完控制權回到自己身上，再交叉比對出結論。"
)

with st.sidebar:
    st.header("⚙️ 設定")
    settings = model_sidebar(key_prefix="campaign_")

    st.subheader("❓ 你想問什麼")
    question = st.text_area("問題", DEFAULT_QUESTION, height=100)
    st.caption(f"資料範圍：{CAMPAIGN}")

    st.subheader("👥 團隊")
    for k, v in AGENT_META.items():
        st.markdown(
            f"<span style='color:{v['color']}'>{v['icon']} **{v['title']}**</span>",
            unsafe_allow_html=True,
        )

    run_btn = st.button("▶️ 開始分析", type="primary", width="stretch")

main_col, side_col = st.columns([3, 2])

with main_col:
    st.subheader("💬 分析過程")
    log_box = st.container()

with side_col:
    st.subheader("🔀 諮詢與查詢軌跡")
    trace_box = st.container()

st.divider()

with st.expander("📊 三份原始資料（可以自己核對 agent 有沒有講錯）", expanded=False):
    tables = raw_tables()
    t1, t2, t3 = st.tabs(["廣告", "銷售", "庫存"])
    with t1:
        st.dataframe(tables["廣告"], width="stretch", hide_index=True)
        st.caption("單看這張表：ROAS 4.0，會得到「加碼投放」的結論。")
    with t2:
        st.dataframe(tables["銷售"], width="stretch", hide_index=True)
        st.caption("單看這張表：營收成長，但平均折扣 32%、整體毛利率只剩 18%。")
    with t3:
        st.dataframe(tables["庫存"], width="stretch", hide_index=True)
        st.caption("單看這張表：賣最好的 SKU-1004 只剩 3.2 天可售，補貨要 21 天。")

if run_btn:
    if not question.strip():
        st.error("請先輸入問題")
    else:
        result = asyncio.run(run_team_live(settings, question.strip(), log_box, trace_box))
        n = len(set(result["consulted"]))
        if n == 3:
            st.success("三位分析師都問過了，結論是交叉比對出來的。")
        elif n > 0:
            st.warning(
                f"這一輪只問了 {n} 位分析師。這是「讓 LLM 自己決定要問誰」的真實代價——"
                "它有時候會覺得問一個就夠了。要保證每份資料都被看過，"
                "就得改用 `ParallelAgent` 把三份分析寫死成必經步驟"
                "（見 `demo/listing_studio/`）。"
            )
        if result["final"]:
            st.download_button(
                "📥 下載分析結論 markdown",
                data=f"# {CAMPAIGN} 成效分析\n\n**問題**：{question}\n\n{result['final']}\n",
                file_name="campaign_insight.md",
                mime="text/markdown",
            )
