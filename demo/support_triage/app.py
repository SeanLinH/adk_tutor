"""客訴工單分流 — Orchestration + 人工審核閘門。

跑法：streamlit run demo/support_triage/app.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent.parent
for _p in (str(PROJECT_ROOT), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from google.genai import types

from agents import AGENT_META, build_pipeline
from demo.common import (
    STREAM,
    StreamPainter,
    make_runner,
    model_sidebar,
    read_state,
    render_card,
    render_tool_call,
    typing,
)
from shared import final_text
from shared.config import Settings
from tools import ORDERS, days_since_delivery, needs_human_review

APP_NAME = "support_triage"
STAGES = ["triage_agent", "policy_agent", "reply_agent"]

SAMPLE_TICKETS = {
    "① 便宜商品、單純詢問（會自動放行）": (
        "你好，我上禮拜買的除濕包 SP-20250412 已經收到了，想問一下如果曬過之後"
        "還是沒恢復，可以換一包嗎？不急，謝謝。"
    ),
    "② 高價 3C 瑕疵（會擋下來）": (
        "訂單 MO-20250408 的耳機右耳完全沒聲音！！買快五千塊用不到三週就這樣，"
        "我已經拍照存證了，如果不處理我會去消保官那邊申訴。"
    ),
    "③ 物流延誤（中等急迫）": (
        "我的床包組 WB-20250420 到現在還沒收到，官網說運送中但已經好幾天了，"
        "這是要送人的禮物，週末就要用了，可以幫我查一下嗎？"
    ),
    "④ 查無訂單（缺事實，一定要人工）": (
        "上個月買的東西壞掉了要退，訂單編號我找不到，你們自己查一下我的名字就好，"
        "不然我去 Dcard 發文。"
    ),
}


def card(placeholder, agent_name: str, status: str, body: str = ""):
    meta = AGENT_META[agent_name]
    render_card(
        placeholder, icon=meta["icon"], title=meta["title"], color=meta["color"],
        status=status, body=body, min_height=200,
    )


async def run_pipeline_live(settings: Settings, ticket: str, placeholders: dict,
                            tool_box) -> dict:
    """跑一次工單流程，回傳這一輪的完整結果（給後續的審核閘門用）。

    注意最後是從 **session state** 把 triage 撈出來，而不是解析 agent 的文字
    輸出：`output_schema` 讓 ADK 幫我們把 JSON 驗證成 dict 存進 state，
    程式直接讀 dict 就好，不必再做一次字串剖析。
    """
    runner, session_id = await make_runner(build_pipeline(settings), APP_NAME)

    card(placeholders["triage_agent"], "triage_agent", "running")
    for name in STAGES[1:]:
        card(placeholders[name], name, "waiting")

    msg = types.Content(role="user", parts=[types.Part(text=ticket)])
    painter = StreamPainter()
    texts: dict[str, str] = {}
    tool_calls: list[dict] = []

    async for ev in runner.run_async(user_id="user", session_id=session_id,
                                     new_message=msg, run_config=STREAM):
        # partial 事件是文字增量，累積起來逐字畫進卡片。
        # 分類 agent 這一段特別值得看：你會看到 output_schema 的 JSON
        # 一個欄位一個欄位長出來。
        if getattr(ev, "partial", False):
            live = painter.add(ev)
            if live is not None and ev.author in placeholders:
                card(placeholders[ev.author], ev.author, "running", typing(live))
            continue

        # 工具呼叫是「agent 真的去查了資料」的證據，畫出來才看得到查證的過程。
        # 只在非 partial 事件處理：開了串流之後同一個 function call 會先出現在
        # 一個 partial 事件、再出現在正式事件上，兩邊都收就會記成兩次。
        for call in ev.get_function_calls():
            tool_calls.append({"author": ev.author, "name": call.name, "args": dict(call.args or {})})
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
        idx = STAGES.index(ev.author)
        if idx + 1 < len(STAGES):
            card(placeholders[STAGES[idx + 1]], STAGES[idx + 1], "running")

    state = await read_state(runner, session_id)
    triage = state.get("triage") or {}
    order_id = (triage.get("order_id") or "").strip().upper()
    order = ORDERS.get(order_id)

    blocked, reasons = needs_human_review(triage, order)
    return {
        "ticket": ticket,
        "texts": texts,
        "tool_calls": tool_calls,
        "triage": triage,
        "order": order,
        "reply_draft": state.get("reply_draft", ""),
        "blocked": blocked,
        "reasons": reasons,
    }


# ─── Streamlit UI ───────────────────────────────────────────────────

st.set_page_config(page_title="客訴工單分流", page_icon="🎧", layout="wide")

st.title("🎧 客訴工單分流 + 退換貨")
st.caption(
    "ADK `SequentialAgent`：分類（`output_schema` 結構化輸出）→ 查證（`FunctionTool`）"
    "→ 擬稿。**能不能寄出去由 Python 決定，不由模型決定。**"
)

st.session_state.setdefault("last_run", None)
st.session_state.setdefault("decision", None)
st.session_state.setdefault("audit_log", [])

with st.sidebar:
    st.header("⚙️ 設定")
    settings = model_sidebar(key_prefix="support_")

    st.subheader("📨 客訴內容")
    sample_key = st.selectbox("範例工單", list(SAMPLE_TICKETS.keys()))
    ticket = st.text_area("客戶訊息", SAMPLE_TICKETS[sample_key], height=170)
    run_btn = st.button("▶️ 處理這張工單", type="primary", width="stretch")

    with st.expander("📇 假訂單資料庫", expanded=False):
        for oid, o in ORDERS.items():
            d = days_since_delivery(o)
            st.markdown(
                f"**{oid}**（{o['platform']}）· NT$ {o['amount_twd']}  \n"
                f"{o['item']}  \n"
                f"{o['status']}"
                + (f"，送達 {d} 天" if d >= 0 else "")
                + ("  · ⭐VIP" if o["vip"] else "")
            )

cols = st.columns(3)
placeholders = {name: cols[i].empty() for i, name in enumerate(STAGES)}

st.subheader("🔧 工具呼叫軌跡")
tool_box = st.container()

gate_area = st.container()

if run_btn:
    if not ticket.strip():
        st.error("請先填客訴內容")
    else:
        for _n in STAGES:
            card(placeholders[_n], _n, "waiting")
        st.session_state["decision"] = None
        st.session_state["last_run"] = asyncio.run(
            run_pipeline_live(settings, ticket.strip(), placeholders, tool_box)
        )

run = st.session_state["last_run"]

if not run:
    for _n in STAGES:
        card(placeholders[_n], _n, "waiting")
elif not run_btn:
    # 按了核准／退回按鈕會讓 Streamlit 重跑整個 script，這時不重新呼叫模型，
    # 直接用上一輪存下來的結果把畫面畫回去。
    for _n in STAGES:
        card(placeholders[_n], _n, "done" if run["texts"].get(_n) else "waiting",
             run["texts"].get(_n, ""))
    with tool_box:
        for c in run["tool_calls"]:
            render_tool_call(st.empty(), author=c["author"], tool_name=c["name"], args=c["args"])

# ─── 人工審核閘門 ───────────────────────────────────────────────────

if run:
    with gate_area:
        st.divider()
        t = run["triage"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("類型", t.get("category", "—"))
        c2.metric("急迫度", t.get("urgency", "—"))
        c3.metric("訂單", t.get("order_id") or "查無")
        c4.metric("金額", f"NT$ {run['order']['amount_twd']}" if run["order"] else "—")
        if t.get("summary"):
            st.caption(f"摘要：{t['summary']}　·　客戶情緒：{t.get('customer_emotion', '—')}")

        st.subheader("🚦 人工審核閘門")
        if run["blocked"]:
            st.warning("**這封不能自動寄出**，理由：\n\n"
                       + "\n".join(f"- {r}" for r in run["reasons"]))
        else:
            st.success("符合自動回覆條件（低風險、小額、事實明確），可直接寄出。")

        st.markdown("**回覆草稿**")
        st.info(run["reply_draft"] or "（沒有產出草稿）")

        decision = st.session_state["decision"]
        if decision is None:
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("✅ 核准並寄出", type="primary", width="stretch"):
                st.session_state["decision"] = "approved"
                st.session_state["audit_log"].append({
                    "時間": datetime.now().strftime("%H:%M:%S"),
                    "訂單": t.get("order_id") or "—",
                    "類型": t.get("category", "—"),
                    "需人工": "是" if run["blocked"] else "否",
                    "決定": "核准寄出",
                })
                st.rerun()
            if b2.button("↩️ 退回改寫", width="stretch"):
                st.session_state["decision"] = "rejected"
                st.session_state["audit_log"].append({
                    "時間": datetime.now().strftime("%H:%M:%S"),
                    "訂單": t.get("order_id") or "—",
                    "類型": t.get("category", "—"),
                    "需人工": "是" if run["blocked"] else "否",
                    "決定": "退回改寫",
                })
                st.rerun()
        elif decision == "approved":
            st.success("已寄出（demo 不會真的發信），並寫入稽核紀錄。")
        else:
            st.error("已退回。實務上這裡會把理由回饋給 prompt 或轉真人接手。")

if st.session_state["audit_log"]:
    with st.expander(f"🧾 稽核紀錄（{len(st.session_state['audit_log'])} 筆）", expanded=False):
        st.dataframe(st.session_state["audit_log"], width="stretch")
        st.caption(
            "每一筆都記錄「這張工單有沒有被閘門擋下、真人做了什麼決定」——"
            "這是 agent 能進客服流程的前提。"
        )
