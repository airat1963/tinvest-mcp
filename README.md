

A.1. Структура проекта
text
tinvest-mcp/
├── pyproject.toml
├── README.md
├── .env.example
└── src/
    └── tinvest_mcp/
        ├── __init__.py
        ├── server.py          # точка входа MCP
        ├── tools.py           # handlers трёх инструментов
        ├── api.py             # обёртки над t_tech.invest с проверками
        └── schemas.py         # JSON-схемы инструментов

A.2. pyproject.toml

A.3. .env.example
T_SANDBOX_TOKEN=t.ВАШ_ПЕСОЧНЫЙ_ТОКЕН
# опционально: фиксированный account_id, иначе берётся первый из get_sandbox_accounts
T_SANDBOX_ACCOUNT_ID="3c6d08f8-fcc0-4d01-babe-3e9670da0d81"

A.4. src/tinvest_mcp/api.py — обёртки с проверками
Здесь живут все «страшные» преобразования, которые мы отлаживали. Handlers их не повторяют.

A.5. src/tinvest_mcp/tools.py — handlers трёх инструментов (ОФЗ 38,39,40)


A.6. src/tinvest_mcp/schemas.py — JSON-схемы инструментов
Именно эти схемы агент видит как «доступные действия». Формулировки description — часть UX: агент опирается на них, когда решает, какой инструмент вызвать.

A.7. src/tinvest_mcp/server.py — MCP-сервер
python
"""MCP-сервер: регистрирует три инструмента и обслуживает stdio."""

A.8. src/tinvest_mcp/__init__.py

A.9. Подключение к агенту (пример для Claude Desktop)

Для Алисы AI / ChatGPT — аналогично, через их MCP-конфиг; главное — команда python -m tinvest_mcp.server и env с токеном.

A.10. Локальная проверка без агента
Пока MCP-клиента нет, handlers можно дёргать напрямую:

python
from tinvest_mcp.tools import (
    tool_get_bonds_positions,
    tool_get_last_close,
    tool_estimate_rate_shift,
)

print(tool_get_bonds_positions())
print(tool_get_last_close(figi="BBG011FJ4HS6"))     # 26238
print(tool_estimate_rate_shift(shift_pp=0.25))
Это ровно наш отлаженный estimate_rate_impact, только возвращает структуру, а не печатает.

A.11. Что заложено «в защиту» — сводка
Грабли из нашей отладки	Где зашито
list(resp) → TypeError	    fetch_last_close: resp.candles
MoneyValue не итерируется	fetch_bonds_positions: total_amount_currencies не трогаем, nominal через money_to_decimal

datetime - date → TypeError	years_to_maturity: .date() у maturity_date
duration в днях	duration_to_years: >100 => /365

current_price нет в позициях	цена через fetch_last_close, не из PositionsSecurities
RESOURCE_EXHAUSTED	пока не в MCP; на этапе MVP добавить retry в api.py (как в sandbox_ofz.py)
Дубли покупок	не актуально: MCP на старте только читает
