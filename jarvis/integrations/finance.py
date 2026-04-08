"""Finance integration via Plaid (free tier available).

Required env vars:
  PLAID_CLIENT_ID
  PLAID_SECRET
  PLAID_ENV        — sandbox | development | production (default: sandbox)
  PLAID_ACCESS_TOKEN — (obtained after OAuth flow)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _plaid_client():
    from plaid.api import plaid_api  # type: ignore[import]
    from plaid.configuration import Configuration  # type: ignore[import]
    from plaid.api_client import ApiClient  # type: ignore[import]

    env_map = {
        "sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com",
    }
    env = os.getenv("PLAID_ENV", "sandbox")
    config = Configuration(
        host=env_map.get(env, env_map["sandbox"]),
        api_key={
            "clientId": os.environ["PLAID_CLIENT_ID"],
            "secret": os.environ["PLAID_SECRET"],
        },
    )
    return plaid_api.PlaidApi(ApiClient(config))


def _access_token() -> str:
    token = os.getenv("PLAID_ACCESS_TOKEN", "")
    if not token:
        raise ValueError(
            "PLAID_ACCESS_TOKEN not set. Complete the Plaid OAuth flow first."
        )
    return token


class FinanceGetBalanceTool(Tool):
    name = "finance_get_balance"
    description = "Get current account balances from your bank via Plaid."
    parameters = {"type": "object", "properties": {}}

    async def execute(self) -> str:
        try:
            from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest  # type: ignore[import]

            client = _plaid_client()
            request = AccountsBalanceGetRequest(access_token=_access_token())
            response = client.accounts_balance_get(request)
            lines = []
            for account in response["accounts"]:
                name = account["name"]
                balance = account["balances"]["current"]
                currency = account["balances"].get("iso_currency_code", "USD")
                lines.append(f"• {name}: {currency} {balance:,.2f}")
            return "\n".join(lines) or "No accounts found."
        except Exception as exc:
            logger.error("finance_get_balance failed: %s", exc)
            return f"Error getting balance: {exc}"


class FinanceListTransactionsTool(Tool):
    name = "finance_list_transactions"
    description = "List recent bank transactions."
    parameters = {
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Days of history (default 30)"},
            "limit": {"type": "integer", "description": "Max transactions (default 20)"},
        },
    }

    async def execute(self, days: int = 30, limit: int = 20) -> str:
        try:
            from plaid.model.transactions_get_request import TransactionsGetRequest  # type: ignore[import]
            from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions  # type: ignore[import]

            client = _plaid_client()
            end = datetime.now().date()
            start = (datetime.now() - timedelta(days=days)).date()
            options = TransactionsGetRequestOptions(count=limit)
            request = TransactionsGetRequest(
                access_token=_access_token(),
                start_date=start,
                end_date=end,
                options=options,
            )
            response = client.transactions_get(request)
            transactions = response["transactions"]
            if not transactions:
                return "No transactions found."
            lines = []
            for tx in transactions:
                date = tx["date"]
                name = tx["name"]
                amount = tx["amount"]
                lines.append(f"• {date} {name}: ${amount:,.2f}")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("finance_list_transactions failed: %s", exc)
            return f"Error listing transactions: {exc}"


class FinanceSpendingSummaryTool(Tool):
    name = "finance_spending_summary"
    description = "Get a spending summary by category for a recent period."
    parameters = {
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Days to analyze (default 30)"},
        },
    }

    async def execute(self, days: int = 30) -> str:
        try:
            from plaid.model.transactions_get_request import TransactionsGetRequest  # type: ignore[import]

            client = _plaid_client()
            end = datetime.now().date()
            start = (datetime.now() - timedelta(days=days)).date()
            request = TransactionsGetRequest(
                access_token=_access_token(),
                start_date=start,
                end_date=end,
            )
            response = client.transactions_get(request)
            transactions = response["transactions"]

            spending: dict[str, float] = {}
            for tx in transactions:
                if tx["amount"] > 0:  # Positive = debit
                    cats = tx.get("category") or ["Uncategorized"]
                    cat = cats[0] if cats else "Uncategorized"
                    spending[cat] = spending.get(cat, 0.0) + tx["amount"]

            if not spending:
                return "No spending data found."
            sorted_spending = sorted(spending.items(), key=lambda x: x[1], reverse=True)
            total = sum(spending.values())
            lines = [f"• {cat}: ${amount:,.2f}" for cat, amount in sorted_spending]
            lines.append(f"\nTotal spending: ${total:,.2f}")
            return f"Spending summary (last {days} days):\n" + "\n".join(lines)
        except Exception as exc:
            logger.error("finance_spending_summary failed: %s", exc)
            return f"Error getting spending summary: {exc}"


class FinanceIntegration(Integration):
    name = "finance"

    def is_configured(self) -> bool:
        return bool(os.getenv("PLAID_CLIENT_ID") and os.getenv("PLAID_SECRET"))

    def get_tools(self) -> list[Tool]:
        return [
            FinanceGetBalanceTool(),
            FinanceListTransactionsTool(),
            FinanceSpendingSummaryTool(),
        ]
