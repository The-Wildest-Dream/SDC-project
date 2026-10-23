"""SQLAlchemy 数据表定义；导入模块不会创建或修改数据库。"""
from sqlalchemy import (MetaData, Table, Column, Text, Numeric, Date, DateTime,
                        Integer, ForeignKey, CheckConstraint, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import JSONB
from data_service import SCHEMAS, NUMBERS, DATES

metadata = MetaData()
TABLE_NAMES = {"产品": "products", "客户": "customers",
               "历史交易": "transactions", "库存": "inventory"}
tables = {}
for kind in ("产品", "客户", "历史交易", "库存"):
    columns = []
    for index, field in enumerate(SCHEMAS[kind]):
        datatype = Numeric() if field in NUMBERS else Date() if field in DATES else Text()
        refs = []
        if field == "产品ID" and kind != "产品":
            refs = [ForeignKey("products.产品ID", ondelete="RESTRICT")]
        if field == "客户ID" and kind != "客户":
            refs = [ForeignKey("customers.客户ID", ondelete="RESTRICT")]
        columns.append(Column(field, datatype, *refs, primary_key=index == 0,
                              nullable=field == "实际付款日期"))
    checks = [CheckConstraint(f'"{f}" {">" if f == "数量" else ">="} 0')
              for f in SCHEMAS[kind] if f in NUMBERS]
    if kind == "库存":
        checks.append(CheckConstraint('"已预留数量" <= "现有数量"'))
    if kind == "历史交易":
        checks.extend([CheckConstraint('"约定付款日期" >= "订单日期"'),
                       CheckConstraint('"实际付款日期" IS NULL OR "实际付款日期" >= "订单日期"')])
    tables[kind] = Table(TABLE_NAMES[kind], metadata, *columns, *checks)

inquiries = Table(
    "inquiries", metadata,
    Column("id", Text, primary_key=True),
    Column("customer_id", Text, ForeignKey("customers.客户ID"), nullable=False),
    Column("product_id", Text, ForeignKey("products.产品ID"), nullable=False),
    Column("quantity", Numeric(), nullable=False),
    Column("unit", Text, nullable=False), Column("currency", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="draft"),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    CheckConstraint("quantity > 0"),
    CheckConstraint("status IN ('draft','submitted','closed')"),
)
quote_versions = Table(
    "quote_versions", metadata,
    Column("id", Text, primary_key=True),
    Column("inquiry_id", Text, ForeignKey("inquiries.id"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("unit", Text, nullable=False), Column("currency", Text, nullable=False),
    Column("quantity", Numeric(), nullable=False),
    Column("unit_cost", Numeric(), nullable=False),
    Column("unit_price", Numeric(), nullable=False),
    Column("total_price", Numeric(), nullable=False),
    Column("target_margin", Numeric(), nullable=False),
    Column("cost_snapshot", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("inquiry_id", "version"),
    CheckConstraint("version > 0 AND quantity > 0 AND unit_cost >= 0 AND unit_price >= 0 AND total_price >= 0"),
    CheckConstraint("target_margin >= 0 AND target_margin < 100"),
)
approval_records = Table(
    "approval_records", metadata,
    Column("id", Text, primary_key=True),
    Column("quote_version_id", Text, ForeignKey("quote_versions.id"), nullable=False),
    Column("actor", Text, nullable=False),
    Column("decision", Text, nullable=False), Column("comment", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    CheckConstraint("decision IN ('submitted','approved','rejected')"),
)
operation_logs = Table(
    "operation_logs", metadata,
    Column("id", Text, primary_key=True),
    Column("action", Text, nullable=False),
    Column("actor", Text, nullable=False),
    Column("details", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
