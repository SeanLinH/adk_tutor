# Day 17 · 七種分工方式：Multi-Agent Workflow Patterns

> 第三部・戰術編排　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 認得七種多 agent 模式並說出各自的適用場合
2. 把每個模式對應到具體的 ADK 元件
3. 知道「下一步由誰決定」才是這七種模式真正的分類軸

## 📌 文章沒講到、本日補上的部分

- ⚠️ 文章的 Agent Routing 補充框是 **TypeScript 專屬**（`RoutedAgent`/`RoutedLlm`），Python 沒有。本日改用 LLM transfer + graph 條件路由的 Python 等價寫法，並實際跑出 `ImportError` 佐證
- 文章七個模式只有片段程式碼，本日**每個模式都給一個可執行的最小範例**
- 補上「交棒（`sub_agents`）控制權不回來、`AgentTool` 會回來」這個分水嶺——模式 2 與模式 4 的真正差別
- ⚠️ 補上圖路由的隱藏坑：使用者輸入**不會**自動變成 `@node` 的參數，得先進 session state，否則 `not found in state`
- 補上 `disallow_transfer_to_parent` / `disallow_transfer_to_peers`：交棒是可以鎖的，以及鎖死的後果

## 檔案

- `day17.ipynb` — 主體

## 對應文章

`Day 17 - 七種分工方式：Multi-Agent Workflow Patterns.md`

---

[← Day 16](../day16_template_workflow_agents/)　|　[30 天總覽](../README.md)　|　[Day 18 →](../day18_collaborative_workflows/)
