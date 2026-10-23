"""透明规则：Decimal计算、不提前舍入，不依赖页面或AI。"""
from decimal import Decimal, InvalidOperation

COSTS = ["单位材料成本", "单位人工成本", "单位制造费用", "整批固定费用", "卖方承担的整批物流费用"]


def number(value):
    try:
        n = Decimal(str(value))
        if not n.is_finite() or n < 0:
            raise ValueError
        return n
    except (InvalidOperation, ValueError):
        raise ValueError("请输入有限的非负数字。") from None


def calculate(quantity, costs, minimum, target):
    q, low, goal = number(quantity), number(minimum), number(target)
    if q <= 0:
        raise ValueError("采购数量必须大于0。")
    if not 0 <= low <= goal < 100:
        raise ValueError("毛利率须满足：0 ≤ 最低毛利率 ≤ 目标毛利率 < 100%。")
    missing = [f for f in COSTS if costs.get(f) in ("", None)]
    values = {f: number(v) for f, v in costs.items() if f in COSTS and v not in ("", None)}
    if missing:
        return {"missing": missing}
    allocation = (values[COSTS[3]] + values[COSTS[4]]) / q
    cost = sum(values[f] for f in COSTS[:3]) + allocation
    return {"missing": [], "allocation": allocation, "unit_cost": cost,
            "floor": cost / (1-low/100), "target": cost / (1-goal/100)}


def check_price(result, price):
    if result["missing"]:
        raise ValueError("关键成本缺失，禁止提交审批：" + "、".join(result["missing"]))
    p = number(price)
    if p <= 0:
        raise ValueError("拟报价必须大于0，才能计算毛利率并提交。")
    if p < result["floor"]:
        raise ValueError("拟报价低于最低允许单价，禁止提交审批。")
    return p


def percentile(values, fraction):
    values = sorted(number(v) for v in values)
    if not values:
        return None
    position = Decimal(len(values)-1) * Decimal(str(fraction))
    i = int(position)
    return values[i] if i == len(values)-1 else values[i] + (values[i+1]-values[i])*(position-i)
