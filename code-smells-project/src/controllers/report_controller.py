"""Cross-entity reporting logic (order stats + discount tiers). This is
exactly the kind of business rule the architecture guidelines say does not
belong in a model - it spans orders, not a single entity's own fields.
"""
from models import order_model

REVENUE_THRESHOLD_HIGH = 10000
REVENUE_THRESHOLD_MID = 5000
REVENUE_THRESHOLD_LOW = 1000

DISCOUNT_RATE_HIGH = 0.10
DISCOUNT_RATE_MID = 0.05
DISCOUNT_RATE_LOW = 0.02


def calculate_discount(faturamento):
    if faturamento > REVENUE_THRESHOLD_HIGH:
        return faturamento * DISCOUNT_RATE_HIGH
    if faturamento > REVENUE_THRESHOLD_MID:
        return faturamento * DISCOUNT_RATE_MID
    if faturamento > REVENUE_THRESHOLD_LOW:
        return faturamento * DISCOUNT_RATE_LOW
    return 0


def build_sales_report():
    stats = order_model.get_stats()
    faturamento = stats["faturamento"] or 0
    desconto = calculate_discount(faturamento)
    total_pedidos = stats["total_pedidos"]

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": stats["pendentes"],
        "pedidos_aprovados": stats["aprovados"],
        "pedidos_cancelados": stats["cancelados"],
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }
