"""Обёртки над t_tech.invest 1.51.0 с проверками типов.

Все грабли SDK собраны здесь:
- get_candles -> resp.candles (НЕ list(resp))
- total_amount_currencies -> MoneyValue (НЕ список)
- Bond.nominal -> MoneyValue
- Bond.maturity_date -> datetime, now().date() -> date (нужен .date())
- Bond.duration -> дни (>100 => делить на 365)
"""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal
from typing import Any

from t_tech.invest import CandleInterval, Client, InstrumentStatus
from t_tech.invest.utils import now, quotation_to_decimal
#from t_tech.invest import CandleInterval, Client, InstrumentStatus


# ---------- примитивы ----------

def money_to_decimal(mv) -> Decimal:
    """MoneyValue | Quotation -> Decimal."""
    return Decimal(mv.units) + Decimal(mv.nano) / Decimal(10**9)


def quotation_pct_to_decimal(q) -> Decimal:
    """Quotation цены облигации (% от номинала) -> Decimal."""
    return quotation_to_decimal(q)


# def duration_to_years(dur_raw: Any, fallback_years: float) -> Decimal:
#     """Bond.duration в 1.51.0 обычно в днях. >100 => дни, иначе уже годы."""
#     if dur_raw:
#         val = Decimal(str(dur_raw))
#         return val / Decimal(365) if val > Decimal(100) else val
#     return Decimal(str(max(fallback_years, 0.5)))
def duration_to_years(dur_raw: Any, fallback_years: float) -> tuple[Decimal, str]:
    """Bond.duration в 1.51.0 обычно в днях. >100 => дни, иначе уже годы.

    Возвращает (годы, источник): 'api' если duration пришёл, 'maturity_proxy' иначе.
    """
    if dur_raw:
        val = Decimal(str(dur_raw))
        years = val / Decimal(365) if val > Decimal(100) else val
        return years, "api"
    return Decimal(str(max(fallback_years, 0.5))), "maturity_proxy"

def years_to_maturity(bond) -> float:
    """Bond.maturity_date (datetime) минус today (date) -> годы."""
    m = bond.maturity_date
    if hasattr(m, "date"):
        m = m.date()
    return max((m - now().date()).days / 365.0, 0.5)


# ---------- клиент ----------

def make_client() -> Client:
    token = os.getenv("T_SANDBOX_TOKEN")
    if not token:
        raise RuntimeError("T_SANDBOX_TOKEN не задан")
    return Client(token.strip())


def resolve_account_id(sb) -> str:
    """Фиксированный из env или первый из песочницы."""
    fixed = os.getenv("T_SANDBOX_ACCOUNT_ID")
    if fixed:
        return fixed
    accounts = sb.get_sandbox_accounts().accounts
    if not accounts:
        raise RuntimeError("Нет счетов в песочнице — создайте через open_sandbox_account")
    return accounts[0].id


# ---------- данные ----------

# def fetch_bonds_positions(sb, account_id: str) -> list[dict]:
#     """Позиции только по облигациям, с номиналом и дюрацией из справочника."""
#     positions = sb.get_sandbox_positions(account_id=account_id)
#     bond_positions = [
#         p for p in positions.securities
#         if getattr(p, "instrument_type", "") == "bond"
#     ]
#     if not bond_positions:
#         return []

#     # справочник облигаций — один запрос, чтобы не дёргать bond_by на каждую
#     all_bonds = {}
#     for b in sb._client.instruments.bonds().instruments:  # type: ignore[attr-defined]
#         all_bonds[b.figi] = b

#     result = []
#     for p in bond_positions:
#         b = all_bonds.get(p.figi)
#         if b is None:
#             continue
#         nominal = money_to_decimal(b.nominal)  # MoneyValue, НЕ список
#         d_mod = duration_to_years(getattr(b, "duration", None), years_to_maturity(b))
#         result.append({
#             "figi": p.figi,
#             "ticker": b.ticker,
#             "name": b.name,
#             "qty": p.balance,
#             "nominal_rub": str(nominal),
#             "duration_years": str(d_mod),
#             "maturity_date": (
#                 b.maturity_date.date().isoformat()
#                 if hasattr(b.maturity_date, "date")
#                 else str(b.maturity_date)
#             ),
#         })
#     return result
def fetch_bonds_positions(cl: Client, sb, account_id: str) -> list[dict]:
    """Позиции только по облигациям, с номиналом и дюрацией из справочника."""
    positions = sb.get_sandbox_positions(account_id=account_id)
    bond_positions = [
        p for p in positions.securities
        if getattr(p, "instrument_type", "") == "bond"
    ]
    if not bond_positions:
        return []

    # справочник облигаций — через Client, не через SandboxService
    all_bonds = {}
    for b in cl.instruments.bonds().instruments:
        all_bonds[b.figi] = b

    result = []
    for p in bond_positions:
        b = all_bonds.get(p.figi)
        if b is None:
            continue
        nominal = money_to_decimal(b.nominal)
        d_mod, d_src = duration_to_years(getattr(b, "duration", None), years_to_maturity(b))
        result.append({
            "figi": p.figi,
            "ticker": b.ticker,
            "name": b.name,
            "qty": p.balance,
            "nominal_rub": str(nominal),
            "duration_years": str(d_mod),
            "duration_source": d_src,
            "maturity_date": (
                b.maturity_date.date().isoformat()
                if hasattr(b.maturity_date, "date")
                else str(b.maturity_date)
            ),
        })
    return result

