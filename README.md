# 中小制造企业报价辅助系统

中文 Python + Streamlit 学生比赛演示，当前完成六页导航、报价计算器和数据中心。
重点是价格分析与报价决策；数据中心支持模拟库存、历史付款记录及付款表现汇总，库存提醒待实现。
数据生成规则、CSV格式、导入及付款口径见 `DATA_GUIDE.md`。
新建询价、成本来源、历史参考、人工报价及提交规则见 `QUOTATION_GUIDE.md`，其说明替代下方旧版计算器的逐页验证流程。
最新模拟角色、报价草稿编辑、经理审批、版本保留、下载和工作台说明见 `WORKFLOW_GUIDE.md`，以此为当前流程。
历史成交价格预测已接入：训练、评估、适用范围及发布加载见 `MODEL_GUIDE.md`。旧文档“未训练AI”的描述仅代表此前阶段。
所有示例数据为模拟数据；业务基础数据已接入PostgreSQL持久化，不接入机器学习。
数据库初始化、检查、关系说明与导入规则见 `DATABASE_GUIDE.md`。

## 启动

需要 Python 3.10 或更新版本。

```bash
python -m pip install -r requirements.txt
python db_manage.py init
python db_manage.py seed
sh start.sh
```

默认访问 http://localhost:3000。启动脚本优先使用 `PORT` 环境变量。
也可直接运行 `python -m streamlit run app.py`（默认端口 8501）。
Replit 中运行 `artifacts/quotation: web` 工作流后打开“制造企业报价辅助系统”预览。

## 主要文件

- `app.py`：应用入口、公共说明与六页侧边栏导航。
- `quote_page.py`：原报价计算器的表单、校验提示、结果与公式核对。
- `pending_page.py`：待实现页面的统一展示和范围说明。
- `calculator.py`：独立计算函数，使用 Decimal 进行十进制计算。
- `data_page.py`：数据中心表格、CSV下载上传和付款汇总。
- `data_service.py`：CSV解析、跨表校验、可比交易筛选及付款汇总逻辑。
- `generate_data.py`：固定种子数据生成及CSV输出。
- `shared_data.py`：页面数据库读写入口及安全错误展示。
- `db_schema.py`：八张业务表及约束定义。
- `database.py`：安全连接、数据库读取、事务化合并导入。
- `db_manage.py`：开发初始化、演示导入、连接检查与记录计数命令。
- `verify_database.py`：实际数据库幂等、回滚和不可用验证。
- `history_page.py`：读取同产品、币种、单位的历史交易（报价建议待实现）。
- `tests/test_data.py`：生成、校验、引用、付款口径回归测试。
- `tests/test_calculator.py`：计算函数回归测试，不依赖页面。
- `requirements.txt`：Streamlit 依赖版本。
- `start.sh`：启动命令及监听地址、端口设置。

## 计算逻辑

1. 单位成本 = 单位材料成本 + 单位人工成本 + 单位制造费用
   + (整批固定费用 + 整批物流费用) / 数量。
2. 参考单价 = 单位成本 / (1 - 目标毛利率 / 100)。
3. 整单报价 = 参考单价 × 数量。

数量必须为正整数；毛利率取值为 0%（含）至 100%（不含）；
费用不可为负，产品名称不可为空。非法输入不产生报价。
毛利率是利润占售价的比例，不是成本加价率。
中间值不提前舍入，仅展示金额时保留两位小数。

默认模拟案例：100 件，材料 30 元、人工 15 元、制造 5 元，
整批固定费用 800 元、物流 200 元，毛利率 20%。
单位成本为 60 元，参考单价为 75 元，整单报价为 7,500 元。

## 逐页验证

1. 点击 Run，打开 Preview：默认显示“工作台”，左侧有六个导航项。
2. 工作台：显示“待实现”，不应出现业务统计数字。
3. 数据中心：按 `DATA_GUIDE.md` 查看模拟数据、下载上传CSV和验证付款口径。
4. 新建询价与成本计算：默认参数点击“计算报价”，应得到 60、75、
   7,500 元；查看代入过程。数量改为 0 或负数、毛利率改为 100 或
   101 后提交，应显示错误，且不保留上一份报价结果。
5. 历史价格与报价建议：选择产品查看可比历史交易，报价建议仍为待实现。
6. 审批中心：显示“待实现”，没有提交、通过或驳回按钮。
7. 报价记录与下载：显示“待实现”，不应把计算结果伪装成已保存记录，
   没有下载按钮。
8. 在页面之间切换，再返回计算页，仍可重新输入并计算。
   表单未提交的修改不保存；当前会话中的最近一次计算结果可继续查看。

运行计算逻辑测试：`python -m unittest discover -s tests -v`。
启动脚本和预览服务配置沿用原有设置；新增SQLAlchemy及psycopg 3依赖。

## License

This project is licensed under the Apache License 2.0.
See the [LICENSE](LICENSE) file for details.
