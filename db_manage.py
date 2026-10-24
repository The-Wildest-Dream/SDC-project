"""Safe database operations that do not print connection strings or raw database errors."""
import argparse
import sys

from database import check_connection, initialize, read_data, import_csv, DatabaseUnavailable
from data_service import csv_bytes
from generate_data import generate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "init", "seed", "counts"])
    args = parser.parse_args()
    try:
        if args.command == "check":
            check_connection()
            print("数据库连接正常（SELECT 1 通过；未输出连接信息）。")
        elif args.command == "init":
            initialize()
            print("开发数据表初始化完成：仅创建缺失表，不清空或重建已有表。")
        elif args.command == "seed":
            errors = import_csv({k: csv_bytes(k, v) for k, v in generate().items()}, seed_only=True)
            if errors:
                print("演示数据校验失败，未写入。")
                return 1
            print("模拟演示数据导入已提交；已有ID保留，询价与报价不受影响。")
        else:
            print({k: len(v) for k, v in read_data().items()})
        return 0
    except DatabaseUnavailable as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
