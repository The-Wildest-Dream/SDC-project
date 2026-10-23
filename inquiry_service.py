"""询价及审批提交：数据库事务和服务端规则复核。"""
from datetime import date
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from database import engine, DatabaseUnavailable
from db_schema import inquiries, inquiry_details, tables, quote_versions, approval_records, operation_logs
from quotation_rules import COSTS, calculate, check_price, number


def save_inquiry(customer, product, quantity, delivery, expiry, costs, reason, minimum, target):
    calculate(quantity, costs, minimum, target)
    if delivery < date.today() or expiry < date.today():
        raise ValueError("交付日期和报价有效期不能早于今天。")
    try:
        with engine().begin() as conn:
            p = conn.execute(select(tables["产品"]).where(tables["产品"].c["产品ID"] == product).with_for_update()).mappings().one()
            changed = any(costs[f] in ("", None) or number(costs[f]) != p[f] for f in COSTS[:3])
            if changed and not reason.strip():
                raise ValueError("修改或清空产品成本必须填写修改理由。")
            snapshot = {"costs": costs, "reason": reason, "minimum": minimum, "target": target,
                        "product_name": p["产品名称"],
                        "source_costs": {f: str(p[f]) for f in COSTS[:3]},
                        "source_updated": p["成本更新时间"].isoformat(),
                        "entered_at": date.today().isoformat()}
            identifier = "INQ-" + uuid4().hex.upper()
            conn.execute(inquiries.insert().values(id=identifier, customer_id=customer, product_id=product,
                         quantity=number(quantity), unit=p["单位"], currency=p["币种"]))
            conn.execute(inquiry_details.insert().values(inquiry_id=identifier, delivery_date=delivery,
                         valid_until=expiry, snapshot=snapshot))
            conn.execute(operation_logs.insert().values(id=str(uuid4()), action="inquiry_saved",
                         actor="demo_operator", details={"inquiry_id": identifier}))
        return identifier
    except SQLAlchemyError:
        raise DatabaseUnavailable("询价保存失败，事务已回滚。请检查数据库及产品、客户数据。") from None


def list_inquiries():
    try:
        with engine().connect() as conn:
            return [dict(r) for r in conn.execute(select(inquiries, inquiry_details.c.delivery_date,
                      inquiry_details.c.valid_until, inquiry_details.c.snapshot).join(
                      inquiry_details, inquiries.c.id == inquiry_details.c.inquiry_id)
                      .order_by(inquiries.c.created_at.desc())).mappings()]
    except SQLAlchemyError:
        raise DatabaseUnavailable("询价读取失败，请检查数据库。") from None


def submit(identifier, price):
    try:
        with engine().begin() as conn:
            row = conn.execute(select(inquiries).where(inquiries.c.id == identifier).with_for_update()).mappings().one()
            details = conn.execute(select(inquiry_details).where(inquiry_details.c.inquiry_id == identifier)).mappings().one()
            if row["status"] != "draft":
                raise ValueError("该询价已提交或关闭，请勿重复提交。")
            if details["valid_until"] < date.today():
                raise ValueError("报价已过有效期，禁止提交。")
            s = details["snapshot"]
            result = calculate(row["quantity"], s["costs"], s["minimum"], s["target"])
            p = check_price(result, price)
            version = (conn.execute(select(func.max(quote_versions.c.version)).where(
                quote_versions.c.inquiry_id == identifier)).scalar() or 0) + 1
            qid = "QUO-" + uuid4().hex.upper()
            conn.execute(quote_versions.insert().values(
                id=qid, inquiry_id=identifier, version=version, unit=row["unit"], currency=row["currency"],
                quantity=row["quantity"], unit_cost=result["unit_cost"], unit_price=p,
                total_price=p*row["quantity"], target_margin=number(s["target"]), cost_snapshot=s))
            conn.execute(approval_records.insert().values(id=str(uuid4()), quote_version_id=qid,
                         actor="demo_operator", decision="submitted", comment="模拟数据：规则校验通过，等待人工审批"))
            conn.execute(inquiries.update().where(inquiries.c.id == identifier).values(status="submitted"))
            conn.execute(operation_logs.insert().values(id=str(uuid4()), action="quote_submitted",
                         actor="demo_operator", details={"inquiry_id": identifier, "quote_version_id": qid}))
        return qid
    except SQLAlchemyError:
        raise DatabaseUnavailable("提交审批失败，全部写入已回滚。") from None
