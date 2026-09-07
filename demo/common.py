"""四個電商應用 demo 共用的 Streamlit / Runner helper。

`app_orchestration.py` 與 `app_coordination.py` 是「一個檔案讀完一個概念」的
教學 demo，所以刻意把側邊欄、卡片渲染都寫在檔案裡。但 `demo/` 底下的四個
應用資料夾各自有 2~3 支程式，同樣的模型側邊欄再抄四遍只會讓人看不出重點，
所以把重複的部分收在這裡。

這裡放的都是「跟 ADK 概念無關的雜務」——模型選擇、卡片 HTML、Runner 組裝。
每個應用真正的 ADK 設計都留在自己資料夾的 `agents.py` 裡。
"""

from __future__ import annotations

import asyncio
import html
import re
import time
import uuid
from collections import deque
from typing import Any

import streamlit as st
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from shared import FALLBACK_MODELS, final_text, load_settings
from shared.config import Settings

# 免費層是按「每分鐘請求數」算的，而這四個應用都會在一輪裡送出多次請求
# （ParallelAgent 三路並行、策略長連續問三個分析師）。掛一個限流 Plugin
# 在 Runner 上，比在每個 agent 上寫 callback 省事，而且一定先執行。
DEFAULT_RPM = 12


class BurstRateLimiter(BasePlugin):
    """令牌桶限流：一分鐘內最多 N 次模型呼叫，但**允許連續用掉**。

    為什麼不直接用 `shared.RateLimiter`：那支是「每次呼叫之間硬性間隔
    60/rpm 秒」。跑 notebook 很合適（總量大、沒人盯著看），但在互動式 app
    上，它會在每個 agent 之間插入固定的空窗——rpm=10 就是 6 秒，一條五個
    agent 的產線等於乾等 30 秒。實測過：畫面上的文字增長剛好卡在 6.9s、
    12.6s、18.3s、24.0s 這種等距節奏上，逐字輸出的意義整個被抵銷。

    而免費層的限制本來就是「每分鐘 N 次」，不是「每次要隔幾秒」，
    所以一口氣用掉額度完全合法。改成令牌桶之後，demo 跑一輪
    （2~7 次呼叫）完全不用等，只有短時間內連續重跑才會被擋下來。
    """

    def __init__(self, rpm: int = DEFAULT_RPM, name: str = "burst_rate_limiter"):
        super().__init__(name=name)
        self.rpm = max(rpm, 1)
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    def _drop_expired(self, now: float) -> None:
        while self._calls and now - self._calls[0] >= 60.0:
            self._calls.popleft()

    async def before_model_callback(self, *, callback_context, llm_request):
        async with self._lock:
            now = time.monotonic()
            self._drop_expired(now)
            if len(self._calls) >= self.rpm:
                # 這一分鐘的額度用完了，等最舊的那次呼叫滿 60 秒退出視窗。
                await asyncio.sleep(60.0 - (now - self._calls[0]) + 0.05)
                self._drop_expired(time.monotonic())
            self._calls.append(time.monotonic())
        return None  # 回 None 代表放行


# ─── 側邊欄：模型連線 ────────────────────────────────────────────────

def model_sidebar(key_prefix: str = "") -> Settings:
    """畫出「🔌 模型連線」設定區，回傳這次執行要用的 Settings。

    回傳 Settings 而不是直接改 .env，是為了讓側邊欄的選擇只影響這一次執行；
    `shared/config.py` 的 get_model(settings=...) 就是為此保留的入口。
    """
    defaults = load_settings()
    with st.expander("🔌 模型連線", expanded=False):
        provider = st.selectbox(
            "Provider", ["gemini", "litellm"],
            index=0 if defaults.provider == "gemini" else 1,
            help="gemini 走 Google AI Studio；litellm 可接本地或第三方模型。",
            key=f"{key_prefix}provider",
        )
        if provider == "gemini":
            model_name = st.selectbox(
                "Model", FALLBACK_MODELS,
                index=FALLBACK_MODELS.index(defaults.model_name)
                if defaults.model_name in FALLBACK_MODELS else 0,
                help="免費層配額是每個模型分開算的，撞到 429 就換一個。",
                key=f"{key_prefix}model",
            )
            api_key = st.text_input(
                "GOOGLE_API_KEY", defaults.api_key, type="password",
                key=f"{key_prefix}key",
            )
            api_base = ""
        else:
            model_name = st.text_input(
                "Model", defaults.model_name or "openai/openai/gpt-oss-120b",
                key=f"{key_prefix}model",
            )
            api_base = st.text_input(
                "OPENAI_API_BASE", defaults.api_base or "http://localhost:5052/v1",
                key=f"{key_prefix}base",
            )
            api_key = st.text_input(
                "OPENAI_API_KEY", defaults.api_key, type="password",
                key=f"{key_prefix}key",
            )
    return Settings(
        provider=provider, model_name=model_name, api_key=api_key, api_base=api_base
    )


