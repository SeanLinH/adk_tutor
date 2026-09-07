"""兩軌 ADK 教材共用的小工具。

    from shared import get_model, run_once, ask, new_session, peek_state

`concept_to_expert/` 每一章都會用到；`30day_practice/` 的每日 notebook 則是
刻意重複寫出環境設定，讓每天都能獨立執行，但同樣可以 import 這裡的 helper。
"""

from shared.config import (
    DEFAULT_MODEL,
    FALLBACK_MODELS,
    LIVE_MODEL,
    MODEL_NAME,
    NATIVE_AUDIO_MODEL,
    PRO_MODEL,
    Settings,
    get_model,
    load_settings,
    pick_available_model,
    quiet,
    require_api_key,
)
from shared.plugins import CallCounter, OrderTracer, RateLimiter
from shared.runtime import (
    ask,
    final_text,
    new_session,
    peek_state,
    print_state,
    run_once,
    thought_parts,
    trace,
    visible_parts,
)

__all__ = [
    # config
    "DEFAULT_MODEL",
    "FALLBACK_MODELS",
    "PRO_MODEL",
    "LIVE_MODEL",
    "NATIVE_AUDIO_MODEL",
    "MODEL_NAME",
    "Settings",
    "get_model",
    "load_settings",
    "pick_available_model",
    "quiet",
    "require_api_key",
    # runtime
    "ask",
    "new_session",
    "run_once",
    "trace",
    "peek_state",
    "print_state",
    "final_text",
    "visible_parts",
    "thought_parts",
    # plugins
    "RateLimiter",
    "CallCounter",
    "OrderTracer",
]
