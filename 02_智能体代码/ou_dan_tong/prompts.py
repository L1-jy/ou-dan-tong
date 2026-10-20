"""提示词骨架（平台无关，可直接复用）。"""

EXTRACTION_SYSTEM = """你是制造企业订单要素提取器。从聊天记录中提取所有订单线索与待办任务，
严格输出 JSON 数组，不编造缺失字段，缺失则填 null：
[{
 "type": "order" | "task",
 "customer": "公司简称", "product": "", "spec": "", "qty": null,
 "unit_price": "可含'待报价'", "delivery_date": "YYYY-MM-DD|null",
 "sample_flag": "打样|大货|无", "status_hint": "沟通中|已报价|已确认|生产中|已交付|null",
 "task_content": "", "owner": "", "task_deadline": "YYYY-MM-DD|null",
 "source_excerpt": "支撑本结论的原文片段，≤100字"
}]
只依据原文；两人对话注意上下文归属；出现"改成/变更为/加到"视为变更线索。"""

QUERY_SYSTEM = """根据查询结果用中文口语回答，每条结论后必须附「依据：{source_excerpt}」。
只陈述数据表中存在的事实，不得补充表外信息。多条结果用列表，先说客户和产品，
再说状态、数量、交期，最后给一句主动建议（如临期提醒）。"""

BRIEFING_SYSTEM = """把以下聚合数据汇总成一份简洁的今日订单协同简报，中文，分条列出，不要编造数字。"""

STATUS_ORDER = ["沟通中", "已报价", "已确认", "生产中", "已交付"]
STATUS_RANK = {s: i for i, s in enumerate(STATUS_ORDER)}


def card_text(order: dict, tasks: list, is_new: bool) -> str:
    tag = "已登记新订单" if is_new else "已更新订单"
    lines = [
        f"✅ {tag} {order['order_id']}",
        f"📦 客户：{order['customer']}｜产品：{order['product']} {order.get('spec','')} ×{order.get('qty','?')}",
        f"💰 单价 {order.get('unit_price','待报价')} ｜ 📅 交期 {order.get('delivery_date') or '待定'} ｜ 状态：{order.get('status')}",
    ]
    if tasks:
        t = "；".join(f"{x['content']}" + (f"（{x['owner']}）" if x.get('owner') else "（待认领）") for x in tasks)
        lines.append(f"🔬 自动记下任务：{t}")
    if order.get("source_excerpt"):
        lines.append(f"📎 依据：\"{order['source_excerpt']}\"")
    return "\n".join(lines)


def query_text(order: dict, suggestion: str = "") -> str:
    base = (f"{order['customer']}的{order['product']} {order.get('spec','')} ×{order.get('qty','?')}，"
            f"当前状态{order.get('status')}，预计{order.get('delivery_date') or '待定'}交付。")
    ev = f"📎 依据：\"{order.get('source_excerpt','')}\"。" if order.get("source_excerpt") else ""
    return base + ev + (suggestion and f" {suggestion}")


def briefing_text(stats: dict) -> str:
    today = stats.get("date", "")
    lines = [f"📋 {today} 订单协同简报",
             f"🆕 新增订单：{stats['new']} 笔（{stats.get('new_customers','')}）",
             f"💰 待报价：{stats['pending_quote']} 笔（最急：{stats.get('most_urgent','无')}）",
             f"⏰ 临期交付：{stats['due_soon']} 笔（{stats.get('due_list','')}）",
             f"❗ 逾期任务：{stats['overdue']} 项（{stats.get('overdue_list','')}）"]
    return "\n".join(lines)
