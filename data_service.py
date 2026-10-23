"""纯 Python 数据契约、CSV 校验及付款口径；不依赖页面或数据库。"""
import csv
import io
import math
import re
from datetime import date

SCHEMAS = {
    "产品": ["产品ID", "产品名称", "单位", "币种", "单位材料成本", "单位人工成本", "单位制造费用", "成本更新时间"],
    "客户": ["客户ID", "客户名称", "合作开始日期"],
    "历史交易": ["订单ID", "订单日期", "客户ID", "产品ID", "数量", "成交单价", "当时单位成本", "约定付款日期", "实际付款日期", "单位", "币种"],
    "库存": ["产品ID", "现有数量", "已预留数量", "更新时间"],
}
NUMBERS = {"单位材料成本", "单位人工成本", "单位制造费用", "数量", "成交单价", "当时单位成本", "现有数量", "已预留数量"}
DATES = {"成本更新时间", "合作开始日期", "订单日期", "约定付款日期", "实际付款日期", "更新时间"}


def csv_bytes(kind, rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=SCHEMAS[kind])
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def parse_csv(kind, content):
    """返回规范化记录及错误；行号为 CSV 物理起始行，表头为第 1 行。"""
    errors, rows = [], []

    def error(line, field, reason):
        errors.append({"行号": line, "字段": field, "原因": reason})

    try:
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)):
            error(1, "表头", "存在重复字段")
        for field in SCHEMAS[kind]:
            if field not in header:
                error(1, field, "缺少必需字段")
        for field in header:
            if field not in SCHEMAS[kind]:
                error(1, field, "未知字段，请使用示例 CSV 格式")
        if errors:
            return [], errors
        seen = set()
        while True:
            line = reader.line_num + 1
            values = next(reader, None)
            if values is None:
                break
            if len(values) != len(header):
                error(line, "整行", "列数与表头不一致")
                continue
            row = {k: v.strip() for k, v in zip(header, values)}
            for field, value in row.items():
                if not value:
                    if field != "实际付款日期":
                        error(line, field, "不能为空")
                    continue
                if field in NUMBERS:
                    try:
                        n = float(value)
                        if not math.isfinite(n) or n < 0 or (field == "数量" and n <= 0):
                            raise ValueError
                        row[field] = n
                    except ValueError:
                        error(line, field, "必须是有限的非负数；交易数量必须大于 0")
                elif field in DATES:
                    try:
                        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                            raise ValueError
                        date.fromisoformat(value)
                    except ValueError:
                        error(line, field, "必须为有效日期 YYYY-MM-DD")
                elif field == "币种" and value not in {"CNY", "USD", "EUR"}:
                    error(line, field, "仅支持 CNY、USD、EUR，不自动换汇")
            key = row[SCHEMAS[kind][0]]
            if key in seen:
                error(line, SCHEMAS[kind][0], f"重复ID：{key}")
            seen.add(key)
            row["_line"] = line
            rows.append(row)
        if not rows:
            error(2, "整表", "不允许导入空表")
    except (UnicodeDecodeError, csv.Error) as exc:
        error(locals().get("line", 1), "文件", f"请使用 UTF-8 CSV：{exc}")
    return rows, errors


def validate_bundle(bundle):
    """检查外键和跨表约束，包含旧表对新主数据的引用。"""
    errors = []
    products = {r["产品ID"]: r for r in bundle["产品"]}
    customers = {r["客户ID"]: r for r in bundle["客户"]}

    def error(kind, row, field, reason):
        errors.append({"数据类型": kind, "行号": row.get("_line", 2),
                       "字段": field, "原因": reason})

    for kind in ("历史交易", "库存"):
        for index, row in enumerate(bundle[kind], 2):
            row = {"_line": index, **row}
            product = products.get(row["产品ID"])
            if product is None:
                error(kind, row, "产品ID", "引用的产品不存在")
            if kind == "库存":
                if row["已预留数量"] > row["现有数量"]:
                    error(kind, row, "已预留数量", "不能超过现有数量")
                continue
            if row["客户ID"] not in customers:
                error(kind, row, "客户ID", "引用的客户不存在")
            elif row["订单日期"] < customers[row["客户ID"]]["合作开始日期"]:
                error(kind, row, "订单日期", "不能早于客户合作开始日期")
            for field in ("单位", "币种"):
                if product and row[field] != product[field]:
                    error(kind, row, field, "必须与引用产品一致；不自动换算单位或币种")
            for field in ("约定付款日期", "实际付款日期"):
                if row[field] and row[field] < row["订单日期"]:
                    error(kind, row, field, "不能早于订单日期")
    return errors


def prepare_import(current, uploads):
    """整批原子校验：任一错误返回 None，不修改 current。"""
    candidate = {k: [dict(r) for r in v] for k, v in current.items()}
    errors = []
    for kind, content in uploads.items():
        rows, issues = parse_csv(kind, content)
        candidate[kind] = rows
        errors.extend({"数据类型": kind, **e} for e in issues)
    if not errors:
        errors = validate_bundle(candidate)
    if errors:
        return None, errors
    return {k: [{f: r[f] for f in SCHEMAS[k]} for r in rows]
            for k, rows in candidate.items()}, []


def comparable_transactions(bundle, product_id):
    product = next(p for p in bundle["产品"] if p["产品ID"] == product_id)
    return [dict(r) for r in bundle["历史交易"]
            if (r["产品ID"], r["币种"], r["单位"]) ==
            (product_id, product["币种"], product["单位"])]


def payment_summary(bundle, as_of):
    """统计截至 as_of 日终；未来付款在该时点视为尚未付款。"""
    cutoff = as_of.isoformat()
    summaries, details = [], []
    for customer in bundle["客户"]:
        orders = [r for r in bundle["历史交易"]
                  if r["客户ID"] == customer["客户ID"] and r["订单日期"] <= cutoff]
        due = [r for r in orders if r["约定付款日期"] <= cutoff]
        on_time = unpaid = historical = 0
        for row in orders:
            paid = row["实际付款日期"]
            paid_by_now = bool(paid and paid <= cutoff)
            late = max(0, (date.fromisoformat(paid) - date.fromisoformat(row["约定付款日期"])).days) if paid_by_now else 0
            historical += late
            open_days = max(0, (as_of - date.fromisoformat(row["约定付款日期"])).days) if not paid_by_now else 0
            unpaid += int(open_days > 0)
            if row in due and paid_by_now and paid <= row["约定付款日期"]:
                on_time += 1
            details.append({"客户ID": customer["客户ID"], "订单ID": row["订单ID"],
                            "历史逾期天数": late, "当前逾期未付天数": open_days})
        summaries.append({
            **customer, "已到期订单数": len(due),
            "按时付款率": f"{on_time / len(due):.1%}" if due else "无到期样本",
            "当前逾期未付订单数": unpaid, "历史逾期天数（累计）": historical,
            "样本提示": "样本不足（到期订单少于10笔）" if len(due) < 10 else "仅为模拟样本描述",
        })
    return summaries, details
