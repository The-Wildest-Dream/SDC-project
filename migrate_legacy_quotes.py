"""开发环境一次性兼容旧报价；重复执行不改变已迁移版本。"""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from database import engine, DatabaseUnavailable
from db_schema import quote_workflows as W, quote_versions as V, inquiries as I
from db_schema import inquiry_details as D, tables, approval_records as A
from sqlalchemy.exc import SQLAlchemyError


def migrate():
    try:
        with engine().begin() as conn:
            old = conn.execute(select(V).where(~V.c.id.in_(select(W.c.id)))).mappings().all()
            for v in old:
                r = conn.execute(select(I).where(I.c.id == v["inquiry_id"])).mappings().one()
                d = conn.execute(select(D).where(D.c.inquiry_id == v["inquiry_id"])).mappings().one()
                c = conn.execute(select(tables["客户"]).where(tables["客户"].c["客户ID"] == r["customer_id"])).mappings().one()
                decision = conn.execute(select(A.c.decision).where(A.c.quote_version_id == v["id"])
                                        .order_by(A.c.created_at.desc())).scalars().first()
                s = v["cost_snapshot"]
                payload = {"customer_id": r["customer_id"], "customer_name": c["客户名称"],
                           "product_id": r["product_id"], "product_name": s["product_name"],
                           "quantity": str(v["quantity"]), "unit": v["unit"], "currency": v["currency"],
                           "price": str(v["unit_price"]), "valid_until": str(d["valid_until"]),
                           "delivery_date": str(d["delivery_date"]), "snapshot": s,
                           "reference": {"说明": "旧版未保存历史参考快照，不补造；客户名称和有效期来自迁移时关联记录。"}}
                conn.execute(insert(W).values(id=v["id"], inquiry_id=v["inquiry_id"],
                    version=v["version"], owner="销售甲",
                    status=decision if decision in ("approved", "rejected") else "pending",
                    payload=payload, created_at=v["created_at"]).on_conflict_do_nothing())
    except SQLAlchemyError:
        raise DatabaseUnavailable("旧报价兼容迁移失败，已回滚。") from None


if __name__ == "__main__":
    import os
    if os.environ.get("REPLIT_DEPLOYMENT") == "1":
        raise SystemExit("此脚本仅用于开发环境。")
    try:
        migrate()
        print("旧报价兼容处理完成，原记录保留。")
    except DatabaseUnavailable as e:
        raise SystemExit(str(e))