# ─── Runner 組裝 ────────────────────────────────────────────────────

async def make_runner(
    agent: Any,
    app_name: str,
    *,
    rpm: int = DEFAULT_RPM,
    state: dict | None = None,
    artifact_service: Any = None,
) -> tuple[Runner, str]:
    """建一個帶 RateLimiter 的 Runner 與一個新 session，回傳 (runner, session_id)。

    每次執行都開新的 Runner 與 session：Streamlit 每按一次按鈕就重跑整個
    script，沿用舊 session 會讓這一輪讀到上一輪的 state，debug 時很難察覺。
    """
    session_service = InMemorySessionService()
    session_id = f"{app_name}-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=app_name, user_id="user", session_id=session_id, state=state or {}
    )
    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service,
        artifact_service=artifact_service,
        plugins=[BurstRateLimiter(rpm=rpm)],
    )
    return runner, session_id


# ─── 串流 ───────────────────────────────────────────────────────────

# 打開 SSE 串流。ADK 預設是 StreamingMode.NONE：模型整段講完才吐一個事件，
# 使用者會盯著一張空卡片十幾秒，不知道是在跑還是掛了。
STREAM = RunConfig(streaming_mode=StreamingMode.SSE)


class StreamPainter:
    """把 SSE 的 partial 事件累積成可以即時顯示的文字，並節流重繪。

    兩件事必須自己處理，實測過才知道：

    1. **partial 給的是「增量」不是「累積」**——一個事件只帶幾個字，
       所以要自己接起來。直接顯示單一事件的內容只會看到字閃來閃去。
    2. **它們來得很密**（一秒十幾個）。Streamlit 每次 `st.markdown()` 都是
       一次完整的 DOM 重繪，每個 chunk 都畫會明顯卡頓，所以用 `min_interval`
       節流：畫面看起來仍然是連續長出來的，但重繪次數少一個數量級。

    最後 ADK 還是會送一個非 partial 的完整事件，所以收尾用那個，
    不必擔心節流漏掉最後幾個字。
    """

    def __init__(self, min_interval: float = 0.15):
        self.text: dict[str, str] = {}
        self.min_interval = min_interval
        self._last_paint: dict[str, float] = {}

    def add(self, event: Any) -> str | None:
        """吃一個 partial 事件。

        回傳「現在該畫的累積文字」；還沒到重繪時機（或這個事件沒有文字）
        就回 None，呼叫端直接跳過。
        """
        delta = final_text(event)          # 濾掉 thought part 之後的可見文字
        if not delta:
            return None
        author = event.author
        self.text[author] = self.text.get(author, "") + delta
        now = time.monotonic()
        if now - self._last_paint.get(author, 0.0) < self.min_interval:
            return None
        self._last_paint[author] = now
        return self.text[author]

    def reset(self, author: str) -> None:
        """某個 agent 的這一輪講完了，清掉緩衝，下一輪重新累積。"""
        self.text.pop(author, None)
        self._last_paint.pop(author, None)


def typing(text: str) -> str:
    """在串流中的文字尾巴加一個游標，讓「還在寫」看得出來。"""
    return f"{text}▌"


