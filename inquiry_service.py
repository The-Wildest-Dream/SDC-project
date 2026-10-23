"""询价及审批提交：数据库事务和服务端规则复核。"""
from datetime import date
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from database import engine, DatabaseUnavailable
from db_schema import inquiries, inquiry_details, tables, quote_versions, approval_records, operation_logs
from quotation_rules import COSTS, calculate, check_price, number


def save_inquiry(customer, product, quantity, delivery, expiry, costs, reason, minimum, target, *, actor):
    from demo_roles import require
    require(actor, "销售人员")
    calculate(quantity, costs, minimum, target)
    if delivery < date.today() or expiry < date.today():
        raise ValueError("交付日期和报价有效期不能早于今天。")
    try:
        with engine().begin() as conn:
            p = conn.execute(select(tables["产品"]).where(tables["产品"].c["产品ID"] == product).with_for_update()).mappings().one()
            changed = any(costs[f] in ("", None) or number(costs[f]) != p[f] for f in COSTS[:3])
            if changed and not reason.strip():
                raise ValueError("修改或清空产品成本必须填写修改理由。")
            snapshot = {"owner": actor, "costs": costs, "reason": reason, "minimum": minimum, "target": target,
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
                         actor=actor, details={"inquiry_id": identifier}))
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


def submit(identifier, price, *, actor):
    """旧询价提交入口关闭，统一使用带版本/角色校验的报价工作流。"""
    raise ValueError("请在报价记录中提交已保存的报价草稿。")
