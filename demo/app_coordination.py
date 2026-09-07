"""技術文件生成 — Coordination（LlmAgent + sub_agents + transfer）視覺化 demo.

跑法：streamlit run demo/app_coordination.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from shared import FALLBACK_MODELS, final_text, get_model, load_settings
from shared.config import Settings


# ─── Agent meta（顏色 + icon 對應）─────────────────────────────────

AGENT_META = {
    "doc_coordinator": {"icon": "🧭", "title": "Coordinator", "color": "#9B59B6"},
    "outline_agent":   {"icon": "📋", "title": "大綱規劃師",   "color": "#3498DB"},
    "writer_agent":    {"icon": "✍️", "title": "技術寫手",     "color": "#E67E22"},
    "reviewer_agent":  {"icon": "🔍", "title": "編輯校對員",   "color": "#27AE60"},
    "user":            {"icon": "🙋", "title": "你",          "color": "#888888"},
}


# ─── 建 agent team（每次 run 開新的）────────────────────────────────

def build_team(settings: Settings) -> LlmAgent:
    model_kwargs = {"settings": settings}

    outline_agent = LlmAgent(
        name="outline_agent",
        model=get_model(**model_kwargs),
        description="規劃技術文件的大綱結構（章節 + 每章重點）。",
        instruction=(
            "你是技術文件大綱規劃師。產出 3~5 章大綱，每章標題 + 2 個 bullet。\n"
            "**完成後務必呼叫 `transfer_to_agent(agent_name='writer_agent')` 工具**。\n"
            "不要把工具呼叫寫成 JSON 文字，要真的觸發 function call。"
        ),
        disallow_transfer_to_peers=False,
        disallow_transfer_to_parent=False,
    )
    writer_agent = LlmAgent(
        name="writer_agent",
        model=get_model(**model_kwargs),
        description="根據大綱撰寫技術文件正文。",
        instruction=(
            "你是技術寫手。讀對話前面的大綱，每章寫 1~2 段繁體中文內容，**保持簡潔**。\n"
            "**寫完後務必呼叫 `transfer_to_agent(agent_name='reviewer_agent')` 工具**。\n"
            "不要序列化成 JSON 文字。"
        ),
        disallow_transfer_to_peers=False,
        disallow_transfer_to_parent=False,
    )
    reviewer_agent = LlmAgent(
        name="reviewer_agent",
        model=get_model(**model_kwargs),
        description="校對技術文件，指出明顯錯誤或結構問題。",
        instruction=(
            "你是技術文件編輯。挑出最多 2 點需要修改的地方（格式：『問題 → 建議修法』）。"
            "如果文件已經 OK，回『無重大問題』。**不要重寫整篇文章**。"
        ),
        disallow_transfer_to_peers=False,
        disallow_transfer_to_parent=False,
    )
    coordinator = LlmAgent(
        name="doc_coordinator",
        model=get_model(**model_kwargs),
        instruction=(
            "你是技術文件團隊的 PM。當使用者要產出技術文件時，"
            "**永遠先呼叫 `transfer_to_agent(agent_name='outline_agent')` 工具**。\n"
            "不要自己寫文件、不要序列化成 JSON 文字。"
        ),
        sub_agents=[outline_agent, writer_agent, reviewer_agent],
    )
    return coordinator


# ─── 視覺化：氣泡 + transfer 軌跡 ────────────────────────────────

def render_bubble(container, author: str, body: str):
    meta = AGENT_META.get(author, {"icon": "🤖", "title": author, "color": "#777"})
    body_html = body.replace("\n", "<br/>") if body else "*(空)*"
    container.markdown(
        f"""
