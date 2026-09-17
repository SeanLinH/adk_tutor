# Day 19 · 跨程序的握手：認識 A2A Protocol

> 第三部・戰術編排　|　🔀 真實跨程序：notebook 會起兩個 A2A server 子程序，最後自動關閉

## 前置需求

- 🔑 需要 Gemini API 金鑰（第 9 節之後才用到）
- 📦 需要 `google-adk[a2a]`（`uv sync` 即可，pyproject 已包含）

## 今天要學會

1. 判斷該用 A2A 還是 local sub-agent，並用**實測延遲**說明代價
2. 看懂 A2A 在線上真正傳的東西：Agent Card、JSON-RPC、Task、SSE 串流
3. 親手走一遍 Task 生命週期：`INPUT_REQUIRED` 補件、長任務串流、中途取消
4. 知道 `RemoteA2aAgent` 把 A2A 的每一種回應翻譯成哪一種 ADK Event
5. 讓一支 agent 同時 consuming 與 exposing，串起三個程序

## 架構

```
notebook ──HTTP──▶ customer_service_server (:8942, ADK + to_a2a)
   │                        │
   │                        └──HTTP──▶ product_catalog_server (:8941, 純 a2a-sdk，無 ADK、無 LLM)
   └────────────HTTP───────────────────▲
```

產品目錄刻意**不用 ADK** 寫，證明 A2A 是跨框架的協定，不是 ADK 的私有格式。

## 📌 文章沒講到、本日補上的部分

- 文章零程式碼。本日起**兩個真的 A2A server**，不是同程序的 mock
- 用 `httpx` **手刻 JSON-RPC**，看清楚線上真正傳的 `SendMessage` / `SendStreamingMessage` / `GetTask` / `CancelTask`
- ⚠️ 手刻請求**必須帶 `A2A-Version: 1.0` header**，否則會收到 `-32009`（server 會把請求當成 0.3 版）
- ⚠️ **`taskId` 續接工作、`contextId` 續接對話**：只帶 `contextId` 補件，server 會開一個新 task
- ⚠️ ADK 端遇到 `INPUT_REQUIRED` 會收到一個 long-running 的 `mock_function_call_for_required_user_input`，**要用 `FunctionResponse` 回覆**才會續接同一個 task
- ⚠️ `data` part 是 protobuf `Struct`，**整數會變成 float**（`42` → `42.0`）
- 把文章的三個核心能力對到實際的 ADK Event：進度訊息 → `thought=True`、artifact → `inline_data`、補件 → long-running function call
- ⚠️ `to_a2a()` 的 Agent Card 會列出內部 sub_agent，task history 會把整條內部呼叫鏈與下游原始資料回傳給外部 client
- 實測「同一段邏輯，本地呼叫 vs A2A」的延遲（同機器約差上千倍），用數字回答文章的 `DataValidator` 反例

## 檔案

- `day19.ipynb` — 主體
- `servers/product_catalog_server.py` — 「另一個團隊」的服務（`a2a-sdk` 的 `AgentExecutor` + `TaskUpdater`）
- `servers/customer_service_server.py` — ADK `LlmAgent`，用 `RemoteA2aAgent` 消費、用 `to_a2a()` 暴露

也可以另開終端機自己跑：

```bash
cd 30day_practice/day19_a2a_protocol
uv run python servers/product_catalog_server.py --port 8941
uv run python servers/customer_service_server.py --port 8942 --catalog-port 8941

curl -s localhost:8941/.well-known/agent-card.json
curl -s localhost:8941/ -H 'A2A-Version: 1.0' -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":1,"method":"SendMessage",
  "params":{"message":{"messageId":"m1","role":"ROLE_USER","parts":[{"text":"A-100 多少錢？"}]}}}'
```

## 對應文章

`Day 19 - 跨程序的握手：認識 A2A Protocol.md`

---

[← Day 18](../day18_collaborative_workflows/)　|　[30 天總覽](../README.md)　|　[Day 20 →](../day20_a2a_exposing_consuming/)
