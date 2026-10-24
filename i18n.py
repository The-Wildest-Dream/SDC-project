"""Centralized, session-scoped translations for the Streamlit interface."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from string import Formatter

import streamlit as st

LANGS = ("zh-CN", "en", "ms-MY")
_RESOURCE_FILES = {"zh-CN": "zh-CN.json", "en": "en.json", "ms-MY": "ms.json", "ms": "ms.json"}
_resources = {
    lang: json.loads((Path(__file__).parent / "locales" / filename).read_text(encoding="utf-8"))
    for lang, filename in {k: _RESOURCE_FILES[k] for k in LANGS}.items()
}
_logger = logging.getLogger("quotation.i18n")
_missing: set[tuple[str, str]] = set()
_ALIAS = {"ms": "ms-MY"}


# Database / CSV field names remain stable internally; only their display labels change.
FIELD_KEYS = {
    "产品ID": "field.product_id", "产品名称": "field.product_name", "单位": "field.unit",
    "币种": "field.currency", "单位材料成本": "field.material_cost",
    "单位人工成本": "field.labor_cost", "单位制造费用": "field.overhead_cost",
    "成本更新时间": "field.cost_updated", "客户ID": "field.customer_id",
    "客户名称": "field.customer_name", "合作开始日期": "field.customer_since",
    "订单ID": "field.order_id", "订单日期": "field.order_date",
    "数量": "field.quantity", "成交单价": "field.transaction_price",
    "当时单位成本": "field.cost_at_sale", "约定付款日期": "field.due_date",
    "实际付款日期": "field.paid_date", "现有数量": "field.stock_on_hand",
    "已预留数量": "field.reserved_stock", "更新时间": "field.updated_at",
    "行号": "field.row", "字段": "field.field", "原因": "field.reason",
    "数据类型": "field.data_type", "样本提示": "field.sample_note",
    "已到期订单数": "field.due_orders", "按时付款率": "field.on_time_rate",
    "当前逾期未付订单数": "field.overdue_orders", "当前逾期未付金额": "field.overdue_amount",
    "历史逾期天数（累计）": "field.cumulative_late_days",
    "历史逾期天数": "field.historical_late_days", "当前逾期未付天数": "field.current_late_days",
    "数据覆盖时间": "field.coverage", "分析日期": "field.analysis_date",
    "约定账期": "field.contractual_due_date", "已付款金额": "field.paid_amount",
    "未付款金额": "field.unpaid_amount", "订单ID": "field.order_id",
    "成本项": "field.cost_item", "来源": "field.source", "原值": "field.original_value",
    "本次值": "field.current_value", "来源更新时间": "field.source_updated",
    "更新时间": "field.updated_at", "编号": "field.quote_id", "产品": "field.product",
    "需求": "field.demand", "可用库存": "field.available_stock",
    "报价ID": "field.quote_id", "询价ID": "field.inquiry_id", "版本": "field.version",
    "状态": "field.status", "单价": "field.unit_price", "总价": "field.total_price",
    "有效期": "field.valid_until", "交付日期": "field.delivery_date",
    "预付款比例": "field.prepayment_pct", "尾款账期天数": "field.balance_term",
    "年资金成本率": "field.annual_funding_rate", "标记": "field.demo_notice",
    "所属模拟销售": "field.demo_sales", "创建": "field.created_at",
    "更新": "field.updated_at", "审批决定": "field.decision", "审批意见": "field.approval_comment",
    "操作人": "field.actor", "操作": "field.action", "时间": "field.time",
    "详情": "field.details", "客户": "field.customer", "匹配交易数量": "field.match_count",
    "历史价格快照": "field.historical_prices", "付款表现": "field.payment_performance",
    "id": "field.audit_id", "quote_version_id": "field.quote_id", "actor": "field.actor",
    "decision": "field.decision", "comment": "field.approval_comment",
    "created_at": "field.created_at", "updated_at": "field.updated_at",
    "details": "field.details", "action": "field.action", "owner": "field.demo_sales",
    "inquiry_id": "field.inquiry_id", "version": "field.version", "status": "field.status",
    "days": "field.days", "valid_until": "field.valid_until", "reasons": "field.reasons",
    "rule_version": "field.rule_version", "amount": "field.amount",
}

KIND_KEYS = {"产品": "data.kind.products", "客户": "data.kind.customers",
             "历史交易": "data.kind.transactions", "库存": "data.kind.inventory"}
STATUS_KEYS = {"draft": "state.draft", "pending": "state.pending",
               "approved": "state.approved", "rejected": "state.rejected"}
ROLE_KEYS = {"销售甲": "role.sales_a", "销售乙": "role.sales_b", "经理": "role.manager"}

_TEXT_KEYS = {
    "无到期样本": "data.no_due_sample",
    "样本不足（到期订单少于10笔）": "data.payment_sample_low",
    "仅为模拟样本描述": "data.synthetic_sample",
    "模拟样本描述": "data.synthetic_sample",
    "模拟角色提交，等待经理审批": "audit.submitted_comment",
    "未修改产品成本": "quote.no_cost_change",
    "无": "common.none",
}
_EXPIRY_PATTERNS = (
    (re.compile(r"成本数据已更新于(?P<age>\d+)天前，超过(?P<threshold>\d+)天阈值，建议缩短至不超过3天"),
     "expiry.cost_stale"),
    (re.compile(r"成本更新时间距今(?P<age>\d+)天，未超过(?P<threshold>\d+)天阈值"),
     "expiry.cost_current"),
    (re.compile(r"原材料变化(?P<change>-?\d+(?:\.\d+)?)%，达到(?P<threshold>\d+)%阈值，建议不超过3天"),
     "expiry.material_change"),
    (re.compile(r"供应商报价至(?P<date>\d{4}-\d{2}-\d{2})；销售报价不超过该日期"),
     "expiry.supplier_until"),
    (re.compile(r"(?P<field>数量|当时单位成本)超出该组训练范围\[(?P<low>-?\d+(?:\.\d+)?), (?P<high>-?\d+(?:\.\d+)?)\]。"),
     "history.model_range"),
)
ERROR_KEYS = {
    "请输入有限的非负数字。": "error.nonnegative_number",
    "采购数量必须大于0。": "error.quantity_positive",
    "毛利率须满足：0 ≤ 最低毛利率 ≤ 目标毛利率 < 100%。": "error.margin_range",
    "拟报价必须大于0，才能计算毛利率并提交。": "error.price_positive",
    "拟报价低于最低允许单价，禁止提交审批。": "error.price_below_floor",
    "关键成本缺失，禁止提交审批：": "error.missing_costs",
    "交付日期和报价有效期不能早于今天。": "error.dates_past",
    "修改或清空产品成本必须填写修改理由。": "error.cost_reason_required",
    "请在报价记录中提交已保存的报价草稿。": "error.draft_required",
    "账期须为0–3650天；预付款及年资金成本率须为0–100%，毛利率须小于100%。": "error.payment_range",
    "有效期规则须满足：1 ≤ 默认天数 ≤ 最长天数，成本过期阈值大于0。": "error.expiry_range",
    "报价不存在。": "error.quote_missing",
    "报价有效期已过，禁止提交。": "error.quote_expired",
    "该询价已有报价或已提交，请在报价记录中修改草稿或创建新版本。": "error.quote_exists",
    "保存报价失败，数据库事务已回滚。": "error.quote_save",
    "只有草稿可修改。待审批版本已锁定，已结束版本须创建新版本。": "error.draft_only",
    "修改成本必须填写理由。": "error.cost_reason_required",
    "修改失败，数据库事务已回滚。": "error.edit_failed",
    "只有草稿可以提交，禁止重复提交。": "error.submit_draft_only",
    "提交失败，事务已回滚。": "error.submit_failed",
    "请填写审批意见。": "error.approval_comment_required",
    "只能处理待审批报价；该版本可能已被处理。": "error.pending_only",
    "审批失败，状态和日志均已回滚。": "error.approval_failed",
    "仅已批准或已驳回报价可以创建修改版本。": "error.revision_closed_only",
    "已有更新版本，请操作最新版本，避免重复创建。": "error.revision_latest_only",
    "新版本创建失败，事务已回滚。": "error.revision_failed",
    "报价记录读取失败。": "error.records_load",
    "审批和操作日志读取失败。": "error.audit_load",
    "询价保存失败，事务已回滚。请检查数据库及产品、客户数据。": "error.inquiry_save",
    "询价读取失败，请检查数据库。": "error.inquiry_load",
    "数据库连接配置无效或 DATABASE_URL 未配置。请检查 Replit 数据库设置。": "error.database_config",
    "数据库读取失败，请检查连接及数据表初始化状态。未使用临时数据回退。": "error.database_read",
    "数据库连接检查失败，请检查数据库状态。": "error.database_check",
    "不允许在部署环境初始化；生产结构通过 Replit Publish 管理。": "error.database_init_deploy",
    "数据表初始化失败；事务已回滚。": "error.database_init",
    "数据库导入失败，整批事务已回滚，没有保存半批数据。请检查连接、字段或数据库约束。": "error.database_import",
    "付款流水读取失败。": "error.ledger_read",
    "付款流水导入失败，事务已回滚。": "error.ledger_import",
    "所有数值必须为有限数字。": "error.finite_number",
    "采购数量必须为大于 0 的整数。": "error.integer_quantity",
    "目标毛利率必须大于或等于 0%，且小于 100%。": "error.target_margin_range",
    "各项成本和费用不能为负数。": "error.negative_cost",
}


def validate_catalogues():
    """Return missing/extra keys and interpolation mismatches for automated audits."""
    reference = set(_resources["zh-CN"])
    problems = {}
    formatter = Formatter()
    placeholders = {
        lang: {key: {name for _, name, _, _ in formatter.parse(value) if name}
               for key, value in _resources[lang].items()}
        for lang in LANGS
    }
    for lang in LANGS:
        current = set(_resources[lang])
        missing, extra = sorted(reference-current), sorted(current-reference)
        mismatch = sorted(
            key for key in reference & current
            if placeholders[lang].get(key, set()) != placeholders["zh-CN"].get(key, set())
        )
        if missing or extra or mismatch:
            problems[lang] = {"missing": missing, "extra": extra, "placeholders": mismatch}
    return problems


def normalize_language(code):
    code = _ALIAS.get(code, code)
    return code if code in LANGS else "zh-CN"


def initialize_language():
    """Initialize this Streamlit session from its URL, then persist selection in the URL."""
    if "ui_language" not in st.session_state:
        try:
            requested = st.query_params.get("lang", "zh-CN")
        except Exception:
            requested = "zh-CN"
        st.session_state["ui_language"] = normalize_language(requested)
    else:
        st.session_state["ui_language"] = normalize_language(st.session_state["ui_language"])
    try:
        if st.query_params.get("lang") != st.session_state["ui_language"]:
            st.query_params["lang"] = st.session_state["ui_language"]
    except Exception:
        # Some Streamlit test runners have no browser query-parameter context.
        pass
    return st.session_state["ui_language"]


def language():
    return normalize_language(st.session_state.get("ui_language", "zh-CN"))


def translate(key, lang=None, **values):
    lang = normalize_language(lang or language())
    if key not in _resources[lang]:
        marker = (lang, key)
        if marker not in _missing:
            _missing.add(marker)
            _logger.warning("Missing translation key %s for locale %s", key, lang)
        # Never expose the raw key; use a localized marker rather than silently
        # displaying another language's content.
        text = _resources[lang].get("i18n.missing", "翻译暂不可用")
    else:
        text = _resources[lang][key]
    try:
        return text.format(**values)
    except (KeyError, ValueError, IndexError):
        _logger.warning("Invalid interpolation for translation key %s", key)
        return text


def t(key, **values):
    return translate(key, **values)


def field_label(field):
    key = FIELD_KEYS.get(field)
    if key:
        return t(key)
    _logger.warning("Unmapped system field label: %s", field)
    return t("i18n.missing")


def kind_label(kind):
    key = KIND_KEYS.get(kind)
    return t(key) if key else t("i18n.missing")


def status_label(status):
    key = STATUS_KEYS.get(status)
    return t(key) if key else t("i18n.missing")


def role_label(role):
    key = ROLE_KEYS.get(role)
    return t(key) if key else role


def display_text(value):
    if not isinstance(value, str):
        return value
    if value in _TEXT_KEYS:
        return t(_TEXT_KEYS[value])
    for pattern, key in _EXPIRY_PATTERNS:
        match = pattern.fullmatch(value)
        if match:
            return t(key, **match.groupdict())
    exact = {
        "缺少成本更新时间，使用企业默认有效期": "expiry.cost_missing",
        "无原材料价格变化数据，按默认值": "expiry.material_missing",
        "无供应商报价到期日期，使用企业默认规则": "expiry.supplier_missing",
        "客户表现触发企业已启用的经理复核及最长3天规则": "expiry.customer_policy",
        "客户有逾期记录，仅提示经理复核；当前企业政策未允许其影响有效期": "expiry.customer_review",
    }
    return t(exact[value]) if value in exact else value


def display_error(error):
    """Translate known business errors; never leak an untranslated backend string."""
    message = str(error)
    if message.startswith("关键成本缺失，禁止提交审批："):
        names = message.split("：", 1)[1]
        return t("error.missing_costs", fields="、".join(field_label(x) for x in names.split("、")))
    key = ERROR_KEYS.get(message)
    if key:
        return t(key)
    _logger.warning("Unmapped user-visible error type: %s", type(error).__name__)
    return t("error.generic")


def _display_cell(column, value):
    if column == "数据类型":
        return kind_label(value)
    if column in ("字段", "成本项"):
        return field_label(value)
    if column == "原因":
        return _validation_reason(value)
    if column == "状态" and value in STATUS_KEYS:
        return status_label(value)
    if column == "审批决定" and value in STATUS_KEYS:
        return status_label(value)
    if column in ("样本提示", "按时付款率"):
        if value == "无到期样本":
            return t("data.no_due_sample")
        if value == "样本不足（到期订单少于10笔）":
            return t("data.payment_sample_low")
        if value == "仅为模拟样本描述":
            return t("data.synthetic_sample")
    if column == "操作" and value in ("quote_approved", "quote_rejected", "quote_submitted",
                                    "quote_draft_saved", "quote_draft_updated", "quote_revised"):
        return t("audit.action." + value.removeprefix("quote_"))
    if column == "操作人":
        return role_label(value)
    return display_text(value)


def _validation_reason(value):
    keys = {
        "存在重复字段": "data.error.duplicate_header",
        "缺少必需字段": "data.error.required_field",
        "未知字段，请使用示例 CSV 格式": "data.error.unknown_field",
        "列数与表头不一致": "data.error.column_count",
        "不能为空": "data.error.empty",
        "必须是有限的非负数；交易数量必须大于 0": "data.error.invalid_number",
        "必须为有效日期 YYYY-MM-DD": "data.error.invalid_date",
        "仅支持 CNY、USD、EUR，不自动换汇": "data.error.currency",
        "引用的产品不存在": "data.error.product_missing",
        "不能超过现有数量": "data.error.reserved_stock",
        "引用的客户不存在": "data.error.customer_missing",
        "不能早于客户合作开始日期": "data.error.customer_date",
        "必须与引用产品一致；不自动换算单位或币种": "data.error.product_mismatch",
        "不能早于订单日期": "data.error.order_date",
        "不允许导入空表": "data.error.empty_file",
    }
    if value.startswith("重复ID："):
        return t("data.error.duplicate_id", value=value.split("：", 1)[1])
    if value.startswith("请使用 UTF-8 CSV："):
        return t("data.error.csv_encoding")
    return t(keys[value]) if value in keys else t("i18n.missing")


def localize_records(rows):
    """Rename known system columns and translate fixed system-generated cell values."""
    output = []
    for row in rows:
        translated = {}
        for key, value in row.items():
            label = field_label(key) if key in FIELD_KEYS else key
            translated[label] = _display_cell(key, value)
        output.append(translated)
    return output


_JSON_KEYS = {
    "customer_id": "field.customer_id", "customer_name": "field.customer_name",
    "product_id": "field.product_id", "product_name": "field.product_name",
    "quantity": "field.quantity", "currency": "field.currency", "unit": "field.unit",
    "price": "field.unit_price", "delivery_date": "field.delivery_date",
    "valid_until": "field.valid_until", "snapshot": "json.snapshot", "reference": "json.reference",
    "costs": "json.costs", "source_costs": "json.source_costs", "reason": "field.reason",
    "minimum": "json.minimum_margin", "target": "json.target_margin",
    "source_updated": "json.source_updated", "entered_at": "json.entered_at",
    "terms": "json.payment_terms", "prepayment_pct": "field.prepayment_pct",
    "term_days": "field.balance_term", "annual_rate_pct": "field.annual_funding_rate",
    "finance": "finance.title", "expiry_advice": "expiry.title",
    "material_change_pct": "json.material_change", "supplier_expiry": "json.supplier_expiry",
    "policy": "json.policy", "default_days": "json.default_days", "max_days": "json.max_days",
    "stale_days": "json.stale_days", "material_threshold_pct": "json.material_threshold",
    "customer_review_affects_expiry": "json.customer_review_policy",
    "筛选开始日期": "history.start_date", "筛选结束日期": "history.end_date",
    "数量下限": "history.quantity_min", "数量上限": "history.quantity_max",
    "匹配笔数": "field.match_count", "订单ID": "field.order_id",
    "历史价格快照": "field.historical_prices", "口径": "history.method",
    "模型预测": "history.model", "模型说明": "history.model_note",
    "模型数据版本": "history.model_version", "继承来源版本": "json.revised_from",
}


def localize_json(value):
    if isinstance(value, dict):
        return {
            t(_JSON_KEYS[key]) if key in _JSON_KEYS else field_label(key) if key in FIELD_KEYS else key:
            localize_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [localize_json(item) for item in value]
    return value


def session_key(widget_name, semantic_name):
    """Readable, locale-independent keys for stateful widgets."""
    return f"{widget_name}.{semantic_name}"