<div style="margin:10px 0; padding:12px 16px; border-left:5px solid {meta['color']}; background:#FFFFFF06; border-radius:6px;">
  <div style="font-weight:bold; color:{meta['color']}; font-size:14px;">{meta['icon']} {meta['title']}</div>
  <div style="margin-top:6px; font-size:13px; line-height:1.55;">{body_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_transfer(container, src: str, dst: str):
    src_meta = AGENT_META.get(src, {"icon": "🤖", "title": src})
    dst_meta = AGENT_META.get(dst, {"icon": "🤖", "title": dst})
    container.markdown(
        f"""
<div style="text-align:center; margin:6px 0; color:#888; font-size:12px;">
  🔀 {src_meta['icon']} {src_meta['title']} ➔ {dst_meta['icon']} {dst_meta['title']}
</div>
""",
        unsafe_allow_html=True,
    )


# ─── 跑流程 + 即時更新 ───────────────────────────────────────────

async def run_team_live(settings: Settings, topic: str, log_container, transfer_container):
    coordinator = build_team(settings)
    session_service = InMemorySessionService()
    sid = f"doc-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(app_name="coord_demo", user_id="user", session_id=sid)
    runner = Runner(agent=coordinator, app_name="coord_demo", session_service=session_service)

    # 顯示使用者訊息
    with log_container:
        render_bubble(st.empty(), "user", f"幫我寫一份「{topic}」的技術文件")

    transfers: list[tuple[str, str]] = []
    final_output = ""

    msg = types.Content(role="user", parts=[types.Part(text=f"幫我寫一份「{topic}」的技術文件")])
    async for ev in runner.run_async(user_id="user", session_id=sid, new_message=msg):
        for call in ev.get_function_calls():
            if call.name == "transfer_to_agent":
                src = ev.author
                dst = call.args.get("agent_name", "?")
                transfers.append((src, dst))
                with transfer_container:
                    render_transfer(st.empty(), src, dst)
        if ev.is_final_response():
            text = final_text(ev)
            if text:
                with log_container:
                    render_bubble(st.empty(), ev.author, text)
                final_output = text

    return transfers, final_output


# ─── Streamlit UI ───────────────────────────────────────────────

st.set_page_config(page_title="技術文件生成 Demo (Coordination)", page_icon="📝", layout="wide")

st.title("📝 技術文件生成 Demo — Coordination")
st.caption(
    "ADK `LlmAgent + sub_agents + transfer_to_agent`：流程**不寫死**，由 LLM 動態決定下一步交給誰。"
)

with st.sidebar:
    st.header("⚙️ 設定")

    with st.expander("🔌 模型連線", expanded=False):
        defaults = load_settings()
        provider = st.selectbox(
            "Provider", ["gemini", "litellm"],
            index=0 if defaults.provider == "gemini" else 1,
            help="gemini 走 Google AI Studio；litellm 可接本地或第三方模型。",
        )
        if provider == "gemini":
            model_name = st.selectbox(
                "Model", FALLBACK_MODELS,
                index=FALLBACK_MODELS.index(defaults.model_name)
                if defaults.model_name in FALLBACK_MODELS else 0,
                help="免費層配額是每個模型分開算的，撞到 429 就換一個。",
            )
            api_key = st.text_input("GOOGLE_API_KEY", defaults.api_key, type="password")
            api_base = ""
        else:
            model_name = st.text_input("Model", defaults.model_name or "openai/openai/gpt-oss-120b")
            api_base = st.text_input("OPENAI_API_BASE", defaults.api_base or "http://localhost:5052/v1")
            api_key = st.text_input("OPENAI_API_KEY", defaults.api_key, type="password")

    st.subheader("📑 文件主題")
    topic = st.text_area(
        "請輸入想生成的技術主題",
        value="RAG（Retrieval-Augmented Generation）系統入門",
        height=80,
    )

    st.subheader("👥 團隊成員")
    for k, v in AGENT_META.items():
        if k == "user":
            continue
        st.markdown(
            f"<span style='color:{v['color']}'>{v['icon']} **{v['title']}**</span>",
            unsafe_allow_html=True,
        )

    run_btn = st.button("▶️ 開始生成", type="primary", use_container_width=True)

main_col, side_col = st.columns([3, 1])

with main_col:
    st.subheader("💬 Agent 對話流")
    log_container = st.container()

with side_col:
    st.subheader("🔀 Transfer 軌跡")
    transfer_container = st.container()

if run_btn:
    if not topic.strip():
        st.error("請先輸入主題")
    else:
        settings = Settings(provider=provider, model_name=model_name,
                            api_key=api_key, api_base=api_base)
        transfers, final_output = asyncio.run(
            run_team_live(settings, topic.strip(), log_container, transfer_container)
        )
        st.success(f"執行完畢，共 {len(transfers)} 次 transfer。")
        if transfers and len(transfers) < 3:
            st.warning(
                "💡 你看到 transfer 比預期少，這是 Coordination 的真實限制 — "
                "LLM 有時會把 `transfer_to_agent` 序列化成文字而不是真的呼叫。"
                "在 notebook 04 有完整解釋。"
            )
        if final_output:
            with st.expander("📥 下載最終輸出"):
                st.download_button(
                    "下載 markdown",
                    data=final_output,
                    file_name="tech_doc.md",
                    mime="text/markdown",
                )
