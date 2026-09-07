"""新品上架內容產線 — ParallelAgent 扇出扇入視覺化。

跑法：streamlit run demo/listing_studio/app.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent.parent
for _p in (str(PROJECT_ROOT), str(APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from google.genai import types

from agents import AGENT_META, PARALLEL_AGENTS, build_pipeline, build_request
from demo.common import STREAM, StreamPainter, make_runner, model_sidebar, render_card, typing
from shared import final_text
from shared.config import Settings

APP_NAME = "listing_studio"


def _height(agent_name: str) -> int:
    return 120 if agent_name == "assemble_agent" else 170


def card(placeholder, agent_name: str, status: str, body: str = ""):
    meta = AGENT_META[agent_name]
    render_card(
        placeholder, icon=meta["icon"], title=meta["title"], color=meta["color"],
        status=status, body=body, min_height=_height(agent_name),
    )


async def run_pipeline_live(settings: Settings, request: str, placeholders: dict) -> str:
    """跑一次產線，**逐字**更新卡片，回傳最終上架包。

    這個函式示範怎麼把 ADK 的事件串流接到 UI：`runner.run_async()` 是一個
    async generator，用 `event.author` 就知道是誰在講、該更新哪張卡。

    開了 `run_config=STREAM`（SSE）之後，事件分兩種：
    * `event.partial=True`：文字**增量**，一次幾個字 → 累積起來即時重繪
    * 非 partial 的 final event：這一輪的**完整**文字 → 用它收尾

    並行階段最好看：三張卡會同時各自長出文字，因為三個分支的 partial
    事件是交錯回來的。
    """
    runner, session_id = await make_runner(build_pipeline(settings), APP_NAME)

    card(placeholders["spec_agent"], "spec_agent", "running")
    for name in PARALLEL_AGENTS:
        card(placeholders[name], name, "waiting")
    card(placeholders["assemble_agent"], "assemble_agent", "waiting")

    msg = types.Content(role="user", parts=[types.Part(text=request)])
    painter = StreamPainter()
    done: set[str] = set()
    listing_pack = ""

    async for ev in runner.run_async(user_id="user", session_id=session_id,
                                     new_message=msg, run_config=STREAM):
        if getattr(ev, "partial", False):
            live = painter.add(ev)
            if live is not None and ev.author in placeholders:
                card(placeholders[ev.author], ev.author, "running", typing(live))
            continue

        if not ev.is_final_response():
            continue
        text = final_text(ev)
        if not text or ev.author not in placeholders:
            continue

        card(placeholders[ev.author], ev.author, "done", text)
        painter.reset(ev.author)
        done.add(ev.author)

        # 賣點分析一講完，三個分支就同時開跑——UI 也一次點亮三張卡，
        # 這是 ParallelAgent 跟 SequentialAgent 在畫面上最直觀的差別。
        if ev.author == "spec_agent":
            for name in PARALLEL_AGENTS:
                card(placeholders[name], name, "running")
        elif all(n in done for n in PARALLEL_AGENTS) and "assemble_agent" not in done:
            card(placeholders["assemble_agent"], "assemble_agent", "running")

        if ev.author == "assemble_agent":
            listing_pack = text

    return listing_pack


# ─── Streamlit UI ───────────────────────────────────────────────────

st.set_page_config(page_title="新品上架內容產線", page_icon="🛍️", layout="wide")

st.title("🛍️ 新品上架內容產線")
st.caption(
    "ADK `SequentialAgent` ➜ `ParallelAgent` ➜ `SequentialAgent`："
    "賣點分析先跑，SEO / 描述 / 社群三路**同時**產出，最後整合成上架包。"
)

with st.sidebar:
    st.header("⚙️ 設定")
    settings = model_sidebar(key_prefix="listing_")

    st.subheader("🛒 商品資料")
    name = st.text_input("商品名稱", "備長炭竹纖維除濕包 300g x3 入")
    category = st.selectbox(
        "類別",
        ["居家生活", "3C 周邊", "服飾配件", "美妝保養", "食品飲料", "母嬰用品", "寵物用品"],
    )
    price = st.number_input("售價（NT$）", min_value=1, value=399, step=10)
    platforms = st.multiselect(
        "上架平台", ["蝦皮", "momo", "官網", "PChome", "Line 購物"],
        default=["蝦皮", "官網"],
    )
    notes = st.text_area(
        "你自己的筆記（越具體，賣點越準）",
        "台灣製，可重複曬乾使用約 2 年。客人常問會不會有炭灰掉出來——不會，有雙層布套。",
        height=110,
    )
    run_btn = st.button("▶️ 產出上架包", type="primary", width="stretch")

st.subheader("① 賣點分析")
spec_col = st.container()
st.subheader("② 三路並行產出")
p_cols = st.columns(3)
st.subheader("③ 整合上架包")
assemble_col = st.container()

placeholders = {
    "spec_agent": spec_col.empty(),
    "seo_agent": p_cols[0].empty(),
    "desc_agent": p_cols[1].empty(),
    "social_agent": p_cols[2].empty(),
    "assemble_agent": assemble_col.empty(),
}
for _name in placeholders:
    card(placeholders[_name], _name, "waiting")

result_area = st.container()

if run_btn:
    if not name.strip():
        st.error("請先填商品名稱")
    else:
        request = build_request(name.strip(), category, int(price), notes.strip(), platforms)
        with st.expander("📨 送進 pipeline 的第一句話", expanded=False):
            st.code(request, language="text")
        listing_pack = asyncio.run(run_pipeline_live(settings, request, placeholders))
        if listing_pack:
            with result_area:
                st.success("上架包完成")
                st.markdown(listing_pack)
                st.download_button(
                    "📥 下載上架包 markdown",
                    data=listing_pack,
                    file_name=f"listing_{name.strip()[:12]}.md",
                    mime="text/markdown",
                )
