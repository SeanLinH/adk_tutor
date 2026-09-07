"""旅遊規劃 — Orchestration（SequentialAgent）視覺化 demo.

跑法：streamlit run demo/app_orchestration.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from shared import FALLBACK_MODELS, final_text, get_model, load_settings
from shared.config import Settings


# ─── 工具：Mock 旅遊資料 ──────────────────────────────────────────

def search_flights(origin: str, destination: str, depart_date: str) -> dict:
    """Search return flights between two cities on a given date."""
    return {
        "flights": [
            {"airline": "長榮 BR-198", "depart": f"{depart_date} 08:30", "price_twd": 14800},
            {"airline": "星宇 JX-822", "depart": f"{depart_date} 13:10", "price_twd": 13200},
            {"airline": "全日空 NH-852", "depart": f"{depart_date} 18:00", "price_twd": 16500},
        ],
        "origin": origin,
        "destination": destination,
    }


def search_hotels(city: str, nights: int) -> dict:
    """Search hotels in a city for a given number of nights."""
    return {
        "hotels": [
            {"name": "Shinjuku Granbell Hotel", "area": "新宿", "price_twd_per_night": 4200},
            {"name": "Park Hotel Tokyo", "area": "汐留", "price_twd_per_night": 6800},
            {"name": "MIMARU Tokyo Ueno East", "area": "上野", "price_twd_per_night": 5500},
        ],
        "city": city,
        "nights": nights,
    }


async def save_itinerary_artifact(content: str, tool_context: ToolContext) -> dict:
    """Save the final itinerary as a user-scoped artifact (markdown)."""
    version = await tool_context.save_artifact(
        filename="user:tokyo_itinerary.md",
        artifact=types.Part(text=content),
    )
    return {"saved": True, "version": version}


# ─── Pipeline builder（每次 run 都開新的，避免狀態互相污染）─────────

def build_pipeline(settings: Settings, save_artifact: bool) -> SequentialAgent:
    model = get_model(settings=settings)

    flight_agent = LlmAgent(
        name="flight_agent",
        model=model,
        instruction=(
            "你是機票搜尋專員。從使用者需求中抓出**起點城市**（英文）、**目的地**（英文）、"
            "**出發日期**，**呼叫 search_flights 工具**取得航班，再用條列格式列 3 個選項。"
        ),
        tools=[FunctionTool(func=search_flights)],
        output_key="flight_options",
    )
    hotel_agent = LlmAgent(
        name="hotel_agent",
        model=get_model(settings=settings),
        instruction=(
            "你是飯店推薦專員。從使用者需求中抓出**目的地城市**（英文）跟**晚數**，"
            "**呼叫 search_hotels 工具**取得飯店，用條列格式列 3 間（名稱、區域、每晚價格）。"
        ),
        tools=[FunctionTool(func=search_hotels)],
        output_key="hotel_options",
    )

    itin_instruction = (
        "你是行程規劃師。根據以下資訊，用繁體中文寫一份簡潔的行程：\n\n"
        "【機票選項】\n{flight_options}\n\n"
        "【飯店選項】\n{hotel_options}\n\n"
        "請推薦其中一個機票+飯店組合，並列出每天 2 個重點景點。"
    )
    itinerary_tools: list = []
    if save_artifact:
        itin_instruction += (
            "\n\n寫完後，**呼叫 save_itinerary_artifact 工具**把整份行程存起來。"
        )
        itinerary_tools.append(FunctionTool(func=save_itinerary_artifact))

    itinerary_agent = LlmAgent(
        name="itinerary_agent",
        model=get_model(settings=settings),
        instruction=itin_instruction,
        tools=itinerary_tools,
        output_key="final_itinerary",
    )

    return SequentialAgent(
        name="travel_pipeline",
        sub_agents=[flight_agent, hotel_agent, itinerary_agent],
        description="機票 → 飯店 → 行程整合",
    )


# ─── 卡片渲染 ────────────────────────────────────────────────────

STAGE_META = {
    "flight_agent":    {"icon": "✈️", "title": "機票 Agent",   "color": "#4A90E2"},
    "hotel_agent":     {"icon": "🏨", "title": "飯店 Agent",   "color": "#F5A623"},
    "itinerary_agent": {"icon": "📋", "title": "行程 Agent",   "color": "#7ED321"},
}


def render_card(placeholder, agent_name: str, status: str, body: str = ""):
    meta = STAGE_META[agent_name]
    status_icon = {"waiting": "⏳ 等待", "running": "🔄 執行中…", "done": "✅ 完成"}[status]
    border = meta["color"] if status != "waiting" else "#CCCCCC"
    body_html = body or "*尚未開始*"
    placeholder.markdown(
        f"""