async def read_state(runner: Runner, session_id: str) -> dict:
    """把這一輪的 session state 撈出來。

    多 agent 應用的資料是靠 state 傳遞的（`output_key` 寫進去、下一個 agent
    的 instruction 用 `{key}` 讀出來），所以 UI 想拿中間結果時看這裡最準，
    比從事件串流裡拼字串可靠。
    """
    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id="user", session_id=session_id
    )
    return dict(session.state) if session else {}


# ─── 卡片 / 氣泡渲染 ────────────────────────────────────────────────

STATUS_LABEL = {
    "waiting": "⏳ 等待",
    "running": "🔄 執行中…",
    "done": "✅ 完成",
    "skipped": "⏭️ 略過",
}


def _mini_md(text: str) -> str:
    """把 agent 輸出的 markdown 轉成卡片裡看得懂的 HTML。

    卡片是自己畫的 `<div>`，不是 `st.markdown` 的內容區，所以 Streamlit 不會
    幫忙渲染裡面的 markdown——不處理的話畫面上會出現一堆裸的 `**` 跟 `###`。
    只處理最常見的四種語法就夠了，這裡不需要一個完整的 markdown parser。

    第一步一定是 `html.escape()`：這些字串是模型產生的，直接塞進 innerHTML
    等於讓模型的輸出決定你的 DOM。
    """
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)                 # **粗體**
    out = re.sub(r"(?m)^\s{0,3}#{1,6}\s*(.+)$", r"<b>\1</b>", out)    # ### 標題
    out = re.sub(r"(?m)^(\s*)[*-]\s+", r"\1• ", out)                  # 條列
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", out)    # *斜體*
    return out.replace("\n", "<br/>")


def render_card(
    placeholder,
    *,
    icon: str,
    title: str,
    color: str,
    status: str,
    body: str = "",
    min_height: int = 170,
) -> None:
    """一張 agent 卡片。status 為 waiting 時邊框轉灰，用來表達「還沒輪到它」。"""
    border = color if status != "waiting" else "#CCCCCC"
    if not body:
        # 已經輪到它、但模型的第一個字還沒回來時，不能再說「尚未開始」——
        # 那段空窗期正是使用者最想知道「到底有沒有在動」的時候。
        body = "*等待模型回應…*" if status == "running" else "*尚未開始*"
    body_html = _mini_md(body)
    placeholder.markdown(
        f"""
<div style="border:2px solid {border}; border-radius:10px; padding:14px;
            min-height:{min_height}px; background:#FFFFFF08">
  <div style="font-size:17px; font-weight:bold;">{icon} {title}</div>
  <div style="color:{color}; font-size:13px; margin-top:4px;">{STATUS_LABEL[status]}</div>
  <hr style="margin:8px 0; border-color:#444"/>
  <div style="font-size:13px; line-height:1.55;">{body_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_bubble(container, *, icon: str, title: str, color: str, body: str) -> None:
    """左側有色條的訊息氣泡，用在「誰說了什麼」的對話流。"""
    body_html = _mini_md(body or "*(空)*")
    container.markdown(
        f"""
<div style="margin:10px 0; padding:12px 16px; border-left:5px solid {color};
            background:#FFFFFF06; border-radius:6px;">
  <div style="font-weight:bold; color:{color}; font-size:14px;">{icon} {title}</div>
  <div style="margin-top:6px; font-size:13px; line-height:1.55;">{body_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_tool_call(container, *, author: str, tool_name: str, args: dict) -> None:
    """一次工具呼叫的軌跡列。

    工具呼叫是 agent「真的去做事」的證據，跟它嘴巴上說要做什麼是兩回事——
    這四個 demo 都把它畫出來，就是要讓這個差別看得見。
    """
    arg_text = ", ".join(f"{k}={v!r}" for k, v in (args or {}).items())
    if len(arg_text) > 90:
        arg_text = arg_text[:90] + "…"
    container.markdown(
        f"""
<div style="font-family:monospace; font-size:12px; color:#8A8A8A; margin:3px 0;">
  🔧 <b>{author}</b> → {tool_name}({arg_text})
</div>
""",
        unsafe_allow_html=True,
    )
