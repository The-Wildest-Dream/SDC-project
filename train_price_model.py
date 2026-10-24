"""Train offline on CPU with `python train_price_model.py`; the web app never triggers training."""
import hashlib
import json
import os
from datetime import datetime, timezone
from statistics import median
from pathlib import Path
import joblib
import pandas as pd
import sklearn
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from generate_data import generate, SEED
from price_model import MODEL_DIR, FEATURES, features, group_key
from data_service import SCHEMAS, parse_csv, validate_bundle
from generate_myr_data import SEED as MYR_SEED

ROOT = Path(__file__).resolve().parent
MYR_FILES = {
    kind: ROOT / "sample_data" / f"MYR_模拟数据_{kind}.csv"
    for kind in SCHEMAS
}


def load_training_rows():
    """Load CNY synthetic trades and the separate, reviewed MYR CSV bundle."""
    bundle = generate()
    myr_bundle = {}
    for kind, path in MYR_FILES.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing MYR training CSV: {path}; run `python generate_myr_data.py` first."
            )
        rows, errors = parse_csv(kind, path.read_bytes())
        if errors:
            raise ValueError(f"Invalid MYR training file {path.name}: {errors}")
        myr_bundle[kind] = [
            {field: row[field] for field in SCHEMAS[kind]}
            for row in rows
        ]

    cny_product_ids = {row["产品ID"] for row in bundle["产品"]}
    cny_customer_ids = {row["客户ID"] for row in bundle["客户"]}
    if cny_product_ids.intersection(row["产品ID"] for row in myr_bundle["产品"]):
        raise ValueError("MYR product IDs must not overlap existing CNY product IDs.")
    if cny_customer_ids.intersection(row["客户ID"] for row in myr_bundle["客户"]):
        raise ValueError("MYR customer IDs must not overlap existing CNY customer IDs.")
    if any(row["币种"] != "MYR" for row in myr_bundle["产品"]):
        raise ValueError("All products in the MYR training bundle must use MYR.")
    if any(row["币种"] != "MYR" for row in myr_bundle["历史交易"]):
        raise ValueError("All transactions in the MYR training bundle must use MYR.")

    combined = {
        kind: [*bundle[kind], *myr_bundle[kind]]
        for kind in SCHEMAS
    }
    errors = validate_bundle(combined)
    if errors:
        raise ValueError(f"Combined synthetic training bundle is invalid: {errors}")
    return sorted(
        combined["历史交易"],
        key=lambda row: (row["订单日期"], row["订单ID"]),
    )


def train():
    # Use only the fixed-seed CNY generator and reviewed MYR CSVs; never database
    # imports or post-transaction payment outcomes.
    rows = load_training_rows()
    data_hash = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    cutoff = rows[int(len(rows)*.8)]["订单日期"]
    train_rows = [r for r in rows if r["订单日期"] < cutoff]
    test_rows = [r for r in rows if r["订单日期"] >= cutoff]
    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_version": data_hash, "generator_seed": SEED,
        "generator_seeds": {"CNY": SEED, "MYR": MYR_SEED},
        "source": "固定种子CNY生成器 + sample_data中的MYR合成CSV；不使用数据库或付款结果",
        "sklearn_version": sklearn.__version__, "algorithm": "分产品/币种/单位 StandardScaler + Ridge(alpha=1)",
        "features": FEATURES, "group_fields": ["产品ID", "币种", "单位"],
        "target": "成交单价", "split_date": cutoff,
        "split_rule": "前约80%日期训练，剩余日期测试；同一天不跨集合；不以测试集调参或重训",
        "train_count": len(train_rows), "test_count": len(test_rows), "groups": {},
        "disclaimer": "合成数据指标只验证原型流程，不证明真实商业收益。",
    }
    models = {}
    for key in sorted({group_key(r["产品ID"], r["币种"], r["单位"]) for r in rows}):
        select = lambda items: [r for r in items if group_key(r["产品ID"], r["币种"], r["单位"]) == key]
        tr, te = select(train_rows), select(test_rows)
        if len(tr) < 20 or len(te) < 5:
            metadata["groups"][key] = {"train_count": len(tr), "test_count": len(te), "status": "样本不足"}
            continue
        frame = lambda items: pd.DataFrame([features(r["数量"], r["当时单位成本"], r["订单日期"]) for r in items], columns=FEATURES)
        xtr, xte = frame(tr), frame(te)
        ytr, yte = [float(r["成交单价"]) for r in tr], [float(r["成交单价"]) for r in te]
        model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        model.fit(xtr, ytr)
        baseline = median(ytr)
        models[key] = model
        model_mae = mean_absolute_error(yte, model.predict(xte))
        baseline_mae = mean_absolute_error(yte, [baseline]*len(te))
        metadata["groups"][key] = {
            "status": "已训练", "train_count": len(tr), "test_count": len(te),
            "train_start": tr[0]["订单日期"], "train_end": tr[-1]["订单日期"],
            "test_start": te[0]["订单日期"], "test_end": te[-1]["订单日期"],
            "baseline": "仅训练集同产品/币种/单位成交价中位数",
            "baseline_price": baseline, "baseline_mae": baseline_mae, "model_mae": model_mae,
            "comparison": "模型MAE较低" if model_mae < baseline_mae else "模型未优于基线",
            "ranges": {f: [float(xtr[f].min()), float(xtr[f].max())]
                       for f in ("quantity", "historical_unit_cost")},
        }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    # Atomically replace the model bundle so the app cannot read a partial artifact.
    temp = MODEL_DIR / "model.tmp"
    joblib.dump({"models": models, "metadata": metadata}, temp)
    os.replace(temp, MODEL_DIR / "model.joblib")
    (MODEL_DIR / "evaluation.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


if __name__ == "__main__":
    train()
