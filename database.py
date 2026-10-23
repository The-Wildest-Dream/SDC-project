"""PostgreSQL 持久化。禁止打印原始连接或数据库异常。"""
import os
from datetime import date
from decimal import Decimal
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from data_service import SCHEMAS, DATES, NUMBERS, parse_csv, validate_bundle
from db_schema import metadata, tables, operation_logs


class DatabaseUnavailable(RuntimeError):
    """只包含可公开展示的错误，不附带底层异常或凭据。"""


@lru_cache(maxsize=1)
def engine():
    try:
        raw = os.environ.get("DATABASE_URL")
        if not raw:
            raise ValueError
        url = make_url(raw)
        if url.get_backend_name() not in ("postgresql", "postgres"):
            raise ValueError
        return create_engine(url.set(drivername="postgresql+psycopg"),
                             echo=False, hide_parameters=True, pool_pre_ping=True,
                             connect_args={"connect_timeout": 10})
    except Exception:
        raise DatabaseUnavailable("数据库连接配置无效或 DATABASE_URL 未配置。请检查 Replit 数据库设置。") from None


def _read(conn):
    result = {}
    for kind, table in tables.items():
        rows = conn.execute(select(table).order_by(table.c[SCHEMAS[kind][0]])).mappings()
        result[kind] = [
            {field: (value.isoformat() if isinstance(value, date)
                     else "" if value is None else value)
             for field, value in row.items()} for row in rows
        ]
    return result


def read_data():
    try:
        # 四表读取使用同一快照，避免并发导入时读到混合版本。
        with engine().connect().execution_options(isolation_level="REPEATABLE READ") as conn:
            with conn.begin():
                return _read(conn)
    except SQLAlchemyError:
        raise DatabaseUnavailable("数据库读取失败，请检查连接及数据表初始化状态。未使用临时数据回退。") from None


def check_connection():
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        raise DatabaseUnavailable("数据库连接检查失败，请检查数据库状态。") from None


def initialize():
    """仅供人工执行的开发数据库初始化，不在启动或部署中调用。"""
    if os.environ.get("REPLIT_DEPLOYMENT") == "1":
        raise DatabaseUnavailable("不允许在部署环境初始化；生产结构通过 Replit Publish 管理。")
    try:
        with engine().begin() as conn:
            metadata.create_all(conn)
    except SQLAlchemyError:
        raise DatabaseUnavailable("数据表初始化失败；事务已回滚。") from None


def _values(row):
    return {f: (date.fromisoformat(v) if v else None) if f in DATES
            else Decimal(str(v)) if f in NUMBERS else v for f, v in row.items()}


def import_csv(uploads, *, seed_only=False):
    parsed, errors = {}, []
    for kind, content in uploads.items():
        rows, issues = parse_csv(kind, content)
        parsed[kind] = rows
        errors.extend({"数据类型": kind, **e} for e in issues)
    if errors:
        return errors
    try:
        with engine().begin() as conn:
            # 所有导入共用事务级锁，串行化“读取-校验-写入”。
            conn.execute(text("SELECT pg_advisory_xact_lock(72623109)"))
            current = _read(conn)
            candidate = {}
            for kind in SCHEMAS:
                pk = SCHEMAS[kind][0]
                by_id = {r[pk]: r for r in current[kind]}
                for row in parsed.get(kind, []):
                    if not seed_only or row[pk] not in by_id:
                        by_id[row[pk]] = row
                candidate[kind] = list(by_id.values())
            errors = validate_bundle(candidate)
            if errors:
                return errors
            changed = {}
            for kind, table in tables.items():
                pk = SCHEMAS[kind][0]
                count = 0
                for row in parsed.get(kind, []):
                    values = _values({f: row[f] for f in SCHEMAS[kind]})
                    stmt = insert(table).values(**values)
                    if seed_only:
                        stmt = stmt.on_conflict_do_nothing(index_elements=[pk])
                    else:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=[pk],
                            set_={f: stmt.excluded[f] for f in SCHEMAS[kind] if f != pk})
                    count += conn.execute(stmt).rowcount
                if count:
                    changed[kind] = count
            if changed:
                conn.execute(operation_logs.insert().values(
                    id=str(uuid4()), action="demo_import" if seed_only else "csv_import",
                    actor="demo_operator", details={"模拟数据": True, "写入数量": changed}))
        # 仅在事务提交成功之后返回成功状态。
        return []
    except SQLAlchemyError:
        raise DatabaseUnavailable("数据库导入失败，整批事务已回滚，没有保存半批数据。请检查连接、字段或数据库约束。") from None
