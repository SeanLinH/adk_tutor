"""在 notebook 裡跑 ADK agent 的共用工具。

ADK 的 Runner 回傳的是「事件串流」而不是一句話。這在教學上很好——你看得到
每一次 function call、每一次 transfer——但每個 cell 都寫一次 `async for`
會把重點淹沒。這裡把兩種需求拆開：

* `ask()` / `run_once()`  只要最後那句話
* `trace()` / `print_events()`  想看中間發生了什麼

`visible_parts` / `thought_parts` 處理的是 reasoning model 的問題：它的最終
回應會包含多個 Part，其中 `thought=True` 的那些是模型的自言自語，不該顯示
給使用者。Gemini 的 thinking 模型與本地 gpt-oss 都有這個行為。
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, AsyncIterator

from google.adk.events import Event
from google.genai import types

DEFAULT_USER = "student"

# --- 全域節流 -------------------------------------------------------------
# AI Studio 免費層是以「每分鐘請求數」計費的，而教材裡一個 cell 可能連送十幾
# 次請求（多 agent、工具呼叫、A/B 對照）。所有提問都會經過 ask()，所以在這裡
# 設一道閘門是最省事的做法。用 ADK_RPM=0 可以關掉。
_RPM = int(os.environ.get("ADK_RPM", "12"))
_throttle_lock = asyncio.Lock()
_last_call = 0.0


async def _throttle() -> None:
    if _RPM <= 0:
        return
    global _last_call
    async with _throttle_lock:
        wait = (60.0 / _RPM) - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call = time.monotonic()


# --- Part 層級：把「給人看的」和「模型自言自語」分開 -----------------------

def visible_parts(event: Event) -> list:
    """回傳給使用者看的 parts（濾掉 thought）。"""
    if not event.content or not event.content.parts:
        return []
    return [p for p in event.content.parts if not getattr(p, "thought", False)]


def thought_parts(event: Event) -> list:
    """回傳模型的推理／自言自語 parts。"""
    if not event.content or not event.content.parts:
        return []
    return [p for p in event.content.parts if getattr(p, "thought", False)]


def final_text(event: Event) -> str:
    """把一個 final response event 的使用者可見文字接起來。"""
    return "".join(p.text for p in visible_parts(event) if getattr(p, "text", None))


# --- Session 與提問 -------------------------------------------------------

def _app_name(runner: Any) -> str:
    return getattr(runner, "app_name", None) or "adk_tutor"


async def new_session(
    runner: Any,
    *,
    user_id: str = DEFAULT_USER,
    state: dict | None = None,
) -> str:
    """開一個新 session，回傳 session_id。

    `state` 可以塞初始狀態，例如 {"user_name": "Sean"}，之後就能在 agent 的
    instruction 裡用 {user_name} 取用。
    """
    session = await runner.session_service.create_session(
        app_name=_app_name(runner), user_id=user_id, state=state or {}
    )
    return session.id


async def ask(
    runner: Any,
    text: str,
    *,
    session_id: str,
    user_id: str = DEFAULT_USER,
    trace: bool = False,
) -> str:
    """送一句話給 agent，回傳最終答覆。

    trace=True 時會一併把過程中的 function call / transfer 印出來，
    這在多 agent 的章節幾乎是必開的。
    """
    await _throttle()
    message = types.Content(role="user", parts=[types.Part(text=text)])
    chunks: list[str] = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message
    ):
        if trace:
            _print_event(event)
        if event.is_final_response():
            piece = final_text(event)
            if piece:
                chunks.append(piece)
    return "\n".join(chunks)


async def run_once(agent: Any, text: str, *, trace: bool = False, state: dict | None = None) -> str:
    """一次性問答：自己建 runner、建 session、問完就丟。

    適合「示範一個概念」的 cell；需要多輪對話時請自己留住 runner 與 session_id。
    """
    from google.adk.runners import InMemoryRunner

    runner = InMemoryRunner(agent=agent, app_name="adk_tutor")
    session_id = await new_session(runner, state=state)
    return await ask(runner, text, session_id=session_id, trace=trace)


# --- 觀察事件串流 ---------------------------------------------------------

def _print_event(event: Event) -> None:
    author = event.author or "?"
    if not event.content or not event.content.parts:
        return
    for part in event.content.parts:
        if getattr(part, "function_call", None):
            fc = part.function_call
            print(f"  🔧 [{author}] 呼叫 {fc.name}({dict(fc.args or {})})")
        elif getattr(part, "function_response", None):
            fr = part.function_response
            print(f"  ↩️  [{author}] {fr.name} 回傳 {fr.response}")
        elif getattr(part, "thought", False):
            print(f"  💭 [{author}] （推理中，已隱藏）")
        elif getattr(part, "text", None):
            print(f"  💬 [{author}] {part.text.strip()[:200]}")


async def trace(events: AsyncIterator[Event]) -> list[Event]:
    """把事件串流印出來並收集起來，方便事後檢查。

    用法：`evs = await trace(runner.run_async(...))`
    """
    collected: list[Event] = []
    async for event in events:
        _print_event(event)
        collected.append(event)
    return collected


async def peek_state(
    runner: Any, session_id: str, *, user_id: str = DEFAULT_USER
) -> dict:
    """把 session state 抓出來看。State 是 agent 之間傳資料的主要管道。"""
    session = await runner.session_service.get_session(
        app_name=_app_name(runner), user_id=user_id, session_id=session_id
    )
    return dict(session.state) if session else {}


def print_state(state: dict, *, max_len: int = 120) -> None:
    """印 state 但把長字串截斷，避免一個 output_key 就洗版整個 cell。"""
    if not state:
        print("(state 是空的)")
        return
    for key, value in state.items():
        text = str(value).replace("\n", " ")
        suffix = f" …（共 {len(str(value))} 字）" if len(text) > max_len else ""
        print(f"  {key}: {text[:max_len]}{suffix}")
