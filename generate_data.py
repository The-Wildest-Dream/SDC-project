"""固定种子合成数据。运行 python generate_data.py 可重新生成示例 CSV。"""
import random
from datetime import date, timedelta
from pathlib import Path

from data_service import csv_bytes, prepare_import

SEED = 20261023
AS_OF = date(2026, 10, 23)


def generate():
    rng = random.Random(SEED)
    products = []
    for i, name in enumerate(["铝合金支架", "精密螺栓", "密封圈", "钢板", "铜线", "塑料外壳"], 1):
        products.append({"产品ID": f"P{i:03}", "产品名称": f"模拟{name}",
                         "单位": "千克" if i in (4, 5) else "件", "币种": "CNY",
                         "单位材料成本": round(rng.uniform(10, 80), 2),
                         "单位人工成本": round(rng.uniform(3, 20), 2),
                         "单位制造费用": round(rng.uniform(2, 10), 2),
                         "成本更新时间": AS_OF.isoformat()})
    customers = [{"客户ID": f"C{i:03}", "客户名称": f"模拟客户{i:02}",
                  "合作开始日期": "2024-01-01"} for i in range(1, 13)]
    orders = []
    for i in range(300):
        p = rng.choice(products)
        # 最后一个客户只分配三笔，以演示小样本提示。
        c = customers[-1] if i < 3 else rng.choice(customers[:-1])
        day = date(2025, 10, 24) + timedelta(days=rng.randrange(365))
        due = day + timedelta(days=rng.choice([15, 30, 45, 60]))
        cost = round(sum(p[f] for f in ("单位材料成本", "单位人工成本", "单位制造费用")) * rng.uniform(.85, 1.15), 2)
        paid = due + timedelta(days=rng.choice([-5, 0, 0, 3, 10, 30, 60]))
        paid_text = paid.isoformat() if rng.random() > .18 and paid <= AS_OF else ""
        orders.append({"订单ID": f"O{i+1:04}", "订单日期": day.isoformat(),
                       "客户ID": c["客户ID"], "产品ID": p["产品ID"],
                       "数量": rng.randint(10, 500), "成交单价": round(cost / (1-rng.uniform(.1, .35)), 2),
                       "当时单位成本": cost, "约定付款日期": due.isoformat(),
                       "实际付款日期": paid_text, "单位": p["单位"], "币种": p["币种"]})
    inventory = []
    for p in products:
        amount = rng.randint(100, 2000)
        inventory.append({"产品ID": p["产品ID"], "现有数量": amount,
                          "已预留数量": rng.randint(0, amount), "更新时间": AS_OF.isoformat()})
    bundle = {"产品": products, "客户": customers, "历史交易": orders, "库存": inventory}
    validated, errors = prepare_import(bundle, {k: csv_bytes(k, v) for k, v in bundle.items()})
    if errors:
        raise ValueError(errors)
    return validated


if __name__ == "__main__":
    output = Path(__file__).parent / "sample_data"
    output.mkdir(exist_ok=True)
    for kind, rows in generate().items():
        (output / f"模拟数据_{kind}.csv").write_bytes(csv_bytes(kind, rows))
    print("已生成模拟数据：6个产品、12个客户、300笔历史交易、6条库存。")
