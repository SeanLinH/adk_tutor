# 概念軌：從觀念到能動手

由淺入深、**線性閱讀**的 12 章。目標是建立 ADK 的整體心智模型——
看完你會知道每個元件為什麼存在、彼此怎麼接。

想針對單一主題深入、或跟著 30 天連載走，請看
[`../30day_practice/`](../30day_practice/)。兩軌互補，不互相依賴。

## 學習地圖

```
00 環境設定  ─────────────────────────────  先跑通這一章
│
├─ Layer 1：一個 Agent 由什麼構成
│   01 身分（name / description / instruction）
│   02 工具（FunctionTool、ToolContext、內建工具）
│   03 模型與結構化輸出（retry、temperature、output_schema）
│
├─ Layer 2：它怎麼跑起來
│   04 Runner / Session / State
│   05 Memory / Artifact
│   06 App / Callbacks / Plugins
│
└─ Layer 3：多個 Agent 怎麼合作
    07 Sequential / Parallel / Loop
    08 Orchestration（流程寫死）
    09 Coordination（模型決定）
    10 Graph Workflows（ADK 2.0 的圖形引擎）
    11 綜合實作 + 離開 notebook
```

## 章節一覽

| # | 檔案 | 你會學到 | 關鍵坑 |
|---|---|---|---|
| 00 | `00_setup.ipynb` | 事件串流怎麼讀、`shared` 的 helper | `part.thought` 不該顯示給使用者；配額是**每個模型分開算**的 |
| 01 | `01_agent_basics.ipynb` | Agent 的三個身分欄位 | `description` 是**路由表**不是註解；`{var?}` 的問號救命 |
| 02 | `02_tools.ipynb` | 函式→工具的自動轉換 | docstring 是**送給模型的 API 文件**；內建工具不能跟自訂工具混用 |
| 03 | `03_models_and_output.ipynb` | 模型設定、結構化輸出 | ADK **預設不重試**（且只有模型物件掛得上）；模型會下架 |
| 04 | `04_runtime_session.ipynb` | Session、State 作用域 | 不能直接改 `session.state`；`SqliteSessionService` 參數是 `db_path` 不是 `db_url` |
| 05 | `05_memory_artifacts.ipynb` | 長期記憶與檔案 | Memory **不是自動的**；⚠️ `InMemoryMemoryService` 是關鍵字比對、**對中文幾乎失效** |
| 06 | `06_app_callbacks_plugins.ipynb` | 橫切關注 | ⚠️ **Plugin 一定先於 agent callback（before/after 都是），而且會短路它** |
| 07 | `07_workflow_agents.ipynb` | 三種內建編排 | `LoopAgent` 自己不會停；`ParallelAgent` 分支看不到彼此；**一個 agent 只能有一個父節點** |
| 08 | `08_orchestration.ipynb` | 流程型多 agent | 流程寫死 = 不會應變，這是特性不是 bug |
| 09 | `09_coordination.ipynb` | LLM 自主委派 | 交棒**預設單向**，交出去回不來 |
| 10 | `10_graph_workflows.ipynb` | ADK 2.0 圖形引擎 | 輸出在 `event.output` 不是 `event.content`；路由靠 `ctx.route` |
| 11 | `11_capstone.ipynb` | 專案結構、`adk run` | `agent.py` 的變數一定要叫 `root_agent`；`state[output_key]` 是 dict 不是 JSON 字串 |

## 開始之前

```bash
uv sync                     # 需要 google-adk 2.8+
cp .env.example .env        # 填入 GOOGLE_API_KEY
```

金鑰到 <https://aistudio.google.com/apikey> 免費申請。
若 shell 已經 `export GEMINI_API_KEY`，`.env` 可以留空。

### 撞到 429 怎麼辦

免費層有兩種**分開計算**的配額：

- **一般模型呼叫**：每個模型各自算，換一個模型 ID 通常就過了，不必等隔天。
- **Google Search grounding**：獨立額度而且緊很多，**換模型救不了**（影響第 02 章的搜尋小節，該節已做成失敗也能往下讀）。

自動探測還有配額的模型：

```python
from shared import pick_available_model
import os
os.environ["ADK_MODEL"] = pick_available_model()   # 自動探測還有配額的
```

或直接改 `.env` 的 `ADK_MODEL`，或 `shared/config.py` 的 `DEFAULT_MODEL`。

本教材另外在 `shared/runtime.py` 的 `ask()` 放了一道全域節流閘門
（預設 12 RPM），設 `ADK_RPM=0` 可關閉。

## 相關

- `../demo/` — 兩支 Streamlit 視覺化 app，對應第 08、09 章
- `../docs/speech_preparing.md` — 這個三層敘事的原始講稿
- `_archive/` — 舊版教材，已被本系列取代，保留備查
