"""教材共用的 Plugin。

Plugin 跟 Callback 用的是同一套 hook，差別在範圍：Callback 掛在單一 agent
或 tool 上，Plugin 註冊在 App／Runner 上就全域生效。ADK 保證 **Plugin 的
callback 一定跑在物件層級 callback 之前，而且會短路後者**——所以護欄類的
邏輯要寫成 Plugin，不要寫成 agent callback。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from google.adk.plugins.base_plugin import BasePlugin


class RateLimiter(BasePlugin):
    """在每次呼叫模型前擋一下，避免打爆 AI Studio 免費層的 RPM 限制。

    免費層是以「每分鐘請求數」計費的，而一個多 agent 的 cell 可能一口氣送
    出十幾次請求。教材批次執行時建議一律掛上。
    """

    def __init__(self, rpm: int = 10, name: str = "rate_limiter"):
        super().__init__(name=name)
        self.min_interval = 60.0 / max(rpm, 1)
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def before_model_callback(self, *, callback_context, llm_request):
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            wait = self.min_interval - elapsed
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
        return None  # 回 None 代表放行；回 LlmResponse 就會跳過真正的模型呼叫


class CallCounter(BasePlugin):
    """數這一輪總共打了幾次模型、幾次工具。

    成本問題在教材裡很容易被忽略，但一個寫壞的 LoopAgent 可以在你眼皮底下
    燒掉幾十次呼叫。把數字印出來，學生才有感。
    """

    def __init__(self, name: str = "call_counter"):
        super().__init__(name=name)
        self.model_calls = 0
        self.tool_calls: list[str] = []

    async def before_model_callback(self, *, callback_context, llm_request):
        self.model_calls += 1
        return None

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        self.tool_calls.append(tool.name)
        return None

    def reset(self) -> None:
        self.model_calls = 0
        self.tool_calls = []

    def report(self) -> str:
        tools = ", ".join(self.tool_calls) if self.tool_calls else "（無）"
        return f"模型呼叫 {self.model_calls} 次；工具呼叫 {len(self.tool_calls)} 次：{tools}"


class OrderTracer(BasePlugin):
    """把 hook 觸發順序記下來。

    Day 12 用它來實證「Plugin 先於 Callback 且會短路」這件事——光看文件
    容易記反，跑一次就永遠不會忘。
    """

    def __init__(self, log: list[str], name: str = "order_tracer"):
        super().__init__(name=name)
        self.log = log

    async def before_model_callback(self, *, callback_context, llm_request):
        self.log.append(f"plugin:{self.name}:before_model")
        return None

    async def after_model_callback(self, *, callback_context, llm_response):
        self.log.append(f"plugin:{self.name}:after_model")
        return None

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        self.log.append(f"plugin:{self.name}:before_tool:{tool.name}")
        return None

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        self.log.append(f"plugin:{self.name}:after_tool:{tool.name}")
        return None