<div style="border:2px solid {border}; border-radius:10px; padding:14px; min-height:180px; background:#FFFFFF08">
  <div style="font-size:18px; font-weight:bold;">{meta['icon']} {meta['title']}</div>
  <div style="color:{meta['color']}; font-size:13px; margin-top:4px;">{status_icon}</div>
  <hr style="margin:8px 0; border-color:#444"/>
  <div style="font-size:13px; line-height:1.5;">{body_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ─── 跑流程 + 即時更新 ───────────────────────────────────────────

async def run_pipeline_live(settings: Settings, request: str, save_artifact: bool, placeholders: dict):
    pipeline = build_pipeline(settings, save_artifact)

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService() if save_artifact else None
    sid = f"trip-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(app_name="orch_demo", user_id="user", session_id=sid)
    runner = Runner(
        agent=pipeline,
        app_name="orch_demo",
        session_service=session_service,
        artifact_service=artifact_service,
    )

    # 初始狀態：第一個 running、其餘 waiting
    render_card(placeholders["flight_agent"], "flight_agent", "running")
    render_card(placeholders["hotel_agent"], "hotel_agent", "waiting")
    render_card(placeholders["itinerary_agent"], "itinerary_agent", "waiting")

    msg = types.Content(role="user", parts=[types.Part(text=request)])
    completed = set()
    async for ev in runner.run_async(user_id="user", session_id=sid, new_message=msg):
        if ev.is_final_response():
            text = final_text(ev)
            if not text or ev.author not in placeholders:
                continue
            render_card(placeholders[ev.author], ev.author, "done", text.replace("\n", "<br/>"))
            completed.add(ev.author)
            # 啟動下一個 stage 的 running 狀態
            order = ["flight_agent", "hotel_agent", "itinerary_agent"]
            idx = order.index(ev.author)
            if idx + 1 < len(order):
                nxt = order[idx + 1]
                if nxt not in completed:
                    render_card(placeholders[nxt], nxt, "running")

    # 取得 artifact（若有開）
    if save_artifact and artifact_service:
        try:
            part = await artifact_service.load_artifact(
                app_name="orch_demo", user_id="user", session_id=sid,
                filename="user:tokyo_itinerary.md",
            )
            if part and part.text:
                return part.text
        except Exception:
            return None
    return None


# ─── Streamlit UI ───────────────────────────────────────────────

st.set_page_config(page_title="旅遊規劃 Demo (Orchestration)", page_icon="✈️", layout="wide")

st.title("✈️ 旅遊規劃 Demo — Orchestration")
st.caption("ADK `SequentialAgent` 把三個 sub-agent 串成一條 pipeline，順序固定、可預測。")

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

    st.subheader("🧳 旅程")
    origin = st.text_input("出發城市（英文）", "Taipei")
    destination = st.text_input("目的地（英文）", "Tokyo")
    depart_date = st.date_input("出發日期", value=date.today() + timedelta(days=14))
    days = st.slider("天數", 2, 7, 3)

    st.subheader("📦 Artifact")
    save_artifact = st.checkbox("把最終行程存成 Artifact（可下載）", value=True)

    run_btn = st.button("▶️ 開始規劃", type="primary", use_container_width=True)

# 主畫面：三張卡片並排
cols = st.columns(3)
placeholders = {
    "flight_agent": cols[0].empty(),
    "hotel_agent": cols[1].empty(),
    "itinerary_agent": cols[2].empty(),
}
for name in placeholders:
    render_card(placeholders[name], name, "waiting")

result_area = st.container()

if run_btn:
    request = (
        f"我想 {depart_date.isoformat()} 從 {origin} 出發去 {destination} 玩 {days} 天"
    )
    st.info(f"使用者輸入：{request}")
    settings = Settings(provider=provider, model_name=model_name,
                            api_key=api_key, api_base=api_base)
    artifact_md = asyncio.run(
        run_pipeline_live(settings, request, save_artifact, placeholders)
    )
    if artifact_md:
        with result_area:
            st.success("行程已存成 Artifact，可下載")
            st.download_button(
                "📥 下載 tokyo_itinerary.md",
                data=artifact_md,
                file_name="tokyo_itinerary.md",
                mime="text/markdown",
            )
