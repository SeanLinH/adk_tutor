# Day 10 · 像管理原始碼一樣管理 Context：壓縮與 Token 最佳化

> 第二部・裝備升級　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 用 EventsCompactionConfig 設定 token-based 壓縮與 sliding window
2. 換掉預設的摘要模型
3. 量出壓縮前後的 token 差異

## 📌 文章沒講到、本日補上的部分

- 補上**實際 token 數字**的量測（文章只講設定）
- ⚠️ 補上兩種策略**不對等**：token-based 會蓋過 sliding window
- 強調設定掛在 **`App`** 上，掛在 agent 上完全沒有作用

## 檔案

- `day10.ipynb` — 主體

## 對應文章

`Day 10 - 像管理原始碼一樣管理 Context：壓縮與 Token 最佳化.md`

---

[← Day 09](../day09_sessions/)　|　[30 天總覽](../README.md)　|　[Day 11 →](../day11_caching_and_artifacts/)
