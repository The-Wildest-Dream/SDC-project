"""Session-scoped static interface translations; business values remain untouched."""
import hashlib
import json
import logging
from pathlib import Path
import streamlit as st

LANGS = ("zh-CN", "en", "ms")
_resources = {lang: json.loads((Path(__file__).parent/"locales"/f"{lang}.json").read_text(encoding="utf-8"))
              for lang in LANGS}
# Stable source text -> semantic resource key. Internal values and user data are never translated.
_source = {
 "中小制造企业报价辅助系统":"app.title","学生比赛演示 · 价格分析与报价决策":"app.subtitle",
 "所有展示数据均为模拟数据，仅用于教学与比赛演示，不作为实际交易报价。":"app.demo",
 "模拟角色 / 演示人员":"role.label","仅为比赛演示的角色切换，不是真实身份认证或生产级权限系统。":"role.warning",
 "工作台":"dashboard.title","数据中心":"data.title","新建询价与成本计算":"quote.title",
 "历史价格与报价建议":"history.title","审批中心":"approval.title","报价记录与下载":"records.title",
 "新建询价":"button.new","进入审批中心":"button.approvals","进入报价记录与下载":"button.records",
 "提交审批":"button.submit","保存报价草稿":"button.save","确认审批":"button.confirm",
 "批准":"button.approve","驳回":"button.reject","下载CSV报价单":"button.download.csv",
 "下载可打印HTML报价单":"button.download.html","草稿":"state.draft","待审批":"state.pending",
 "已批准":"state.approved","已驳回":"state.rejected","全部":"state.all","模拟数据":"common.simulated",
 "客户":"common.customer","产品":"common.product","数量":"common.quantity","币种":"common.currency",
 "状态":"common.status","单位":"common.unit","日期":"common.date","原因":"common.reason",
 "成本底线与目标报价（保存时的成本快照）":"history.base","历史参考（同产品、币种、单位）":"history.reference",
 "模型预测成交单价（独立辅助参考）":"history.model","人工拟报价":"history.manual",
 "成本来源及修改理由":"history.cost_source","付款条件与综合报价参考":"finance.title",
 "立即付款参考报价":"finance.immediate","当前付款条件参考报价":"finance.conditional",
 "差额":"finance.difference","预计垫付金额":"finance.advance","资金占用成本":"finance.cost",
 "有效期建议":"expiry.title","暂无待审批报价。":"approval.no_pending",
 "报价单":"export.title","模拟演示 · 非真实交易凭证":"export.demo",
 "数据不足":"common.insufficient","暂无数据":"common.empty"
}
_missing = set()


def language():
    return st.session_state.get("ui_language", "zh-CN")


def t(key, **values):
    lang = language()
    if key not in _resources[lang]:
        _missing.add(key)
        logging.getLogger("quotation.i18n").warning("Missing translation key: %s", key)
    text = _resources[lang].get(key, _resources["zh-CN"].get(key, key))
    try:
        return text.format(**values)
    except (KeyError, ValueError):
        return text


def _translate(value):
    if not isinstance(value, str) or language() == "zh-CN":
        return value
    key = _source.get(value)
    if key is None:
        if value not in _missing:
            _missing.add(value)
            logging.getLogger("quotation.i18n").warning("Missing translation entry for interface text: %s", value)
        return value
    return t(key)


def install():
    """Translate UI labels while deriving widget keys from stable source labels."""
    names = ("header", "title", "subheader", "caption", "write", "markdown", "info",
             "warning", "error", "success", "button", "page_link", "selectbox", "radio",
             "text_input", "text_area", "number_input", "date_input", "file_uploader",
             "download_button", "metric", "expander", "checkbox", "form_submit_button")
    for name in names:
        original = getattr(st, name)
        if getattr(original, "_i18n_wrapped", False):
            continue
        def make_wrapper(fn, widget_name):
            def wrapped(*args, **kwargs):
                args = list(args)
                if args and isinstance(args[0], str):
                    source = args[0]
                    if widget_name in {"selectbox","radio","text_input","text_area","number_input",
                                       "date_input","file_uploader","checkbox","button","form_submit_button"}:
                        kwargs.setdefault("key", "i18n_"+hashlib.sha1((widget_name+source).encode()).hexdigest()[:16])
                    args[0] = _translate(source)
                for label in ("label", "help"):
                    if isinstance(kwargs.get(label), str):
                        kwargs[label] = _translate(kwargs[label])
                return fn(*args, **kwargs)
            wrapped._i18n_wrapped = True
            return wrapped
        setattr(st, name, make_wrapper(original, name))

