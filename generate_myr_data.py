"""Create a separate, repeatable Malaysian-scenario MYR synthetic CSV bundle."""
import random
from datetime import date, timedelta
from pathlib import Path

from data_service import SCHEMAS, csv_bytes, prepare_import

SEED = 20261024
AS_OF = date(2026, 10, 23)
PRODUCT_SPECS = [
    {
        "产品ID": "P_MY_001",
        "产品名称": "模拟MYR CNC铝制安装支架",
        "单位": "件",
        "单位材料成本": 12.40,
        "单位人工成本": 6.20,
        "单位制造费用": 3.50,
    },
    {
        "产品ID": "P_MY_002",
        "产品名称": "模拟MYR不锈钢紧固件",
        "单位": "件",
        "单位材料成本": 2.10,
        "单位人工成本": 0.65,
        "单位制造费用": 0.45,
    },
    {
        "产品ID": "P_MY_003",
        "产品名称": "模拟MYR注塑电缆外壳",
        "单位": "件",
        "单位材料成本": 3.80,
        "单位人工成本": 1.30,
        "单位制造费用": 0.95,
    },
    {
        "产品ID": "P_MY_004",
        "产品名称": "模拟MYR焊接钢制底板",
        "单位": "千克",
        "单位材料成本": 8.60,
        "单位人工成本": 2.40,
        "单位制造费用": 1.70,
    },
]
CUSTOMER_NAMES = [
    "模拟 Seri Maju Engineering Sdn. Bhd.",
    "模拟 Bintang Precision Works Sdn. Bhd.",
    "模拟 Harmoni Industrial Components Sdn. Bhd.",
    "模拟 Selatan Automation Supply Sdn. Bhd.",
    "模拟 Cekap Manufacturing Services Sdn. Bhd.",
    "模拟 Reka Teknikal Industries Sdn. Bhd.",
]


def generate():
    """Return a validated synthetic MYR bundle without touching a database."""
    rng = random.Random(SEED)
    products = [
        {
            **spec,
            "币种": "MYR",
            "成本更新时间": AS_OF.isoformat(),
        }
        for spec in PRODUCT_SPECS
    ]
    customers = [
        {
            "客户ID": f"C_MY_{index:03}",
            "客户名称": name,
            "合作开始日期": "2024-01-01",
        }
        for index, name in enumerate(CUSTOMER_NAMES, 1)
    ]

    candidates = []
    first_day = AS_OF - timedelta(days=364)
    for product in products:
        base_cost = sum(
            product[field]
            for field in ("单位材料成本", "单位人工成本", "单位制造费用")
        )
        for sample_index in range(80):
            order_date = first_day + timedelta(days=rng.randrange(365))
            historical_cost = round(base_cost * rng.uniform(0.85, 1.15), 2)
            gross_margin = rng.uniform(0.12, 0.32)
            # MYR prices are generated independently in MYR; no CNY conversion is used.
            unit_price = round(
                historical_cost / (1 - gross_margin) * rng.uniform(0.98, 1.02), 2
            )
            due_date = order_date + timedelta(days=rng.choice([15, 30, 45, 60]))
            candidate_paid_date = due_date + timedelta(
                days=rng.choice([-5, 0, 0, 3, 10, 30, 60])
            )
            paid_date = (
                candidate_paid_date.isoformat()
                if rng.random() > 0.18 and candidate_paid_date <= AS_OF
                else ""
            )
            customer = rng.choice(customers)
            candidates.append(
                {
                    "_sort_date": order_date,
                    "_product_id": product["产品ID"],
                    "_sample_index": sample_index,
                    "订单日期": order_date.isoformat(),
                    "客户ID": customer["客户ID"],
                    "产品ID": product["产品ID"],
                    "数量": rng.randint(10, 500),
                    "成交单价": unit_price,
                    "当时单位成本": historical_cost,
                    "约定付款日期": due_date.isoformat(),
                    "实际付款日期": paid_date,
                    "单位": product["单位"],
                    "币种": "MYR",
                }
            )

    candidates.sort(
        key=lambda row: (
            row["_sort_date"],
            row["_product_id"],
            row["_sample_index"],
        )
    )
    transactions = []
    for index, candidate in enumerate(candidates, 1):
        row = {field: value for field, value in candidate.items() if not field.startswith("_")}
        row["订单ID"] = f"O_MY_{index:04}"
        transactions.append(row)

    inventory = []
    for product in products:
        on_hand = rng.randint(100, 2000)
        inventory.append(
            {
                "产品ID": product["产品ID"],
                "现有数量": on_hand,
                "已预留数量": rng.randint(0, on_hand),
                "更新时间": AS_OF.isoformat(),
            }
        )

    bundle = {
        "产品": products,
        "客户": customers,
        "历史交易": transactions,
        "库存": inventory,
    }
    validated, errors = prepare_import(
        bundle, {kind: csv_bytes(kind, rows) for kind, rows in bundle.items()}
    )
    if errors:
        raise ValueError(f"Generated MYR synthetic data failed validation: {errors}")
    return validated


def write_csvs(output_dir=None):
    output = Path(output_dir) if output_dir else Path(__file__).resolve().parent / "sample_data"
    output.mkdir(parents=True, exist_ok=True)
    bundle = generate()
    written = []
    for kind in SCHEMAS:
        path = output / f"MYR_模拟数据_{kind}.csv"
        path.write_bytes(csv_bytes(kind, bundle[kind]))
        written.append(path)
    return written


if __name__ == "__main__":
    files = write_csvs()
    print(f"已生成并校验 MYR 模拟数据：4个产品、6个客户、320笔历史交易、4条库存。")
    for path in files:
        print(path.relative_to(Path(__file__).resolve().parent))
