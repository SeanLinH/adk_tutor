# Day 07 · 開放協定：MCP 與 OpenAPI 整合

> 第二部・裝備升級　|　🔀 需要兩個程序（notebook 自動起停）

## 前置需求

- 🔑 需要 Gemini API 金鑰
- 📦 需要額外套件或服務

## 今天要學會

1. 用 McpToolset 把 ADK 當成 MCP client
2. 把 ADK agent 包成 MCP server 給別人用
3. 用 OpenAPIToolset 從 spec 自動生工具

## 📌 文章沒講到、本日補上的部分

- ⚠️ 補上**部署陷阱**：用 `McpToolset` 的 agent 必須**同步定義**，寫成 async 在本地 `adk web` 會過、部署會炸。做成 ✅/❌ 對照 cell
- MCP server 需要子程序，本日用背景 subprocess 起服務、notebook 當 client，結尾清理

## 檔案

- `day07.ipynb` — 主體

## 對應文章

`Day 07 - 開放協定：MCP 與 OpenAPI 整合.md`

---

[← Day 06](../day06_custom_tools/)　|　[30 天總覽](../README.md)　|　[Day 08 →](../day08_grounding/)
