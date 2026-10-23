"""模拟角色及报价状态的服务端校验；行锁和事务保护审批。"""
from copy import deepcopy
from datetime import date
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from database import engine, DatabaseUnavailable
from db_schema import quote_workflows as W, quote_versions as V, approval_records as A
from db_schema import inquiries as I, inquiry_details as D, tables, operation_logs as L
from demo_roles import require, own
from quotation_rules import calculate, check_price, number, COSTS

LABELS = {"draft": "草稿", "pending": "待审批", "approved": "已批准", "rejected": "已驳回"}


def log(conn, actor, action, identifier):
    conn.execute(L.insert().values(id=str(uuid4()), actor=actor, action=action,
                                  details={"quote_id": identifier, "模拟演示": True}))


def locked(conn, identifier):
    row = conn.execute(select(W).where(W.c.id == identifier).with_for_update()).mappings().first()
    if not row:
        raise ValueError("报价不存在。")
    return row


def validate(payload, submitting=False):
    result = calculate(payload["quantity"], payload["snapshot"]["costs"],
                       payload["snapshot"]["minimum"], payload["snapshot"]["target"])
    if submitting:
        check_price(result, payload["price"])
        if date.fromisoformat(payload["valid_until"]) < date.today():
            raise ValueError("报价有效期已过，禁止提交。")
    elif payload["price"] not in ("", None):
        number(payload["price"])
    date.fromisoformat(payload["delivery_date"])
    date.fromisoformat(payload["valid_until"])
    return result


def next_version(conn, inquiry_id):
    a = conn.execute(select(func.max(W.c.version)).where(W.c.inquiry_id == inquiry_id)).scalar() or 0
    b = conn.execute(select(func.max(V.c.version)).where(V.c.inquiry_id == inquiry_id)).scalar() or 0
    return max(a, b) + 1


def create_draft(inquiry_id, price, reference, actor):
    require(actor, "销售人员")
    try:
        with engine().begin() as conn:
            r = conn.execute(select(I).where(I.c.id == inquiry_id).with_for_update()).mappings().one()
            d = conn.execute(select(D).where(D.c.inquiry_id == inquiry_id)).mappings().one()
            own(actor, d["snapshot"].get("owner", "销售甲"))
            existing = conn.execute(select(W).where(W.c.inquiry_id == inquiry_id)).mappings().first()
            if existing or r["status"] != "draft":
                raise ValueError("该询价已有报价或已提交，请在报价记录中修改草稿或创建新版本。")
            customer = conn.execute(select(tables["客户"]).where(
                tables["客户"].c["客户ID"] == r["customer_id"])).mappings().one()
            p = {"customer_id": r["customer_id"], "customer_name": customer["客户名称"],
                 "product_id": r["product_id"], "product_name": d["snapshot"]["product_name"],
                 "quantity": str(r["quantity"]), "currency": r["currency"], "unit": r["unit"],
                 "price": str(price), "delivery_date": str(d["delivery_date"]),
                 "valid_until": str(d["valid_until"]), "snapshot": d["snapshot"],
                 "reference": reference}
            validate(p)
            identifier = "QUO-" + uuid4().hex.upper()
            conn.execute(W.insert().values(id=identifier, inquiry_id=inquiry_id,
                         version=next_version(conn, inquiry_id), owner=actor, status="draft", payload=p))
            log(conn, actor, "quote_draft_saved", identifier)
        return identifier
    except SQLAlchemyError:
        raise DatabaseUnavailable("保存报价失败，数据库事务已回滚。") from None


def edit_draft(identifier, changes, actor):
    require(actor, "销售人员")
    try:
        with engine().begin() as conn:
            r = locked(conn, identifier)
            own(actor, r["owner"])
            if r["status"] != "draft":
                raise ValueError("只有草稿可修改。待审批版本已锁定，已结束版本须创建新版本。")
            p = deepcopy(r["payload"])
            for key in ("quantity", "price", "delivery_date", "valid_until"):
                p[key] = str(changes[key])
            if changes["costs"] != p["snapshot"]["costs"] and not changes["reason"].strip():
                raise ValueError("修改成本必须填写理由。")
            p["snapshot"].update(costs=changes["costs"], reason=changes["reason"],
                                 minimum=changes["minimum"], target=changes["target"])
            validate(p)
            conn.execute(W.update().where(W.c.id == identifier).values(payload=p, updated_at=func.now()))
            log(conn, actor, "quote_draft_updated", identifier)
    except SQLAlchemyError:
        raise DatabaseUnavailable("修改失败，数据库事务已回滚。") from None


