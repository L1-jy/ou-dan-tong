"""管线自测：用 Mock 抽取验证 入库/变更/查询/简报 全链路（无需 Key）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from store import Store
from agent import parse_chat, query, briefing
from sim_chats import SCENARIO1_MOCK, SCENARIO3_MOCK


def test_pipeline():
    store = Store()
    store.reset()

    # 场景1：应入库 2 单 + 1 任务
    _, info = parse_chat("dummy", store, mock=SCENARIO1_MOCK)
    assert len(info["orders"]) == 2, info["orders"]
    assert len(info["tasks"]) == 1
    assert store.orders[0]["order_id"].startswith("ORD-")

    # 场景3：变更应 UPDATE 且留痕，qty 5000 → 6000
    parse_chat("dummy", store, mock=SCENARIO3_MOCK)
    nmx = next(o for o in store.orders if o["product"] == "NMX-60 断路器外壳")
    assert nmx["qty"] == 6000, nmx
    assert len(nmx["changes"]) >= 1, nmx["changes"]

    # 场景2：查询带原文依据
    ans = query("万博那单到哪了？", store)
    assert "万博机电" in ans and "依据" in ans, ans

    # 场景5：简报数字来自台账
    b = briefing(store)
    assert "新增订单" in b and "临期交付" in b, b

    print("ALL TESTS PASSED ✅")
    print("-" * 40)
    print(b)


if __name__ == "__main__":
    test_pipeline()
