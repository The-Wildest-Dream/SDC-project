"""Quotation calculations; monetary values are expressed in yuan."""
from decimal import Decimal


def calculate_quote(quantity, material, labor, overhead, fixed, logistics, margin):
    values = [Decimal(str(v)) for v in
              (quantity, material, labor, overhead, fixed, logistics, margin)]
    if not all(v.is_finite() for v in values):
        raise ValueError("所有数值必须为有限数字。")
    quantity, material, labor, overhead, fixed, logistics, margin = values
    if quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError("采购数量必须为大于 0 的整数。")
    if not 0 <= margin < 100:
        raise ValueError("目标毛利率必须大于或等于 0%，且小于 100%。")
    if any(v < 0 for v in (material, labor, overhead, fixed, logistics)):
        raise ValueError("各项成本和费用不能为负数。")
    allocated = (fixed + logistics) / quantity
    unit_cost = material + labor + overhead + allocated
    unit_price = unit_cost / (1 - margin / 100)
    return {
        "allocated": allocated,
        "unit_cost": unit_cost,
        "unit_price": unit_price,
        "total": unit_price * quantity,
    }