def fetch_last_close(cl: Client, figi: str, lookback_days: int = 15) -> dict:
    """Цена закрытия последней дневной свечи (в % от номинала).

    resp.candles — список свечей внутри GetCandlesResponse.
    """
    resp = cl.market_data.get_candles(
        figi=figi,
        from_=now() - timedelta(days=lookback_days),
        to=now(),
        interval=CandleInterval.CANDLE_INTERVAL_DAY,
    )
    candles = resp.candles  # КЛЮЧЕВОЕ: не list(resp)
    if not candles:
        return {"figi": figi, "close_pct": None, "time": None, "source": "candles_empty"}

    last = candles[-1]
    return {
        "figi": figi,
        "close_pct": str(quotation_pct_to_decimal(last.close)),
        "time": last.time.isoformat(),
        "source": "daily_candle",
    }


def compute_rate_shift(
    bonds: list[dict],
    closes: dict[str, Decimal],
    shift_pp: Decimal,
) -> dict:
    """ΔP ≈ -D_mod * P * Δy по каждой бумаге и суммарно."""
    rows = []
    total_value = Decimal(0)
    total_impact = Decimal(0)

    for b in bonds:
        figi = b["figi"]
        close = closes.get(figi)
        if close is None:
            rows.append({**b, "close_pct": None, "value_rub": None, "impact_rub": None})
            continue

        qty = Decimal(b["qty"])
        nominal = Decimal(b["nominal_rub"])
        d_mod = Decimal(b["duration_years"])

        value = (close / Decimal(100)) * nominal * qty
        impact = -d_mod * value * (shift_pp / Decimal(100))

        total_value += value
        total_impact += impact

        rows.append({
            **b,
            "close_pct": str(close),
            "value_rub": f"{value:.2f}",
            "impact_rub": f"{impact:.2f}",
        })

    pct = (Decimal(100) * total_impact / total_value) if total_value else Decimal(0)
    return {
        "shift_pp": str(shift_pp),
        "rows": rows,
        "total_value_rub": f"{total_value:.2f}",
        "total_impact_rub": f"{total_impact:.2f}",
        "total_impact_pct": f"{pct:.2f}",
    }
# ---------- поиск бумаг ----------

def fetch_bonds_catalog(cl: Client) -> list:
    """Справочник облигаций (кэш на один вызов)."""
    return cl.instruments.bonds(
        instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
    ).instruments


def find_best_ofz(
    cl: Client,
    target_years: float,
    tolerance_years: float = 0.5,
) -> dict:
    """Самый выгодный ОФЗ (макс. YTM) со сроком в target_years ± tolerance."""
    best = None
    for b in fetch_bonds_catalog(cl):
        if not b.ticker.startswith("SU"):     # только ОФЗ-ПД
            continue
        m = b.maturity_date
        if hasattr(m, "date"):
            m = m.date()
        years = (m - now().date()).days / 365.0
        if abs(years - target_years) > tolerance_years:
            continue
        ytm = getattr(b, "yield_to_maturity", None)
        if ytm is None:
            continue
        ytm_dec = quotation_to_decimal(ytm)
        if best is None or ytm_dec > best["ytm_pct"]:
            best = {
                "figi": b.figi,
                "ticker": b.ticker,
                "name": b.name,
                "maturity_date": m.isoformat(),
                "years_to_maturity": round(years, 2),
                "ytm_pct": ytm_dec,
            }
    if best is None:
        return {"found": False, "target_years": target_years}
    best["ytm_pct"] = f"{best['ytm_pct']:.2f}"
    return {"found": True, **best}


# ---------- сценарии ----------

def compare_scenarios(
    bonds: list[dict],
    closes: dict[str, Decimal],
    shifts_pp: list[Decimal],
) -> dict:
    """Прогон compute_rate_shift по списку сдвигов."""
    results = []
    for s in shifts_pp:
        r = compute_rate_shift(bonds, closes, s)
        results.append({
            "shift_pp": r["shift_pp"],
            "total_value_rub": r["total_value_rub"],
            "total_impact_rub": r["total_impact_rub"],
            "total_impact_pct": r["total_impact_pct"],
        })
    return {"scenarios": results}


# ---------- ребалансировка (предложение, не исполнение) ----------

def propose_rebalance(
    bonds: list[dict],
    closes: dict[str, Decimal],
    target_ticker: str,
    target_pct: Decimal,
) -> dict:
    """Предложение: сколько продать/купить target_ticker, чтобы его доля = target_pct."""
    # текущая стоимость портфеля
    values = {}
    total = Decimal(0)
    for b in bonds:
        c = closes.get(b["figi"])
        if c is None:
            continue
        v = (c / Decimal(100)) * Decimal(b["nominal_rub"]) * Decimal(b["qty"])
        values[b["ticker"]] = v
        total += v

    if target_ticker not in values:
        return {"error": f"{target_ticker} нет в портфеле"}

    target_value = total * (target_pct / Decimal(100))
    current_value = values[target_ticker]
    delta_rub = target_value - current_value

    b = next(x for x in bonds if x["ticker"] == target_ticker)
    price_pct = closes.get(b["figi"])
    if price_pct is None:
        return {"error": f"нет цены для {target_ticker}"}
    one_lot_value = (price_pct / Decimal(100)) * Decimal(b["nominal_rub"])
    delta_qty = (delta_rub / one_lot_value).quantize(Decimal("1"))

    action = "BUY" if delta_qty > 0 else ("SELL" if delta_qty < 0 else "HOLD")
    return {
        "target_ticker": target_ticker,
        "target_pct": str(target_pct),
        "current_value_rub": f"{current_value:.2f}",
        "target_value_rub": f"{target_value:.2f}",
        "delta_rub": f"{delta_rub:.2f}",
        "action": action,
        "delta_qty": int(abs(delta_qty)),
        "note": "Предложение, не исполнение. Торговля через MCP пока недоступна.",
    }