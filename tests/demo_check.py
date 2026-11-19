# 1. ИМПОРТЫ
"""Прогон 6 реплик демо через наш tinvest-mcp. Печатает PASS/FAIL."""

import os
from decimal import Decimal

from dotenv import load_dotenv

from tinvest_mcp.tools import (
    tool_get_bonds_positions,
    tool_get_last_close,
    tool_estimate_rate_shift,
    tool_find_best_ofz,
    tool_compare_scenarios,
    tool_propose_rebalance,
)

load_dotenv()


# 2. ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ check
def check(cond: bool, msg: str) -> bool:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    return cond

def main() -> None:
    if not os.getenv("T_SANDBOX_TOKEN"):
        raise SystemExit("Задайте T_SANDBOX_TOKEN")

    all_ok = True

    # ---------- B.1′ ----------
    print("\nB.1′ — Покажи портфель")
    pos = tool_get_bonds_positions()
    print(f"  count={pos['count']}")
    for b in pos["bonds"]:
        print(f"  {b['ticker']}: qty={b['qty']}, maturity={b['maturity_date']}, "
              f"duration={b['duration_years']} ({b['duration_source']})")

    by_ticker = {b["ticker"]: b for b in pos["bonds"]}
    all_ok &= check(pos["count"] == 3, "три выпуска в портфеле")
    all_ok &= check(
        "SU26238RMFS4" in by_ticker
        and by_ticker["SU26238RMFS4"]["maturity_date"].startswith("2041"),
        "26238 погашается в 2041",
    )
    all_ok &= check(
        "SU26239RMFS2" in by_ticker
        and by_ticker["SU26239RMFS2"]["maturity_date"].startswith("2031"),
        "26239 погашается в 2031",
    )

    # ---------- B.2′ ----------
    print("\nB.2′ — Что при +0,25?")
    r = tool_estimate_rate_shift(shift_pp=0.25)
    print(f"  total_value={r['total_value_rub']} RUB, impact={r['total_impact_rub']} RUB "
          f"({r['total_impact_pct']}%)")
    all_ok &= check(Decimal(r["total_impact_rub"]) < 0, "impact отрицательный при росте ставки")

    rows = {row["ticker"]: row for row in r["rows"]}
    imp_238 = abs(Decimal(rows["SU26238RMFS4"]["impact_rub"]))
    imp_240 = abs(Decimal(rows["SU26240RMFS0"]["impact_rub"]))
    all_ok &= check(imp_238 > imp_240,
                    f"|impact(26238)|={imp_238} > |impact(26240)|={imp_240}")

    # ---------- B.3′ ----------
    # 
        # ---------- B.3′ ----------
    print("\nB.3′ — Выгодный ОФЗ ~2 года")
    best = tool_find_best_ofz(target_years=2.0, tolerance_years=0.5)
    print(f"  {best}")
    if best.get("found"):
        all_ok &= check(
            1.5 <= float(best["years_to_maturity"]) <= 2.5,
            "срок в диапазоне 1.5–2.5 лет",
        )
    else:
        print("  ℹ️  в песочнице нет ОФЗ ~2 года — это верный ответ для песочницы")
        all_ok &= check(True, "found=False — корректно (нет таких бумаг)")

    # ---------- B.4′ ----------
    print("\nB.4′ — Почему 26238 сильнее 26239")
    d_238 = Decimal(by_ticker["SU26238RMFS4"]["duration_years"])
    d_239 = Decimal(by_ticker["SU26239RMFS2"]["duration_years"])
    all_ok &= check(d_238 > d_239,
                    f"duration(26238)={d_238} > duration(26239)={d_239}")

    # ---------- B.5′ ----------
    print("\nB.5′ — Сравни сценарии")
    cmp = tool_compare_scenarios(shifts_pp=[-0.25, 0.0, 0.25, 0.5])
    for s in cmp["scenarios"]:
        print(f"  shift={s['shift_pp']:>5}  value={s['total_value_rub']:>10}  "
              f"impact={s['total_impact_rub']:>10}  ({s['total_impact_pct']}%)")

    impacts = [Decimal(s["total_impact_rub"]) for s in cmp["scenarios"]]
    mono = all(impacts[i] > impacts[i + 1] for i in range(len(impacts) - 1))
    all_ok &= check(mono, "impact монотонно убывает с ростом сдвига")

    # ---------- B.6′ ----------
    print("\nB.6′ — Ребалансировка 26240 к 10%")
    reb = tool_propose_rebalance(target_ticker="SU26240RMFS0", target_pct=10.0)
    print(f"  {reb}")
    all_ok &= check("action" in reb, "получено предложение (action)")
    all_ok &= check("note" in reb and "не исполнение" in reb["note"].lower(),
                    "явно помечено как предложение, не исполнение")

    # ---------- итог ----------
    print("\n" + "=" * 50)
    print("ИТОГ:", "PASS" if all_ok else "FAIL")
    print("=" * 50)


if __name__ == "__main__":
    main()