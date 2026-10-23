"""开发数据库模拟流程验证；保留标记为自动校验的演示记录。"""
from datetime import date, timedelta
from copy import deepcopy
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from database import read_data, engine, DatabaseUnavailable
from inquiry_service import save_inquiry
from workflow_service import create_draft, edit_draft, submit_quote, decide, revise, records, audit
from quotation_rules import COSTS
from quote_exports import csv_export, html_export


def rejects(function, *args):
    try:
        function(*args)
    except ValueError:
        return
    raise AssertionError("角色或状态检查未拒绝非法操作")


def run():
    data = read_data()
    p, c = data["产品"][0], data["客户"][0]
    costs = {f: str(p[f]) if i < 3 else "0" for i, f in enumerate(COSTS)}
    identifier = save_inquiry(c["客户ID"], p["产品ID"], 10, date.today()+timedelta(days=30),
                 date.today()+timedelta(days=10), costs, "模拟自动校验", 10, 20, actor="销售甲")
    qid = create_draft(identifier, "200", {"说明": "模拟自动校验，无历史推荐"}, "销售甲")
    rejects(submit_quote, qid, "销售乙")
    rejects(submit_quote, qid, "经理")
    submit_quote(qid, "销售甲")
    rejects(submit_quote, qid, "销售甲")
    rejects(edit_draft, qid, {}, "销售甲")
    rejects(decide, qid, True, "不应成功", "销售甲")
    def failure(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO approval_records"):
            raise SQLAlchemyError("controlled rollback")
    event.listen(engine(), "before_cursor_execute", failure)
    try:
        try:
            decide(qid, True, "模拟数据库故障", "经理")
        except DatabaseUnavailable:
            pass
        else:
            raise AssertionError("未模拟审批失败")
    finally:
        event.remove(engine(), "before_cursor_execute", failure)
    first = next(r for r in records() if r["id"] == qid)
    assert first["status"] == "pending"
    assert len(audit(qid)[0]) == 1
    decide(qid, True, "自动校验批准V1", "经理")
    rejects(decide, qid, False, "重复审批", "经理")
    first = next(r for r in records() if r["id"] == qid)
    assert "已批准" in csv_export(first).decode("utf-8-sig")
    assert "模拟演示" in html_export(first).decode()
    original = deepcopy(first["payload"])
    q2 = revise(qid, "销售甲")
    rejects(revise, qid, "销售甲")
    second = next(r for r in records() if r["id"] == q2)
    assert "草稿/未批准" in html_export(second).decode()
    changes = dict(quantity="12", price="210", delivery_date=original["delivery_date"],
                   valid_until=original["valid_until"], costs=costs, reason="模拟自动校验",
                   minimum=10, target=20)
    rejects(edit_draft, q2, changes, "销售乙")
    edit_draft(q2, changes, "销售甲")
    submit_quote(q2, "销售甲")
    decide(q2, False, "自动校验驳回V2", "经理")
    assert next(r for r in records() if r["id"] == qid)["payload"] == original
    assert next(r for r in records() if r["id"] == q2)["status"] == "rejected"
    print("角色/归属、状态锁定、审批事务回滚、重复拦截、下载标记及版本保留验证通过。")


if __name__ == "__main__":
    try:
        run()
    except DatabaseUnavailable as e:
        raise SystemExit(str(e))
