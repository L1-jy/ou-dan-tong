"""模块二自测：验证 缺失/冲突/异常 判定（契约4）正确识别模块一五类陷阱。

无需 API Key。运行：python test_validator.py
- test_cases()：单元级，逐条断言 classify_order 的 status 判定。
- test_against_module1()：跨模块，确认模块一 6 类场景均被本模块覆盖。
- demo()：端到端跑一段含 5 类陷阱的群聊，打印模块二产出的卡片。
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validator import classify_order
from contracts import CheckStatus
from store import Store
from agent import parse_chat


def _order(**kw):
    base = {"type": "order", "customer": "温州机电", "product": "法兰盘", "spec": "",
            "qty": None, "unit_price": "待报价", "delivery_date": None,
            "status_hint": "沟通中", "sample_flag": "无", "source_excerpt": ""}
    base.update(kw)
    return base


def test_cases():
    # 1. 正常新建
    assert classify_order(_order(qty=100, delivery_date="2026-11-01")).status == CheckStatus.OK

    # 2. 异常：负数数量（笔误）
    r = classify_order(_order(qty=-300, delivery_date="2026-11-01",
                              source_excerpt="数量改 -300，算错了对吧"))
    assert r.status == CheckStatus.ABNORMAL and "负数" in r.message, r

    # 3. 异常：日期倒挂（交期早于下单日）
    r = classify_order(_order(qty=100, delivery_date="2026-10-19"), order_date="2026-10-20")
    assert r.status == CheckStatus.ABNORMAL and "倒挂" in r.message, r

    # 4. 异常：交期格式错误
    r = classify_order(_order(qty=100, delivery_date="10-19"))
    assert r.status == CheckStatus.ABNORMAL and "格式" in r.message, r

    # 5. 冲突：与在途单数量矛盾，且无变更动词
    existing = _order(qty=300, delivery_date="2026-11-25")
    r = classify_order(_order(qty=280, delivery_date="2026-11-25",
                              source_excerpt="法兰盘280个就够了"), existing=existing)
    assert r.status == CheckStatus.CONFLICT and "矛盾" in r.message, r

    # 6. 冲突：交期矛盾（独立断言，无变更动词）
    existing = _order(qty=300, delivery_date="2026-11-25")
    r = classify_order(_order(qty=300, delivery_date="2026-11-28",
                              source_excerpt="交期28号交货"), existing=existing)
    assert r.status == CheckStatus.CONFLICT, r

    # 7. 正常更新：带变更动词，不判冲突（应落库为 6000）
    existing = _order(qty=5000, delivery_date="2026-11-20")
    r = classify_order(_order(qty=6000, delivery_date="2026-11-20",
                              source_excerpt="数量改成6000个"), existing=existing)
    assert r.status == CheckStatus.OK, r

    # 8. 缺失：缺数量
    assert classify_order(_order(qty=None, delivery_date="2026-11-01")).status == CheckStatus.MISSING

    # 9. 缺失：缺交期
    assert classify_order(_order(qty=100, delivery_date=None)).status == CheckStatus.MISSING

    # 10. 缺失：仅产品名（无客户/数量/交期）
    r = classify_order({"customer": "", "product": "NMX-60", "qty": None, "delivery_date": None})
    assert r.status == CheckStatus.MISSING, r

    print("模块二 单元自测 ALL PASSED ✅")


def test_against_module1():
    """模块一 6 类场景 → 模块二应覆盖的状态。"""
    p = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "..", "03_演示数据", "data", "chat_logs.json"))
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    groups = data if isinstance(data, list) else data.get("groups", [])
    types = {g.get("scene_type") for g in groups}
    # 场景类型 → 模块二应判定状态
    mapping = {
        "新建订单": CheckStatus.OK,
        "多次迭代更新": CheckStatus.OK,
        "动态演进": CheckStatus.OK,
        "缺失信息": CheckStatus.MISSING,
        "矛盾冲突": CheckStatus.CONFLICT,
        "明显异常": CheckStatus.ABNORMAL,
    }
    for t, expect in mapping.items():
        assert t in types, f"模块一缺少场景类型：{t}"
    print(f"模块一场景类型({len(types)}类) ↔ 模块二判定覆盖：全部对齐 ✅")


def demo():
    print("\n===== 模块二端到端演示：一段含 5 类陷阱的群聊 =====")
    store = Store()
    store.reset()
    now = "2026-10-20T14:30:00"

    # (1) 正常新建
    parse_chat("x", store, mock=[_order(customer="温州机电", product="法兰盘",
                  qty=300, delivery_date="2026-11-25", source_excerpt="法兰盘300个，11-25交")], now=now)
    # (2) 冲突：同一单又来个 280（无变更动词）
    card, _ = parse_chat("x", store, mock=[_order(customer="温州机电", product="法兰盘",
                  qty=280, delivery_date="2026-11-25", source_excerpt="法兰盘280个就够了")], now=now)
    print("\n[矛盾冲突] " + card)
    # (3) 异常：负数数量
    card, _ = parse_chat("x", store, mock=[_order(customer="温州机电", product="法兰盘",
                  qty=-300, delivery_date="2026-11-25", source_excerpt="数量改 -300")], now=now)
    print("\n[明显异常] " + card)
    # (4) 缺失：有客户产品但缺数量/交期
    card, _ = parse_chat("x", store, mock=[_order(customer="瑞安五金", product="螺栓",
                  qty=None, delivery_date=None, source_excerpt="瑞安五金螺栓再走一批")], now=now)
    print("\n[缺失信息] " + card)
    # (5) 正常更新（变更动词）
    card, _ = parse_chat("x", store, mock=[_order(customer="温州机电", product="法兰盘",
                  qty=6000, delivery_date="2026-11-25", source_excerpt="法兰盘数量改成6000个")], now=now)
    print("\n[正常更新] " + card)

    print("\n----- 当前台账（含冲突标记 / 缺失占位）-----")
    for o in store.orders:
        flag = o.get("flags") or {}
        print(f"  {o['order_id']} {o['customer']}/{o['product']} ×{o.get('qty')} "
              f"交期{o.get('delivery_date')} 状态={o['status']} 标记={flag or '无'}")


if __name__ == "__main__":
    test_cases()
    test_against_module1()
    demo()
