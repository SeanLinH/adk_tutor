"""Product Catalog Agent：另一個團隊維護的 A2A 服務。

刻意**不用 ADK、也不呼叫 LLM**，只用 `a2a-sdk` 手刻：
  * 證明 A2A 是協定而不是 ADK 的私有格式——任何框架只要講同一套 JSON-RPC 就能接
  * 行為是確定的（不耗 token），適合拿來看協定本身

單獨啟動（另開一個終端機）：
    uv run python servers/product_catalog_server.py --port 8941

三種行為，分別對應 A2A 的 Task 生命週期：
  * 訊息裡有 SKU        → WORKING → artifact → COMPLETED
  * 訊息裡沒有 SKU      → WORKING → INPUT_REQUIRED（回頭跟呼叫方要東西）
  * 訊息含「盤點」       → 長任務：每 0.5 秒回報一次進度，可被 CancelTask 中斷
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re

from a2a.helpers.proto_helpers import (
    new_data_part,
    new_task_from_user_message,
    new_text_message,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
from google.protobuf.json_format import MessageToDict
from starlette.applications import Starlette

CATALOG = {
    "A-100": {"name": "降噪耳機", "price": 3990, "stock": 42},
    "B-200": {"name": "機械鍵盤", "price": 2490, "stock": 0},
    "C-300": {"name": "4K 螢幕", "price": 11900, "stock": 7},
}
SKU_PATTERN = re.compile(r"[A-Z]-\d{3}")


def lookup(text: str) -> dict | None:
    """純函式版本的查詢邏輯。notebook 會拿它跟 A2A 版本比延遲。"""
    match = SKU_PATTERN.search(text.upper())
    if not match or match.group() not in CATALOG:
        return None
    sku = match.group()
    return {"sku": sku, **CATALOG[sku]}


def read_request_text(context: RequestContext) -> str:
    """把使用者訊息攤平成文字。

    ADK 的 RemoteA2aAgent 回覆 INPUT_REQUIRED 時，送來的是 FunctionResponse 轉成的
    JSON 字串；其他框架可能送 data part。兩種都接得住，才叫「跨框架」。
    """
    text = context.get_user_input()
    for part in context.message.parts:
        if part.HasField("data"):
            text += " " + json.dumps(MessageToDict(part.data), ensure_ascii=False)
    return text


class CatalogExecutor(AgentExecutor):
    """A2A server 的核心：收到請求 → 把狀態變化丟進 event_queue。"""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if task is None:
            # 第一次收到這個 task：先把 Task 物件本身發出去（狀態 SUBMITTED）
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        def say(text: str):
            return new_text_message(text, task_id=task.id, context_id=task.context_id)

        text = read_request_text(context)
        await updater.start_work(say("收到，查詢目錄中…"))

        if "盤點" in text:
            for i in range(1, 11):
                await asyncio.sleep(0.5)
                await updater.update_status(
                    TaskState.TASK_STATE_WORKING, say(f"盤點進度 {i * 10}%")
                )
            await updater.complete(say(f"盤點完成，共 {len(CATALOG)} 項商品"))
            return

        product = lookup(text)
        if product is None:
            # ⭐ 不是失敗：狀態停在 INPUT_REQUIRED，execute() 直接 return。
            #    呼叫方帶著同一個 task_id 補件，框架會再呼叫一次 execute()。
            await updater.requires_input(say("請提供商品編號（例如 A-100）"))
            return

        await updater.add_artifact([new_data_part(product)], name="product")
        status = "有貨" if product["stock"] else "缺貨"
        await updater.complete(
            say(f"{product['sku']} {product['name']}：NT${product['price']}，{status}（庫存 {product['stock']}）")
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # 框架已經先把 execute() 的 asyncio task 取消掉，這裡只負責宣告最終狀態。
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()


def build_card(host: str, port: int) -> AgentCard:
    """手寫 Agent Card。用 ADK 的 to_a2a() 時這張卡是自動產生的，這裡是另一個團隊自己寫。"""
    return AgentCard(
        name="product_catalog_agent",
        description="產品目錄服務：依商品編號（SKU）查詢品名、價格與庫存，也能做全品項盤點。",
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url=f"http://{host}:{port}/",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id="lookup_product",
                name="查詢產品",
                description="給一個 SKU（格式如 A-100），回傳品名、價格、庫存。缺 SKU 時會要求補件。",
                tags=["catalog", "inventory"],
                examples=["A-100 多少錢？", "B-200 還有貨嗎？"],
            ),
            AgentSkill(
                id="stocktake",
                name="全品項盤點",
                description="長時間任務，會持續回報進度，可取消。",
                tags=["catalog", "long-running"],
                examples=["幫我盤點"],
            ),
        ],
    )


def build_app(host: str = "localhost", port: int = 8941) -> Starlette:
    card = build_card(host, port)
    handler = DefaultRequestHandler(
        agent_executor=CatalogExecutor(),
        task_store=InMemoryTaskStore(),  # Task 的狀態存在這裡，GetTask 才查得到
        agent_card=card,
    )
    return Starlette(
        routes=[
            *create_agent_card_routes(card),  # GET  /.well-known/agent-card.json
            *create_jsonrpc_routes(handler, "/"),  # POST /  （JSON-RPC 2.0）
        ]
    )


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8941)
    args = parser.parse_args()
    uvicorn.run(build_app(args.host, args.port), host=args.host, port=args.port, log_level="warning")
