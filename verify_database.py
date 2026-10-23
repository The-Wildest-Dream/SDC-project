"""开发数据库集成验证：幂等导入、失败回滚、只读内容指纹。"""
import hashlib
import json
import sys
from copy import deepcopy

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from database import engine, import_csv, read_data, DatabaseUnavailable
from data_service import csv_bytes
from generate_data import generate


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    default=str).encode()).hexdigest()


def verify():
    before = read_data()
    uploads = {k: csv_bytes(k, v) for k, v in before.items() if v}
    assert not import_csv(uploads)
    assert not import_csv(uploads)
    assert fingerprint(read_data()) == fingerprint(before), "重复导入改变业务内容"
    assert not import_csv({k: csv_bytes(k, v) for k, v in generate().items()}, seed_only=True)
    assert fingerprint(read_data()) == fingerprint(before), "重复演示导入改变业务内容"
    # 在已经执行写入、尚未提交时制造数据库异常，验证全部回滚。
    changed = deepcopy(before["产品"])
    changed[0]["产品名称"] += "_rollback_probe"

    def fail_before_log(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO operation_logs"):
            raise SQLAlchemyError("controlled rollback probe")

    event.listen(engine(), "before_cursor_execute", fail_before_log)
    rejected = False
    try:
        import_csv({"产品": csv_bytes("产品", changed)})
    except DatabaseUnavailable:
        rejected = True
    finally:
        event.remove(engine(), "before_cursor_execute", fail_before_log)
    assert rejected, "故障未被拒绝"
    assert fingerprint(read_data()) == fingerprint(before), "失败后留下部分修改"
    # 模拟连接失败：不得回退到示例数据或文件。
    def fail_read(conn, cursor, statement, parameters, context, executemany):
        raise SQLAlchemyError("controlled availability probe")
    event.listen(engine(), "before_cursor_execute", fail_read)
    try:
        try:
            read_data()
        except DatabaseUnavailable:
            pass
        else:
            raise AssertionError("数据库失败未明确报错")
    finally:
        event.remove(engine(), "before_cursor_execute", fail_read)
    print("数据库幂等、事务回滚和不可用报错验证通过。")
    print("业务数据SHA256:", fingerprint(read_data()))
    print("记录数:", {k: len(v) for k, v in read_data().items()})


if __name__ == "__main__":
    try:
        verify()
    except DatabaseUnavailable as error:
        print(str(error))
        sys.exit(1)
