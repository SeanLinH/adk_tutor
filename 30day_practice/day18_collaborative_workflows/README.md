# Day 18 · 打造一支 Agent 團隊：Collaborative Workflows 與 Agent Modes

> 第三部・戰術編排　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 跟著四個步驟把單一 agent 長成一支團隊
2. 分辨三種 Agent Mode 的差異
3. 理解 context 隔離對行為的影響

## 📌 文章沒講到、本日補上的部分

- 補上最關鍵的一格實測：**`mode` 會改變 parent 實際拿到的 `tools`**（`chat` 不加、`single_turn` 加 `_SingleTurnAgentTool`、`task` 加 `_TaskAgentTool`）——這是三種 mode 的真正差別
- ⚠️ **更正流傳的說法**：「`task` mode 在 graph workflow 裡自 Python 2.0.0 起停用」在 **2.8.0 實測不成立**，`LlmAgent(mode="task")` 可以當節點；真正寫死的限制是 `RemoteA2aAgent` 的 task mode 不能當獨立節點（附原始碼佐證）
- 補上 Managed Agents 是 **Preview** 狀態的實際意義：只支援伺服器端工具，你自己的 `FunctionTool` 會被拒絕
- 補上 context 隔離的**實測對照**：同一個問題，`chat` 的 sub-agent 看得到使用者原話，`single_turn` 只拿得到 parent 轉述的那一句
- 文章用 LiteLLM 示範多模型，本日補上只用一把 Gemini 金鑰也能跑的異質團隊（便宜模型分類 + 好模型寫字）

## 檔案

- `day18.ipynb` — 主體

## 對應文章

`Day 18 - 打造一支 Agent 團隊：Collaborative Workflows 與 Agent Modes.md`

---

[← Day 17](../day17_multi_agent_patterns/)　|　[30 天總覽](../README.md)　|　[Day 19 →](../day19_a2a_protocol/)
