"""Customer Service Agent：同時扮演 Consuming 與 Exposing 兩個角色。

  * Consuming：用 RemoteA2aAgent 接上 product_catalog_server（另一個程序）
  * Exposing ：自己再用 to_a2a() 開出去，讓任何 A2A client 呼叫

呼叫鏈：  A2A client ──HTTP──▶ 本服務 (ADK) ──HTTP──▶ product_catalog (a2a-sdk)

單獨啟動（先啟動 product_catalog_server.py）：
    uv run python servers/customer_service_server.py --port 8942 --catalog-port 8941
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from shared import get_model, quiet  # noqa: E402

quiet()

from google.adk.a2a.utils.agent_to_a2a import to_a2a  # noqa: E402
from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent  # noqa: E402


def build_agent(catalog_port: int) -> LlmAgent:
    product_catalog = RemoteA2aAgent(
        name="product_catalog",
        # ⚠️ 必須跟對方卡片上宣告的 host 完全一致（localhost ≠ 127.0.0.1，見 Day 20）
        agent_card=f"http://localhost:{catalog_port}/.well-known/agent-card.json",
        description="產品目錄服務：依 SKU 查詢品名、價格、庫存。",
    )
    return LlmAgent(
        name="customer_service_agent",
        model=get_model(),
        description="電商客服：回答產品價格與庫存問題。",
        instruction=(
            "你是電商客服。凡是產品價格、庫存的問題，一律轉給 product_catalog，"
            "拿到結果後用繁體中文、一到兩句話回覆顧客。"
        ),
        sub_agents=[product_catalog],
    )


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8942)
    parser.add_argument("--catalog-port", type=int, default=8941)
    args = parser.parse_args()

    # ⭐ Exposing 只有這一行；Agent Card 會從 agent 的 name / description / sub_agents 自動產生
    app = to_a2a(build_agent(args.catalog_port), host=args.host, port=args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
