# Google ADK 教學

用 **Google ADK 2.x**（Agent Development Kit）從零打造 AI Agent 的兩軌教材。
全部是可執行的 Jupyter notebook，輸出都留在檔案裡。

## 兩條路，挑一條開始

| | [`concept_to_expert/`](concept_to_expert/) | [`30day_practice/`](30day_practice/) |
|---|---|---|
| **形式** | 12 章，線性閱讀（全部完成） | 30 天，一天一資料夾（全 30 天完成） |
| **目的** | 建立整體心智模型 | 深入單一主題 + 生產環境考量 |
| **怎麼讀** | 從 00 依序往下 | 從任何一天開始都可以 |
| **適合** | 第一次接觸 ADK | 已有概念，想深入或查特定主題 |

兩軌互補、互不依賴。建議先跑完概念軌的 `00_setup.ipynb`，確認環境沒問題。

## 快速開始

```bash
uv sync                    # 需要 Python 3.13+、會裝 google-adk 2.8+
cp .env.example .env       # 填入 GOOGLE_API_KEY
```

金鑰到 <https://aistudio.google.com/apikey> 免費申請。
若你的 shell 已經 `export GEMINI_API_KEY`，`.env` 可以留空。

```bash
uv run jupyter lab         # 然後打開 concept_to_expert/00_setup.ipynb
```

## 專案結構

```
concept_to_expert/     概念軌：12 章 + README 學習地圖
30day_practice/        實作軌：30 個資料夾 + README 總覽
shared/                兩軌共用的設定與 helper
demo/                  兩支概念視覺化 app + 四個電商應用資料夾
docs/                  演講稿（概念軌三層敘事的來源）
```

### `shared/` 在做什麼

所有 notebook 都從這裡拿模型與 helper，所以**一份 `.env` 控制全部**。

| 檔案 | 內容 |
|---|---|
| `config.py` | 模型設定。`DEFAULT_MODEL` 集中管理模型 ID、`get_model()` 自動掛重試、`pick_available_model()` 撞配額時自動換 |
| `runtime.py` | `run_once()` / `ask()` / `new_session()` / `peek_state()`，以及全域節流閘門 |
| `plugins.py` | `RateLimiter`、`CallCounter`、`OrderTracer` |

```python
from shared import get_model, run_once
from google.adk.agents import LlmAgent

agent = LlmAgent(name="bot", model=get_model(), instruction="用繁體中文回答。")
print(await run_once(agent, "你好", trace=True))
```

## 撞到 429 的時候

免費層有兩種**分開計算**的配額：

- **一般模型呼叫**：每個模型各自算。`gemini-2.5-flash` 用完了，
  換 `gemini-flash-lite-latest` 還能跑——不必等隔天。
- **Google Search grounding**：獨立額度，而且緊很多。換模型救不了。

```python
import os
from shared import pick_available_model
os.environ["ADK_MODEL"] = pick_available_model()
```

或直接改 `.env` 的 `ADK_MODEL`。另外 `ask()` 有一道全域節流
（預設 12 RPM），設 `ADK_RPM=0` 可關閉。

## 換非 Gemini 模型

教材預設用 Gemini，但 `shared/config.py` 保留了 LiteLLM 這條路。
把 `.env` 改成：

```
ADK_PROVIDER=litellm
ADK_MODEL=openai/openai/gpt-oss-120b
OPENAI_API_BASE=http://localhost:5052/v1
OPENAI_API_KEY=dummy
```

所有 notebook 的程式碼**一行都不用改**——這就是把模型設定集中管理的好處。
（細節見概念軌第 03 章、實作軌 Day 03 / Day 18。）

## Streamlit demo

**概念 demo**（一支檔案講一個概念，對應概念軌第 08、09 章）：

```bash
uv run streamlit run demo/app_orchestration.py   # SequentialAgent 流程視覺化
uv run streamlit run demo/app_coordination.py    # 多 agent 交棒視覺化
```

**應用 demo**（中小型電商的四個真實情境，各自有完整 README）：

| 應用 | 解決什麼 | 主要示範的 ADK 寫法 |
|---|---|---|
| [`demo/listing_studio/`](demo/listing_studio/) | 新品上架內容包 | `SequentialAgent` 包 `ParallelAgent` |
| [`demo/support_triage/`](demo/support_triage/) | 客訴分流與退換貨 | `output_schema` + `FunctionTool` + 人工審核閘門 |
| [`demo/inventory_watch/`](demo/inventory_watch/) | 多平台庫存異常日報 | 規則引擎與 LLM 的分界線 |
| [`demo/campaign_insight/`](demo/campaign_insight/) | 廣告/銷售/庫存交叉分析 | `sub_agents` + `mode="single_turn"` |

```bash
uv run streamlit run demo/listing_studio/app.py     # 其餘三個換掉資料夾名即可
```

資料全是假的，不必接任何電商平台就能跑完整流程。四個應用合起來在回答同一個
問題——**這一步該讓誰做**——詳見 [`demo/README.md`](demo/)。

## 環境需求

- Python 3.13+
- `google-adk[a2a,db,eval,mcp,otel-gcp] >= 2.8.0`（1.x 沒有 `Workflow`，第 10 章會跑不起來）
- Gemini API 金鑰
