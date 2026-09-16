# Day 16 · 老前輩的實力：Template Workflow Agents

> 第三部・戰術編排　|　✅ 完整可執行

> 📌 本日的三個 agent 在 ADK 2.8.0 已 deprecated，但建議**先讀本日再讀 [Day 13](../day13_graph_workflows/)**。

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 用 SequentialAgent / ParallelAgent / LoopAgent 組流程
2. 知道 LoopAgent 的停止責任在誰身上
3. 知道三個都不夠用時怎麼繼承 BaseAgent

## 📌 文章沒講到、本日補上的部分

- ⚠️ 補上：這三個在 **ADK Python 2.8.0 已正式 deprecated**，每個範例都標註對應的 Graph 寫法
- 📌 **建議先讀本日再讀 Day 13**——這三個是跨語言共通的原語，是理解圖的墊腳石
- 補上 ParallelAgent 分支之間**看不到彼此 state** 的實驗
- ⚠️ 補上「**一個 agent 只能有一個父節點**」：想換個編排方式重跑同一批 agent，不能重用實例，要寫成工廠函式

## 檔案

- `day16.ipynb` — 主體

## 對應文章

`Day 16 - 老前輩的實力：Template Workflow Agents.md`

---

[← Day 15](../day15_human_in_the_loop/)　|　[30 天總覽](../README.md)　|　[Day 17 →](../day17_multi_agent_patterns/)
