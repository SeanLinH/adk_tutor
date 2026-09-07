"""兩軌教材共用的設定層。

`concept_to_expert/` 的 notebook、`30day_practice/` 的每日 notebook、以及
`demo/` 的 Streamlit app 都從這裡拿模型，所以一份 .env 就能控制全部。

設計重點：模型 ID 全部集中在 DEFAULT_MODEL / PRO_MODEL / FALLBACK_MODELS。
理由有兩個，而且都是實際踩過的：

1. **模型會下架。** gemini-2.0-flash 已停用，呼叫直接回 404 並要求改用
   gemini-3.6-flash。集中在一處，壞掉時只要改一行。
2. **免費層配額是每個模型分開算的。** 撞到 429 時換一個模型 ID 通常就過了，
   不必等隔天——pick_available_model() 就是把這件事自動化。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# --- 模型預設值 -----------------------------------------------------------
# 免費層的配額是「每個模型各自計算」的：gemini-2.5-flash 用完了，
# gemini-2.5-flash-lite 還是照跑。所以撞到 429 時，換一個模型 ID 通常就過了，
# 不必等隔天。這也是為什麼模型 ID 要集中在這裡——改一行，全教材跟著換。
DEFAULT_MODEL = "gemini-flash-lite-latest"  # 教材預設：便宜、快、配額寬鬆
PRO_MODEL = "gemini-flash-latest"           # 需要較好推理品質時
FALLBACK_MODELS = [                         # 撞到配額時的候補清單，依序試
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]
LIVE_MODEL = "gemini-3.1-flash-live-preview"          # Day 21/22 Live API
NATIVE_AUDIO_MODEL = "gemini-2.5-flash-native-audio-latest"  # Day 23


@dataclass(frozen=True)
class Settings:
    """一次執行所需的全部模型設定。

    Streamlit 側邊欄可以直接建構 Settings(...) 來覆寫，不必改 .env。
    """

    provider: str          # "gemini" | "litellm"
    model_name: str
    api_key: str = ""      # gemini: GOOGLE_API_KEY / litellm: OPENAI_API_KEY
    api_base: str = ""     # 只有 litellm 走本地端點時才需要


def load_settings(env_path: Path | str | None = None) -> Settings:
    """讀 .env（若存在）並組出 Settings。

    provider 由 ADK_PROVIDER 決定，預設 gemini。
    Gemini 金鑰接受 GOOGLE_API_KEY 或 GEMINI_API_KEY（google-genai 兩個都吃，
    但兩個同時設定時它會優先用 GOOGLE_API_KEY 並印出提示）。
    """
    target = Path(env_path) if env_path else ENV_FILE
    if target.exists():
        load_dotenv(target, override=False)

    provider = os.environ.get("ADK_PROVIDER", "gemini").strip().lower()

    if provider == "litellm":
        api_base = os.environ.get("OPENAI_API_BASE", "http://localhost:5052/v1")
        api_key = os.environ.get("OPENAI_API_KEY", "test123")
        # LiteLLM 從 os.environ 全域讀這兩個值，所以要寫回去。
        os.environ["OPENAI_API_BASE"] = api_base
        os.environ["OPENAI_API_KEY"] = api_key
        return Settings(
            provider="litellm",
            model_name=os.environ.get("ADK_MODEL", "openai/openai/gpt-oss-120b"),
            api_key=api_key,
            api_base=api_base,
        )

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        # ADK 內部的 google-genai client 讀 GOOGLE_API_KEY。
        os.environ.setdefault("GOOGLE_API_KEY", api_key)
    return Settings(
        provider="gemini",
        model_name=os.environ.get("ADK_MODEL", DEFAULT_MODEL),
        api_key=api_key,
    )


_DEFAULT = load_settings()
MODEL_NAME = _DEFAULT.model_name


def _retry_options():
    """免費層很容易撞到 429（配額）與 503（模型忙碌），自動重試才跑得完一本 notebook。

    ADK 預設不重試，所以要自己給。這也是 `model="gemini-2.5-flash"` 這種
    字串寫法辦不到、必須改用模型「物件」的第一個實際理由（Day 03 主題）。
    """
    from google.genai.types import HttpRetryOptions

    return HttpRetryOptions(
        attempts=5,
        initial_delay=2.0,
        max_delay=30.0,
        http_status_codes=[429, 500, 502, 503, 504],
    )


def get_model(model_name: str | None = None, settings: Settings | None = None):
    """回傳可直接餵給 `LlmAgent(model=...)` 的東西。

    Gemini  -> 回傳 Gemini 物件（帶重試設定），而不是裸字串。
    LiteLLM -> 回傳 LiteLlm 實例；每次都給新的，避免多個 agent 共用底層
               client 造成狀態互相污染。
    """
    s = settings or _DEFAULT
    name = model_name or s.model_name

    if s.provider == "litellm":
        from google.adk.models.lite_llm import LiteLlm  # 延遲 import，Gemini 路徑不需要

        return LiteLlm(model=name, api_base=s.api_base, api_key=s.api_key)

    from google.adk.models.google_llm import Gemini

    return Gemini(model=name, retry_options=_retry_options())


def require_api_key(settings: Settings | None = None) -> None:
    """在 notebook 開頭呼叫，缺金鑰時給出可行動的錯誤訊息而不是一路跑到 404。"""
    s = settings or _DEFAULT
    if s.provider == "gemini" and not s.api_key:
        raise RuntimeError(
            "找不到 GOOGLE_API_KEY（或 GEMINI_API_KEY）。\n"
            "1. 到 https://aistudio.google.com/apikey 申請一把免費金鑰\n"
            f"2. 寫進 {ENV_FILE}：GOOGLE_API_KEY=your-key-here\n"
            "3. 重啟 notebook kernel"
        )


def quiet() -> None:
    """關掉幾個已知會洗版 notebook 輸出的第三方警告。

    這些訊息本身無害，但每個 cell 都噴一次會蓋掉真正要看的東西：
      * authlib 的 deprecation warning（ADK 相依套件在 import 時就會噴）
      * ADK 的 [EXPERIMENTAL] feature 提示
      * google-genai 的 automatic function calling 建議
    只擋這幾類，其他警告照舊顯示——真的出事時你還是看得到。
    """
    import logging
    import warnings

    warnings.filterwarnings("ignore")

    # authlib 是在「第一次真的呼叫 API」時才被 lazy import 的，警告會在某個
    # cell 執行到一半才冒出來。而且 authlib/deprecate.py 在自己被 import 時會
    # 執行 warnings.simplefilter("always", AuthlibDeprecationWarning)，硬是把
    # 自己插到所有既有 filter 前面——所以「先 filter 再 import」是沒用的，
    # 必須先把它 import 進來，再蓋掉它裝的那個 filter。
    try:
        from authlib.deprecate import AuthlibDeprecationWarning

        warnings.filterwarnings("ignore", category=AuthlibDeprecationWarning)
        import authlib.jose  # noqa: F401
    except Exception:
        pass

    # ADK 會把 node 失敗的完整 traceback 用 logging 印一次，然後才把例外丟出來。
    # 教材裡刻意示範錯誤時，那份 log 會蓋掉真正想給人看的訊息。
    for name in ("google_genai", "google_genai.models", "google.adk", "google_adk"):
        logging.getLogger(name).setLevel(logging.CRITICAL)


def pick_available_model(candidates: list[str] | None = None, verbose: bool = True) -> str:
    """依序試候補模型，回傳第一個還有配額的。

    免費層的配額是每個模型分開算的，所以撞到 429 時換一個模型 ID 通常就過了，
    不必等隔天。這個函式把「換一個試試」自動化：

        import os
        from shared import pick_available_model
        os.environ["ADK_MODEL"] = pick_available_model()

    每試一個模型會花掉一次很小的請求，所以不要放在迴圈裡呼叫。
    """
    import os

    from google import genai

    names = candidates or FALLBACK_MODELS
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    client = genai.Client(api_key=key)

    for name in names:
        try:
            client.models.generate_content(model=name, contents="hi")
            if verbose:
                print(f"✅ {name} 可用")
            return name
        except Exception as exc:
            reason = "配額用完 (429)" if "429" in str(exc) else str(exc)[:60]
            if verbose:
                print(f"⏭️  {name} 跳過：{reason}")
    raise RuntimeError(f"候補清單裡沒有可用的模型：{names}")