def submit_quote(identifier, actor):
    require(actor, "销售人员")
    try:
        with engine().begin() as conn:
            r = locked(conn, identifier)
            own(actor, r["owner"])
            if r["status"] != "draft":
                raise ValueError("只有草稿可以提交，禁止重复提交。")
            p = r["payload"]
            result = validate(p, True)
            price = number(p["price"])
            conn.execute(V.insert().values(id=identifier, inquiry_id=r["inquiry_id"], version=r["version"],
                         unit=p["unit"], currency=p["currency"], quantity=number(p["quantity"]),
                         unit_cost=result["unit_cost"], unit_price=price, total_price=price*number(p["quantity"]),
                         target_margin=number(p["snapshot"]["target"]), cost_snapshot=p))
            conn.execute(W.update().where(W.c.id == identifier).values(status="pending", updated_at=func.now()))
            conn.execute(I.update().where(I.c.id == r["inquiry_id"]).values(status="submitted"))
            conn.execute(A.insert().values(id=str(uuid4()), quote_version_id=identifier,
                         actor=actor, decision="submitted", comment="模拟角色提交，等待经理审批"))
            log(conn, actor, "quote_submitted", identifier)
    except SQLAlchemyError:
        raise DatabaseUnavailable("提交失败，事务已回滚。") from None


def decide(identifier, approved, comment, actor):
    require(actor, "经理")
    if not comment.strip():
        raise ValueError("请填写审批意见。")
    try:
        with engine().begin() as conn:
            r = locked(conn, identifier)
            if r["status"] != "pending":
                raise ValueError("只能处理待审批报价；该版本可能已被处理。")
            state = "approved" if approved else "rejected"
            conn.execute(W.update().where(W.c.id == identifier).values(status=state, updated_at=func.now()))
            conn.execute(A.insert().values(id=str(uuid4()), quote_version_id=identifier,
                         actor=actor, decision=state, comment=comment.strip()))
            log(conn, actor, "quote_"+state, identifier)
    except SQLAlchemyError:
        raise DatabaseUnavailable("审批失败，状态和日志均已回滚。") from None


def revise(identifier, actor):
    require(actor, "销售人员")
    try:
        with engine().begin() as conn:
            r = locked(conn, identifier)
            own(actor, r["owner"])
            if r["status"] not in ("approved", "rejected"):
                raise ValueError("仅已批准或已驳回报价可以创建修改版本。")
            conn.execute(select(I).where(I.c.id == r["inquiry_id"]).with_for_update())
            latest = conn.execute(select(func.max(W.c.version)).where(W.c.inquiry_id == r["inquiry_id"])).scalar()
            if latest != r["version"]:
                raise ValueError("已有更新版本，请操作最新版本，避免重复创建。")
            new_id = "QUO-" + uuid4().hex.upper()
            p = deepcopy(r["payload"])
            p["reference"] = {**p["reference"], "继承来源版本": identifier}
            conn.execute(W.insert().values(id=new_id, inquiry_id=r["inquiry_id"],
                         version=next_version(conn, r["inquiry_id"]), owner=actor, status="draft", payload=p))
            log(conn, actor, "quote_revised", new_id)
        return new_id
    except SQLAlchemyError:
        raise DatabaseUnavailable("新版本创建失败，事务已回滚。") from None


def records():
    try:
        with engine().connect() as conn:
            return [dict(r) for r in conn.execute(select(W).order_by(W.c.created_at.desc())).mappings()]
    except SQLAlchemyError:
        raise DatabaseUnavailable("报价记录读取失败。") from None


def audit(identifier):
    try:
        with engine().connect() as conn:
            approvals = [dict(r) for r in conn.execute(select(A).where(A.c.quote_version_id == identifier)
                         .order_by(A.c.created_at)).mappings()]
            operations = [dict(r) for r in conn.execute(select(L).where(
                L.c.details["quote_id"].astext == identifier).order_by(L.c.created_at)).mappings()]
            return approvals, operations
    except SQLAlchemyError:
        raise DatabaseUnavailable("审批和操作日志读取失败。") from None
