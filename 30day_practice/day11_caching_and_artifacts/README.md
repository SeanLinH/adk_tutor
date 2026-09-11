# Day 11 · Caching 與 Artifacts：省錢與管檔案的兩把工具

> 第二部・裝備升級　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 設定 ContextCacheConfig 並確認快取真的命中
2. 用 Artifact 把大東西移出 state
3. 用 LoadArtifactsTool 做延遲載入

## 📌 文章沒講到、本日補上的部分

- ⚠️ 補上第 01 章那個提示的完整解法：**每次 agent 交棒都會讓 prompt 前綴改變、快取全部失效**——多 agent 系統帳單爆掉的頭號原因
- 補上 cache hit 的實際觀測方法（文章只說「怎麼確認」沒給可跑的碼）
- 文章有一段 Kotlin，本日改寫成 Python

## 檔案

- `day11.ipynb` — 主體

## 對應文章

`Day 11 - Caching 與 Artifacts：省錢與管檔案的兩把工具.md`

---

[← Day 10](../day10_context_compaction/)　|　[30 天總覽](../README.md)　|　[Day 12 →](../day12_callbacks_events_plugins/)
