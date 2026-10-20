"""模拟业务群聊数据 + 对应的抽取 Mock（无 Key 也能跑全管线）。
真实运行时由 LLM 产出同样结构的 list[dict]，Mock 仅用于测试/演示。"""

SCENARIO1_CHAT = """王工：李经理，NMX-60 断路器外壳 5000 个，什么时候能给报个价？客户挺急的
李经理：稍等，我算一下，明天上午给你
（第二天）
李经理：王工，NMX-60 外壳 5000 个，单价 3.2，11 月 20 号交，含 13% 税
王工：行，先安排打样 20 个发过来确认
万博机电：李经理，TND-3 稳压器 200 台麻烦排一下，下周要
李经理：好的，TND-3 下周一起排产，28 号前出货"""

SCENARIO1_MOCK = [
    {"type": "order", "customer": "王工（XX电气）", "product": "NMX-60 断路器外壳", "spec": "",
     "qty": 5000, "unit_price": "3.2", "delivery_date": "2026-11-20", "status_hint": "已报价",
     "sample_flag": "打样", "source_excerpt": "NMX-60 外壳 5000 个，单价 3.2，11 月 20 号交…先安排打样 20 个"},
    {"type": "order", "customer": "万博机电", "product": "TND-3 稳压器", "spec": "",
     "qty": 200, "unit_price": "待报价", "delivery_date": "2026-10-28", "status_hint": "生产中",
     "sample_flag": "大货", "source_excerpt": "TND-3 下周一起排产，28 号前出货"},
    {"type": "task", "task_content": "安排打样 20 个", "owner": "李经理", "task_deadline": "2026-10-22"},
]

SCENARIO3_CHAT = "王工：李经理，NMX-60 那批数量改一下，改成 6000 个"
SCENARIO3_MOCK = [
    {"type": "order", "customer": "王工（XX电气）", "product": "NMX-60 断路器外壳",
     "qty": 6000, "source_excerpt": "NMX-60 那批数量改一下，改成 6000 个"},
]

# 缺信息陷阱：无客户/产品，应被跳过
MISSING_TRAP_MOCK = [
    {"type": "order", "customer": "", "product": ""},
]
