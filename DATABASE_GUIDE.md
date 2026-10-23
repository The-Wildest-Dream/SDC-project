# PostgreSQL 持久化

应用只读取环境变量 `DATABASE_URL`。不输出连接URL、密码或原始数据库异常，
SQL日志关闭，SQLAlchemy隐藏查询参数。使用SQLAlchemy及psycopg 3：
连接构建时把驱动明确设置为 `postgresql+psycopg`，不混用psycopg2。
本应用仍为Python + Streamlit，不使用模板中的Drizzle表定义。

## 开发环境操作

```bash
python db_manage.py check
python db_manage.py init
python db_manage.py seed
python db_manage.py counts
sh start.sh
```

- `check`：只运行SELECT 1，输出成功或安全错误信息，不输出凭据。
- `init`：只在开发环境人工执行；创建缺失表，不清空/重建表，不迁移已有列。
  应用启动不运行DDL。将来字段变化需单独开发迁移；生产结构由Replit Publish管理。
- `seed`：先校验固定种子合成数据，再在事务中仅补齐缺失ID。
  重复执行不覆盖已有业务修改，不插入重复订单，不动询价、报价版本或审批。
- `counts`：从数据库查询四类基础数据数量。
- `python verify_database.py`：开发集成验证，重复导入现有基础数据并产生导入日志，
  模拟事务中途失败验证回滚，验证不可用时不回退；不留下测试业务记录。
- `python -m unittest discover -s tests -v`：纯逻辑回归测试。

在Replit打开 **Tools → Database → Development Database → My Data** 查看表。
所有业务表在public schema。不要把连接URL贴入README、日志或聊天。
数据库是整个应用共享的，不再是各浏览器私有数据。目前未实现用户登录和权限，
操作日志使用`demo_operator`标记演示操作者，不冒充已认证用户。

## 表与关联

| 表 | 主键与关系 |
|---|---|
| products | 产品ID，产品成本、单位、币种与更新时间 |
| customers | 客户ID，客户名称、合作日期 |
| transactions | 订单ID；客户ID→customers，产品ID→products；价格/成本及单位币种快照，付款日期可NULL |
| inventory | 产品ID为主键及products外键；一产品一条库存 |
| inquiries | id；customer_id→customers，product_id→products；数量、单位、币种、状态 |
| quote_versions | id；inquiry_id→inquiries；同询价的version唯一；价格、毛利及cost_snapshot JSONB |
| approval_records | id；quote_version_id→quote_versions；操作者、决定、备注与时间 |
| operation_logs | id；操作类型、操作者、JSONB摘要和时间，无业务删除级联 |

客户/产品各对应多笔交易与询价；询价对应多个报价版本；报价版本对应多条审批记录。
删除受外键限制，禁止隐式级联清空历史数据。数据库还约束非负金额、正数量、
预留量不超过现有量、合理日期以及版本唯一性。
操作日志不保存连接信息或CSV全文，与数据写入同事务提交。
询价、报价版本和审批的表结构已准备；本阶段未新增其业务保存/审批界面，
现有计算结果仅为未提交的页面草稿，不能当作已保存报价。

## CSV导入

从原“会话内整表替换”调整为**按ID合并**：
新增ID插入，相同ID更新，未上传记录保留，不提供批量删除。
一次上传的所有表先做字段校验，再获取数据库事务级导入锁，
读取最新数据、合并校验所有外键及单位币种，最后一起写入。
一个错误或数据库异常则全部回滚，成功提示只在提交完成后出现。
订单ID为数据库主键，重复批次不会产生重复订单。
演示导入特殊处理为同ID跳过，而不是更新。

业务数据不放进session_state，不自动写临时文件，不自动恢复默认数据；
每次页面读取都从数据库取同一事务快照。session_state只存输入控件、
未提交计算草稿、上传文件和操作反馈。数据库不可用时明确显示错误并停止数据页面。
四份sample_data CSV只是可重复生成的示例文件，绝不作为故障后备存储。
