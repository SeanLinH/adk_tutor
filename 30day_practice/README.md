# 30 天實作軌

對應 30 篇連載文章，**一天一個資料夾、各自獨立**。可以從任何一天開始，
不需要照順序讀——每天的 notebook 都自己重複一次環境設定。

想先建立整體觀念，請走 [`../concept_to_expert/`](../concept_to_expert/)。
兩軌互補，不互相依賴。

## 每天的結構

```
dayNN_slug/
├── README.md      學習目標 / 前置需求 / 本日補了什麼
└── dayNN.ipynb    1 概念 → 2 最小範例 → 3 逐步加深
                   → 4 📌 文章沒講到的補充 → 5 常見錯誤
                   → 6 動手練習 → 本日回顧
```

第 4 節「文章沒講到的補充」是這一軌的重點——文章受篇幅限制沒展開、
或是官方文件埋在 Caution 裡的坑，都補在那裡。

## 目前進度

**Day 01 – 30 全部完整實作**，每一格都實際執行過、輸出留在檔案裡。

| 狀態 | 天數 |
|---|---|
| ✅ 完整實作並執行驗證 | Day 01 – 30 |

> 全部 30 天都在 **google-adk 2.8.0 / Python 3.13** 上重跑驗證過。
> 若你的版本不同，`📌 補充` 段落裡那些「翻原始碼查證」的格子會直接反映**你安裝的版本**——
> 那正是它們被寫成程式而不是寫死文字的原因。

## 圖例

**前置需求**

🔑 需要 Gemini API 金鑰　☁️ 需要 Google Cloud 專案　💻 會用到終端機／子程序　📦 需要額外套件或服務　🌐 部分內容需要瀏覽器

**可執行性**

- ✅ 完整可執行
- 🧠 概念為主，附自製可執行實驗
- 💻 以 CLI／子程序實跑
- 🔀 需要兩個程序（notebook 自動起停）
- ⚠️ 部分需要 GCP，其餘可跑
- 🛠️ 工具設定為主
- 🌐 設定可跑，即時互動需瀏覽器


## 第一部・新兵入伍

> 跑起來：環境、第一個 agent、開發介面

| Day | 主題 | 可執行性 | 需要 |
|---|---|---|---|
| 01 | [遇見 Google ADK 2.0](day01_meet_adk2/) | 🧠 概念為主，附自製可執行實驗 | 🔑 |
| 02 | [武器庫點交：環境建置與 Agents CLI](day02_environment_and_cli/) | 💻 以 CLI／子程序實跑 | 🔑 💻 |
| 03 | [你的第一個智能助理：Agent 定義與模型設定](day03_first_agent_and_models/) | ✅ 完整可執行 | 🔑 |
| 04 | [視覺化戰情室：Runtime、Web UI 與 Visual Builder](day04_runtime_web_ui/) | 💻 以 CLI／子程序實跑 | 🔑 💻 |
| 05 | [AI 輔助開發：Code with AI](day05_code_with_ai/) | 🛠️ 工具設定為主 | — |

## 第二部・裝備升級

> 讓它能做事：工具、外部協定、記憶與事件

| Day | 主題 | 可執行性 | 需要 |
|---|---|---|---|
| 06 | [賦予行動力：Custom Tools 與 Function Tools](day06_custom_tools/) | ✅ 完整可執行 | 🔑 |
| 07 | [開放協定：MCP 與 OpenAPI 整合](day07_mcp_and_openapi/) | 🔀 需要兩個程序（notebook 自動起停） | 🔑 📦 |
| 08 | [資料落地：Grounding 與查證機制](day08_grounding/) | ⚠️ 部分需要 GCP，其餘可跑 | 🔑 |
| 09 | [Sessions 管理：對話狀態、Rewind 與 Schema 遷移](day09_sessions/) | ✅ 完整可執行 | 🔑 |
| 10 | [像管理原始碼一樣管理 Context：壓縮與 Token 最佳化](day10_context_compaction/) | ✅ 完整可執行 | 🔑 |
| 11 | [Caching 與 Artifacts：省錢與管檔案的兩把工具](day11_caching_and_artifacts/) | ✅ 完整可執行 | 🔑 |
| 12 | [事件驅動架構：Callbacks、Events 與 Plugins](day12_callbacks_events_plugins/) | ✅ 完整可執行 | 🔑 |

## 第三部・戰術編排

> 多個 agent 怎麼協作：圖、模式、跨程序

