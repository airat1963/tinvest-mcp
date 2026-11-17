"""Handlers MCP-инструментов. Только бизнес-логика, без протокола."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .api import (
    compute_rate_shift,
    fetch_bonds_positions,
    fetch_last_close,
    make_client,
    resolve_account_id,
)


def tool_get_bonds_positions(account_id: str | None = None) -> dict:
    """Позиции по облигациям: тикер, кол-во, номинал, дюрация, погашение."""
    with make_client() as cl:
        sb = cl.sandbox
        acc = account_id or resolve_account_id(sb)
        bonds = fetch_bonds_positions(sb, acc)
        return {"account_id": acc, "bonds": bonds, "count": len(bonds)}


def tool_get_last_close(figi: str, lookback_days: int = 15) -> dict:
    """Цена закрытия последней дневной свечи по FIGI (в % от номинала)."""
    with make_client() as cl:
        return fetch_last_close(cl, figi, lookback_days=lookback_days)


def tool_estimate_rate_shift(shift_pp: float, account_id: str | None = None) -> dict:
    """Оценка ΔP ≈ -D_mod·P·Δy по портфелю ОФЗ.

    shift_pp: сдвиг ставки в процентных пунктах (например, 0.25 или -0.5).
    """
    try:
        shift = Decimal(str(shift_pp))
    except InvalidOperation as e:
        raise ValueError(f"shift_pp должен быть числом, получено {shift_pp!r}") from e

    with make_client() as cl:
        sb = cl.sandbox
        acc = account_id or resolve_account_id(sb)
        bonds = fetch_bonds_positions(sb, acc)

        closes: dict[str, Decimal] = {}
        for b in bonds:
            info = fetch_last_close(cl, b["figi"])
            if info["close_pct"] is not None:
                closes[b["figi"]] = Decimal(info["close_pct"])

        return compute_rate_shift(bonds, closes, shift)