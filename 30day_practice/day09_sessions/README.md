# Day 09 · Sessions 管理：對話狀態、Rewind 與 Schema 遷移

> 第二部・裝備升級　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 操作 Session 的四個核心屬性與生命週期
2. 用 EventActions(state_delta) 正確改 state
3. 在四種 SessionService 之間切換

## 📌 文章沒講到、本日補上的部分

- ⚠️ 補上 `SqliteSessionService` 的兩個坑：**不在 `__all__` 裡**（要從子模組 import）、參數是 **`db_path`** 不是 `DatabaseSessionService` 的 `db_url`
- 補上「直接改 `session.state` 為什麼在 InMemory 看起來有效、換 DB 就失效」的實驗
- ⚠️ 補上 `InMemoryMemoryService` 是**字詞重疊比對而非語意搜尋**，而且 `\w+` 斷不開中文——中文查詢實質上永遠命中不了

## 檔案

- `day09.ipynb` — 主體

## 對應文章

`Day 09 - Sessions 管理：對話狀態、Rewind 與 Schema 遷移.md`

---

[← Day 08](../day08_grounding/)　|　[30 天總覽](../README.md)　|　[Day 10 →](../day10_context_compaction/)