| Day | 主題 | 可執行性 | 需要 |
|---|---|---|---|
| 13 | [告別失控的 AI：Graph Workflows 與 Graph Routes](day13_graph_workflows/) | ✅ 完整可執行 | 🔑 |
| 14 | [資料怎麼流：Data Handling 與 Dynamic Workflows](day14_data_handling_dynamic_workflows/) | ✅ 完整可執行 | 🔑 |
| 15 | [讓人類插一腳：Human Input 與 Tool Confirmation](day15_human_in_the_loop/) | ✅ 完整可執行 | 🔑 |
| 16 | [老前輩的實力：Template Workflow Agents](day16_template_workflow_agents/) | ✅ 完整可執行 | 🔑 |
| 17 | [七種分工方式：Multi-Agent Workflow Patterns](day17_multi_agent_patterns/) | ✅ 完整可執行 | 🔑 |
| 18 | [打造一支 Agent 團隊：Collaborative Workflows 與 Agent Modes](day18_collaborative_workflows/) | ✅ 完整可執行 | 🔑 |
| 19 | [跨程序的握手：認識 A2A Protocol](day19_a2a_protocol/) | 🧠 概念為主，附自製可執行實驗 | 🔑 |
| 20 | [動手接上遠端 Agent：A2A Exposing 與 Consuming](day20_a2a_exposing_consuming/) | 🔀 需要兩個程序（notebook 自動起停） | 🔑 📦 |

## 第四部・特種作戰

> 即時語音、多模態、常駐執行、能力包

| Day | 主題 | 可執行性 | 需要 |
|---|---|---|---|
| 21 | [Live and Voice Agents：跟 Gemini 講電話](day21_live_and_voice/) | 🌐 設定可跑，即時互動需瀏覽器 | 🔑 🌐 |
| 22 | [RunConfig 深潛：BIDI、Session Resumption 與 Streaming Tools](day22_runconfig_deep_dive/) | ✅ 完整可執行 | 🔑 |
| 23 | [Audio, Images, Video：讓 Agent 真的能聽能看](day23_audio_images_video/) | 🌐 設定可跑，即時互動需瀏覽器 | 🔑 🌐 |
| 24 | [沒人盯著的時候：Ambient Agents、Event Loop 與 Resume](day24_ambient_agents_resume/) | 💻 以 CLI／子程序實跑 | 🔑 💻 |
| 25 | [Agent Skills 與生態：按需載入的能力包](day25_agent_skills/) | ✅ 完整可執行 | 🔑 |

## 第五部・實彈演習

> 上線該有的樣子：評估、模擬、安全、觀測、部署

| Day | 主題 | 可執行性 | 需要 |
|---|---|---|---|
| 26 | [評估與最佳化：讓 Agent 的品質可以被測量](day26_evaluation_and_optimization/) | 💻 以 CLI／子程序實跑 | 🔑 💻 |
| 27 | [模擬器：連使用者和後端都能假造](day27_simulators/) | ✅ 完整可執行 | 🔑 |
| 28 | [企業級安全網：誰能替 Agent 的行為負責](day28_enterprise_security/) | ⚠️ 部分需要 GCP，其餘可跑 | 🔑 |
| 29 | [系統觀測力：Log、Metric、Trace 三支柱](day29_observability/) | ⚠️ 部分需要 GCP，其餘可跑 | 🔑 |
| 30 | [終極部署：把 Agent 送上戰場](day30_deployment/) | 💻 以 CLI／子程序實跑 | ☁️ 💻 |

## 幾個跨天的注意事項

- **建議先讀 Day 16 再讀 Day 13。** Sequential / Parallel / Loop 是跨語言共通的原語，
  也是理解 Graph Workflow 的墊腳石。
- **Day 17 和 Day 24 的部分內容是 TypeScript 專屬**（`RoutedAgent`、`AbortSignal`），
  Python 沒有對應 API。兩天的 notebook 都會標註並給 Python 的等價做法。
- **Day 16 的三個 workflow agent 在 ADK Python 2.8.0 已正式 deprecated**，
  範例仍可執行，但每個都標註了對應的 Graph 寫法。

## 配額提醒

免費層有幾個獨立計算的配額，很容易誤判：

| 配額 | 行為 |
|---|---|
| 一般模型呼叫 | **每個模型分開算**——`gemini-2.5-flash` 用完了，換 `gemini-flash-lite-latest` 還能跑 |
| Google Search grounding | **獨立且緊很多**，換模型救不了（影響 Day 08） |

```python
from shared import pick_available_model
import os
os.environ["ADK_MODEL"] = pick_available_model()   # 自動探測還有配額的模型
```

`shared/runtime.py` 另外有一道全域節流（預設 12 RPM），設 `ADK_RPM=0` 可關閉。

## 素材來源

- 30 篇連載文章（`wiki/moc/`）— 敘事主線
- `wiki/` 根目錄的 51 篇 API 參考筆記 — 比文章更深的細節
- `wiki/review/` 的實測報告 — 「新手照著做會卡在哪」
