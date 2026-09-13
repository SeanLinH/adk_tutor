# Day 15 · 讓人類插一腳：Human Input 與 Tool Confirmation

> 第三部・戰術編排　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 用 RequestInput 在圖裡停下來等人
2. 用 tool confirmation 讓工具需要人工核可
3. 分辨兩套 HITL 系統的適用場合

## 📌 文章沒講到、本日補上的部分

- ⚠️ 補上 **`invocation_id` 陷阱**：回覆沒帶對 id 會**靜默開一個新 invocation**，不會報錯——做成可重現的 demo
- ⚠️ 補上 `except BaseException` 會吞掉 `NodeInterruptedError`，讓 HITL 直接失效
- 補上在 Jupyter 裡模擬「暫停→人工回覆→恢復」的可執行寫法

## 檔案

- `day15.ipynb` — 主體

## 對應文章

`Day 15 - 讓人類插一腳：Human Input 與 Tool Confirmation.md`

---

[← Day 14](../day14_data_handling_dynamic_workflows/)　|　[30 天總覽](../README.md)　|　[Day 16 →](../day16_template_workflow_agents/)
