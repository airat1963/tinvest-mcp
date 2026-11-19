"""JSON-схемы MCP-инструментов. description — то, что видит агент."""

TOOLS = [
    {
        "name": "get_bonds_positions",
        "description": (
            "Возвращает позиции пользователя только по облигациям: FIGI, тикер, "
            "название, количество, номинал в рублях, модифицированную дюрацию "
            "в годах и дату погашения. Используй, когда нужно понять состав "
            "облигационного портфеля."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "ID счёта. Если не указан — берётся первый счёт песочницы.",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_last_close",
        "description": (
            "Возвращает цену закрытия последней дневной свечи по FIGI облигации "
            "в процентах от номинала (например, 98.5 означает 98.5% от номинала). "
            "Используй, когда нужна текущая/последняя цена конкретной бумаги."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "figi": {"type": "string", "description": "FIGI облигации."},
                "lookback_days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 365,
                    "default": 15,
                    "description": "Сколько дней назад искать свечи.",
                },
            },
            "required": ["figi"],
            "additionalProperties": False,
        },
    },
    {
        "name": "estimate_rate_shift",
        "description": (
            "Оценивает изменение стоимости облигационного портфеля при сдвиге "
            "ключевой ставки на shift_pp процентных пунктов по формуле "
            "ΔP ≈ -D_mod · P · Δy. Возвращает таблицу по бумагам и итог: "
            "стоимость портфеля, изменение в рублях и в процентах. "
            "Используй для вопросов вида «что будет с портфелем, если ставка "
            "вырастет на 0.25 п.п.». Торговлю не выполняет."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "shift_pp": {
                    "type": "number",
                    "description": "Сдвиг ставки в п.п.: 0.25 = +0.25 п.п., -0.5 = -0.5 п.п.",
                },
                "account_id": {
                    "type": "string",
                    "description": "ID счёта. Если не указан — первый счёт песочницы.",
                },
            },
            "required": ["shift_pp"],
            "additionalProperties": False,
        },
    },
    {
        "name": "find_best_ofz",
        "description": (
            "Ищет самый выгодный ОФЗ (максимальная доходность к погашению, YTM) "
            "со сроком до погашения около target_years лет (±tolerance_years). "
            "Используй для вопросов вида «найди самый выгодный ОФЗ на 2 года»."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_years": {"type": "number", "description": "Целевой срок в годах."},
                "tolerance_years": {"type": "number", "default": 0.5},
            },
            "required": ["target_years"],
            "additionalProperties": False,
        },
    },
    {
        "name": "compare_scenarios",
        "description": (
            "Считает изменение стоимости портфеля ОФЗ для нескольких сдвигов ставки "
            "за один вызов. Возвращает таблицу «сдвиг → стоимость → изменение». "
            "Используй для «покажи, что будет при -0.25, 0, +0.25, +0.5»."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "shifts_pp": {
                    "type": "array", "items": {"type": "number"},
                    "description": "Список сдвигов в п.п., например [-0.25, 0, 0.25, 0.5].",
                },
                "account_id": {"type": "string"},
            },
            "required": ["shifts_pp"],
            "additionalProperties": False,
        },
    },
    {
        "name": "propose_rebalance",
        "description": (
            "Предлагает, сколько купить/продать бумаги target_ticker, чтобы её доля "
            "в портфеле стала target_pct процентов. Торговлю НЕ выполняет — только "
            "возвращает действие и количество."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_ticker": {"type": "string"},
                "target_pct": {"type": "number"},
                "account_id": {"type": "string"},
            },
            "required": ["target_ticker", "target_pct"],
            "additionalProperties": False,
        },
    },
]

HANDLERS = {
    "get_bonds_positions": "tinvest_mcp.tools:tool_get_bonds_positions",
    "get_last_close": "tinvest_mcp.tools:tool_get_last_close",
    "estimate_rate_shift": "tinvest_mcp.tools:tool_estimate_rate_shift",
    "find_best_ofz": "tinvest_mcp.tools:tool_find_best_ofz",
    "compare_scenarios": "tinvest_mcp.tools:tool_compare_scenarios",
    "propose_rebalance": "tinvest_mcp.tools:tool_propose_rebalance",
}
# "find_best_ofz": "tinvest_mcp.tools:tool_find_best_ofz",
# "compare_scenarios": "tinvest_mcp.tools:tool_compare_scenarios",
# "propose_rebalance": "tinvest_mcp.tools:tool_propose_rebalance",

