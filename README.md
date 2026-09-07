# Google ADK 教學

用 **Google ADK 2.0**（Agent Development Kit）從零打造 AI Agent 的兩軌教材，
全繁體中文。對象是「會寫 Python，但沒做過 agent」的人。

- **42 本 Jupyter notebook**：概念軌 12 章 + 實作軌 30 天
- **6 支 Streamlit app**：2 支概念視覺化 + 4 個中小型電商的完整應用
- 每一格都**真的執行過，輸出留在檔案裡**——還沒申請金鑰也能先讀完再決定要不要動手

## 這份教材跟官方文件差在哪

官方文件告訴你 API 怎麼用；這份教材想回答的是**為什麼會有這個 API，以及它會在哪裡咬你**。

| | |
|---|---|
| **每一章都標出「關鍵坑」** | 例如：`InMemoryMemoryService` 是關鍵字比對、對中文幾乎失效；Plugin 一定先於 agent callback 執行**而且會短路它**。這類東西官方文件多半埋在 Caution 區塊，或根本沒寫 |
| **查證寫成程式，不寫成文字** | 版本會變、模型會下架。那些「翻原始碼確認」的段落都是可執行的 cell，你在自己安裝的版本上重跑，看到的就是你的答案 |
| **設定集中在一處** | 42 本 notebook 共用 `shared/`，換模型、換 provider 都只改一行，notebook 本身不用動 |
| **最後有能用的東西** | `demo/` 的四個電商應用不是 hello world，而是同一個問題的四種答案：**這一步該讓誰做** |

## 你會學到什麼

ADK 的元件不少，但可以壓成三層。跑完概念軌，你會知道每個元件為什麼存在、彼此怎麼接：

```
Layer 1  一個 Agent 由什麼構成
         身分（name / description / instruction）
         工具（FunctionTool、ToolContext、內建工具）
         模型與結構化輸出（retry、temperature、output_schema）

Layer 2  它怎麼跑起來
         Runner / Session / State
         Memory / Artifact
         App / Callbacks / Plugins

Layer 3  多個 Agent 怎麼合作
         Sequential / Parallel / Loop
         Orchestration（流程寫死）vs Coordination（模型決定）
         Graph Workflows（ADK 2.0 的圖形引擎）
```

實作軌在這之上再往生產環境走：MCP / OpenAPI 整合、A2A 跨程序協作、Live 語音與
多模態、評估與最佳化、模擬器、企業級安全、觀測、部署。

## 開始你的練習

| | [`concept_to_expert/`](concept_to_expert/) | [`30day_practice/`](30day_practice/) |
|---|---|---|
| **形式** | 12 章，線性閱讀（全部完成） | 30 天，一天一資料夾（全 30 天完成） |
| **目的** | 建立整體心智模型 | 深入單一主題 + 生產環境考量 |
| **怎麼讀** | 從 00 依序往下 | 從任何一天開始都可以 |
| **適合** | 第一次接觸 ADK | 已有概念，想深入或查特定主題 |

該挑哪一條：

- **沒碰過 ADK** → 概念軌，從 `00_setup.ipynb` 依序讀下去。
- **想查特定主題**（A2A？語音？部署？）→ 實作軌，直接跳到那一天，不必補前面。
- **要做一個能給人看的東西** → `demo/` 的四個電商應用，換掉資料檔就能改成你自己的。

兩軌互補、互不依賴。無論走哪一條，建議先跑完概念軌的 `00_setup.ipynb` 確認環境沒問題。

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
concept_to_expert/     概念軌：12 章 notebook + 學習地圖 README
30day_practice/        實作軌：30 個資料夾，每天一份 README + notebook
demo/                  2 支概念視覺化 app + 4 個電商應用（各自有 README）
shared/                兩軌共用的模型設定與 helper
slides/                前十二日的簡報，單一 HTML，用瀏覽器打開就能看
```

所有 notebook 都從這裡拿模型與 helper，所以**一份 `.env` 控制全部**。

| 檔案 | 內容 |
|---|---|
| `config.py` | 模型設定。`DEFAULT_MODEL` 集中管理模型 ID、`get_model()` 自動掛重試、`pick_available_model()` 額度用完時自動換一個 |
| `runtime.py` | `run_once()` / `ask()` / `new_session()` / `peek_state()`，以及全域節流閘門 |
| `plugins.py` | `RateLimiter`、`CallCounter`、`OrderTracer` |


## 換非 Gemini 模型

教材預設用 Gemini，但 `shared/config.py` 保留了 LiteLLM 這條路。
把 `.env` 改成：

```
ADK_PROVIDER=litellm
ADK_MODEL=openai/openai/gpt-oss-120b
OPENAI_API_BASE=http://localhost:5000/v1
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
- Gemini API 金鑰（免費層就夠跑完全部教材）

免費層的額度用完時（`429`）該怎麼辦，兩軌的 README 各自寫在最後：
[概念軌](concept_to_expert/#撞到-429-怎麼辦)、[實作軌](30day_practice/#配額提醒)。
