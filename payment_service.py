"""合成订单的分笔付款流水追加、读取与日期截断分析。"""
import csv
import io
from datetime import date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from database import engine, DatabaseUnavailable, read_data
from db_schema import payment_ledger, tables
from finance_rules import ledger_summary


def get_ledger():
    try:
        with engine().connect() as conn:
            return [dict(r) for r in conn.execute(select(payment_ledger)).mappings()]
    except SQLAlchemyError:
        raise DatabaseUnavailable("付款流水读取失败。") from None


def import_ledger(content):
    issues, rows = [], []
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        required = {"订单ID", "付款日期", "金额"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            return [{"行号": 1, "原因": "必需列为：订单ID、付款日期、金额"}]
        for line, row in enumerate(reader, 2):
            try:
                day = date.fromisoformat(row["付款日期"])
                amount = Decimal(row["金额"])
                if amount <= 0 or not amount.is_finite(): raise ValueError
                rows.append({"order_id": row["订单ID"], "payment_date": day, "amount": amount})
            except Exception:
                issues.append({"行号": line, "原因": "付款日期无效或金额必须为正数"})
    except Exception:
        return [{"行号": 1, "原因": "文件须为UTF-8 CSV"}]
    if issues: return issues
    data = read_data()
    orders = {r["订单ID"]: r for r in data["历史交易"]}
    for i, row in enumerate(rows, 2):
        order = orders.get(row["order_id"])
        if not order:
            issues.append({"行号": i, "原因": "引用订单不存在"})
        elif row["payment_date"].isoformat() < order["订单日期"]:
            issues.append({"行号": i, "原因": "付款日期早于订单日期"})
    if issues: return issues
    try:
        with engine().begin() as conn:
            # 导入流水为追加操作；同一订单允许多次付款，按CSV每行建立独立流水。
            for row in rows:
                conn.execute(payment_ledger.insert().values(id=str(uuid4()), **row))
            # 整单累计付款不得超过成交总额（已有旧付款日期视为旧流水基线）。
            for oid in {r["order_id"] for r in rows}:
                order = orders[oid]
                total = Decimal(str(order["成交单价"]))*Decimal(str(order["数量"]))
                sums = conn.execute(select(payment_ledger.c.amount).where(payment_ledger.c.order_id == oid)).scalars()
                legacy = total if order["实际付款日期"] else Decimal(0)
                if sum(sums, Decimal(0))+legacy > total:
                    raise ValueError(f"订单{oid}付款总额超过成交金额。")
    except ValueError as e:
        return [{"行号": "-", "原因": str(e)+"；事务已回滚"}]
    except SQLAlchemyError:
        raise DatabaseUnavailable("付款流水导入失败，事务已回滚。") from None
    return []


def summary(customer, as_of):
    return ledger_summary(read_data(), get_ledger(), customer, as_of)

