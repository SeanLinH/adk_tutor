# Day 08 · 資料落地：Grounding 與查證機制

> 第二部・裝備升級　|　⚠️ 部分需要 GCP，其餘可跑

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 用 google_search 做 grounding
2. 讀懂 groundingMetadata 的結構
3. 知道 Search Suggestions 的顯示義務

## 📌 文章沒講到、本日補上的部分

- 補上 `groundingMetadata` 的**真實 payload**（文章只有示意 JSON）
- ⚠️ 補上 **Search Suggestions 是強制顯示義務**，不做等於違反使用條款
- Agent Search 需要 GCP（AI Studio 不支援），本日標註並附可複製的程式碼
- ⚠️ 補上：**Search grounding 的免費配額跟一般模型呼叫是分開算的，而且緊很多**——撞到 429 時換模型也救不了

## 檔案

- `day08.ipynb` — 主體

## 對應文章

`Day 08 - 資料落地：Grounding 與查證機制.md`

---

[← Day 07](../day07_mcp_and_openapi/)　|　[30 天總覽](../README.md)　|　[Day 09 →](../day09_sessions/)
