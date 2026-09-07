# Day 06 · 賦予行動力：Custom Tools 與 Function Tools

> 第二部・裝備升級　|　✅ 完整可執行

## 前置需求

- 🔑 需要 Gemini API 金鑰

## 今天要學會

1. 寫出同步、長時間執行、以及 AgentTool 三種形態的工具
2. 用 BaseToolset 打包一組工具
3. 讓工具平行執行
4. 避開「一個 agent 只能有一個內建工具」的限制

## 📌 文章沒講到、本日補上的部分

- 補上工具 schema 的**實際輸出**（`_get_declaration()`），看清楚模型收到什麼
- 補上「平行執行需要工具**和** prompt 都寫成可平行」——只改一邊沒有用
- 補上 CPU-bound 工具用 ThreadPoolExecutor 卸載的實測差異

## 檔案

- `day06.ipynb` — 主體

## 對應文章

`Day 06 - 賦予行動力：Custom Tools 與 Function Tools.md`

---

[← Day 05](../day05_code_with_ai/)　|　[30 天總覽](../README.md)　|　[Day 07 →](../day07_mcp_and_openapi/)
