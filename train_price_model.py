"""CPU独立训练：python train_price_model.py；网页不会调用训练。"""
import hashlib
import json
import os
from datetime import datetime, timezone
from statistics import median
import joblib
import pandas as pd
import sklearn
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from generate_data import generate, SEED
from price_model import MODEL_DIR, FEATURES, features, group_key


def train():
    # 唯一数据来源为本项目固定种子的合成交易，不接收真实交易或付款数据。
    rows = sorted(generate()["历史交易"], key=lambda r: (r["订单日期"], r["订单ID"]))
    data_hash = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    cutoff = rows[int(len(rows)*.8)]["订单日期"]
    train_rows = [r for r in rows if r["订单日期"] < cutoff]
    test_rows = [r for r in rows if r["订单日期"] >= cutoff]
    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_version": data_hash, "generator_seed": SEED,
        "source": "generate_data.generate()固定合成历史交易；不使用数据库真实数据",
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
    # 单文件模型含完整元数据，原子替换，避免页面读取半个模型。
    temp = MODEL_DIR / "model.tmp"
    joblib.dump({"models": models, "metadata": metadata}, temp)
    os.replace(temp, MODEL_DIR / "model.joblib")
    (MODEL_DIR / "evaluation.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


if __name__ == "__main__":
    train()
