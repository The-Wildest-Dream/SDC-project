"""Historical transaction-price prototype; load only the trusted project-trained artifact."""
from datetime import date, timedelta
from pathlib import Path
from functools import lru_cache
import json
import math
import joblib
import pandas as pd
import sklearn

MODEL_DIR = Path(__file__).resolve().parent / "models" / "historical_price"
FEATURES = ["quantity", "historical_unit_cost", "date_ordinal", "month"]


def features(quantity, cost, day):
    day = date.fromisoformat(str(day)[:10])
    return {"quantity": float(quantity), "historical_unit_cost": float(cost),
            "date_ordinal": day.toordinal(), "month": day.month}


def group_key(product, currency, unit):
    return json.dumps([product, currency, unit], ensure_ascii=False)


@lru_cache(maxsize=2)
def load_bundle(path, modified):
    return joblib.load(path)


def predict_price(product, currency, unit, quantity, cost, day):
    path = MODEL_DIR / "model.joblib"
    try:
        if not path.is_file():
            return None, "模型文件缺失，请先离线训练；继续使用历史参考和成本计算。", None
        bundle = load_bundle(str(path), path.stat().st_mtime_ns)
        meta = bundle["metadata"]
        if meta["sklearn_version"] != sklearn.__version__:
            return None, "模型与当前scikit-learn版本不一致，请重新训练。", meta
        key = group_key(product, currency, unit)
        info = meta["groups"].get(key)
        if info is None or info.get("status") != "已训练" or key not in bundle["models"]:
            return None, "该产品/币种/单位未覆盖或训练、测试样本不足。", meta
        x = features(quantity, cost, day)
        for field in FEATURES:
            if not math.isfinite(x[field]):
                return None, "预测输入缺失或不是有限数值。", meta
        for field in ("quantity", "historical_unit_cost"):
            low, high = info["ranges"][field]
            if not low <= x[field] <= high:
                return None, f"{field}超出该组训练范围[{low:.2f}, {high:.2f}]。", meta
        d = date.fromisoformat(str(day)[:10])
        if not date.fromisoformat(info["train_start"]) <= d <= date.fromisoformat(info["train_end"]) + timedelta(days=180):
            return None, "询价日期超出适用窗口（训练起日到训练末日后180天）。", meta
        value = float(bundle["models"][key].predict(pd.DataFrame([x], columns=FEATURES))[0])
        if not math.isfinite(value) or value <= 0:
            return None, "模型输出无效，继续使用历史参考和成本计算。", meta
        return value, "仅为历史成交单价预测，不是利润最优价格或客户购买概率。", meta
    except Exception:
        return None, "模型无法加载或预测失败，请检查训练产物；继续使用历史参考和成本计算。", None
