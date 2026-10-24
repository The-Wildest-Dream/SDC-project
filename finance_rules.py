"""Payment financing cost, cutoff-based payment analysis, and rule-based quote validity."""
from datetime import date
from decimal import Decimal
from quotation_rules import number

RULE_VERSION = "PAY-EXP-1"


def apply_funding(result, finance):
    if result["missing"] or not finance:
        return result
    adjusted = dict(result)
    adjusted["unit_cost"] = result["unit_cost"] + finance["funding_unit"]
    adjusted["floor"] = adjusted["unit_cost"]/(1-number(finance["minimum"])/100)
    adjusted["target"] = adjusted["unit_cost"]/(1-number(finance["target"])/100)
    adjusted["funding_cost"] = finance["funding_cost"]
    return adjusted


def funding(base_cost, quantity, minimum, margin, prepayment_pct, term_days, annual_rate):
    """Estimate the advance using the immediate-payment total; do not create a circular quote."""
    cost, q = number(base_cost), number(quantity)
    low, m, advance_pct, rate = map(number, (minimum, margin, prepayment_pct, annual_rate))
    days = int(term_days)
    if days < 0 or days > 3650 or advance_pct > 100 or rate > 100 or m >= 100 or low > 100:
        raise ValueError("账期须为0–3650天；预付款及年资金成本率须为0–100%，毛利率须小于100%。")
    immediate_total = (cost * q) / (1 - m / 100)
    advance = max(Decimal(0), cost*q-immediate_total*advance_pct/100)
    charge = advance*rate/100*days/365
    return {"minimum": str(low), "target": str(m),
            "immediate_unit": cost/(1-m/100),
            "advance_amount": advance, "funding_cost": charge,
            "funding_unit": charge/q,
            "conditional_unit": (cost+charge/q)/(1-m/100),
            "difference_unit": (charge/q)/(1-m/100),
            "immediate_reference_total": immediate_total}


def expiry_advice(as_of, cost_updated, default_days=7, max_days=30,
                  supplier_expiry=None, material_change_pct=None,
                  stale_days=90, change_threshold_pct=10, customer_overdue=False,
                  policy_review=False):
    if default_days < 1 or max_days < default_days or stale_days < 1:
        raise ValueError("有效期规则须满足：1 ≤ 默认天数 ≤ 最长天数，成本过期阈值大于0。")
    reasons, days = [], min(default_days, max_days)
    age = (as_of-date.fromisoformat(str(cost_updated)[:10])).days if cost_updated else None
    if age is None:
        reasons.append("缺少成本更新时间，使用企业默认有效期")
    elif age > stale_days:
        days = min(days, 3)
        reasons.append(f"成本数据已更新于{age}天前，超过{stale_days}天阈值，建议缩短至不超过3天")
    else:
        reasons.append(f"成本更新时间距今{age}天，未超过{stale_days}天阈值")
    if material_change_pct is None:
        reasons.append("无原材料价格变化数据，按默认值")
    elif abs(float(material_change_pct)) >= change_threshold_pct:
        days = min(days, 3)
        reasons.append(f"原材料变化{material_change_pct:.1f}%，达到{change_threshold_pct}%阈值，建议不超过3天")
    if supplier_expiry:
        supplier = date.fromisoformat(str(supplier_expiry)[:10])
        days = max(1, min(days, (supplier-as_of).days))
        reasons.append(f"供应商报价至{supplier.isoformat()}；销售报价不超过该日期")
    else:
        reasons.append("无供应商报价到期日期，使用企业默认规则")
    if customer_overdue and policy_review:
        days = min(days, 3)
        reasons.append("客户表现触发企业已启用的经理复核及最长3天规则")
    elif customer_overdue:
        reasons.append("客户有逾期记录，仅提示经理复核；当前企业政策未允许其影响有效期")
    return {"days": days, "valid_until": (as_of+__import__("datetime").timedelta(days=days)).isoformat(),
            "reasons": reasons, "rule_version": RULE_VERSION}


def ledger_summary(bundle, ledger, customer_id, as_of, sample_min=10):
    """Use contractual due dates and aggregate installments; exclude payments after the cutoff."""
    orders = [r for r in bundle["历史交易"] if r["客户ID"] == customer_id
              and r["订单日期"] <= as_of.isoformat()]
    detail, due_count, on_time = [], 0, 0
    overdue_count, overdue_amount = 0, Decimal(0)
    start, end = [], []
    for o in orders:
        due = date.fromisoformat(o["约定付款日期"])
        amount = Decimal(str(o["成交单价"]))*Decimal(str(o["数量"]))
        rows = [x for x in ledger if x["订单ID"] == o["订单ID"]
                and x["付款日期"] <= as_of.isoformat()]
        if rows:
            paid = sum((Decimal(str(x["金额"])) for x in rows), Decimal(0))
            paid_by = max((x["付款日期"] for x in rows if Decimal(str(x["金额"])) > 0), default="")
        else:
            # Legacy compatibility: the old paid date represents one full settlement only when no ledger rows exist.
            paid_by = o.get("实际付款日期", "") if o.get("实际付款日期", "") <= as_of.isoformat() else ""
            paid = amount if paid_by else Decimal(0)
        balance = max(Decimal(0), amount-paid)
        if due <= as_of:
            due_count += 1
            if paid >= amount and paid_by and date.fromisoformat(paid_by) <= due:
                on_time += 1
        late_days = max(0, (date.fromisoformat(paid_by)-due).days) if paid_by else 0
        overdue_days = max(0, (as_of-due).days) if balance and due < as_of else 0
        if overdue_days:
            overdue_count += 1
            overdue_amount += balance
        detail.append({"订单ID": o["订单ID"], "约定账期": o["约定付款日期"],
                       "已付款金额": str(paid), "未付款金额": str(balance),
                       "已结清逾期天数": late_days, "当前逾期天数": overdue_days})
        start.append(o["订单日期"]); end.append(o["订单日期"])
    return {"客户ID": customer_id, "分析日期": as_of.isoformat(), "已到期订单数": due_count,
            "按时付款率": on_time/due_count if due_count else None,
            "当前逾期未付订单数": overdue_count, "当前逾期未付金额": str(overdue_amount),
            "样本数": len(orders), "样本提示": "数据不足" if due_count < sample_min else "模拟样本描述",
            "数据覆盖时间": f"{min(start)} 至 {max(end)}" if start else "无历史记录",
            "逾期明细": detail}
