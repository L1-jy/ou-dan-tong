"""瓯单通 CLI 入口。默认 mock 模式（无需 Key 即可演示全管线）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from store import Store
from agent import parse_chat, query, briefing
from sim_chats import (
    SCENARIO1_CHAT, SCENARIO1_MOCK, SCENARIO3_CHAT, SCENARIO3_MOCK,
)


def run_demo(store: Store, live: bool = False):
    print("=== 场景1：乱中取单（贴群聊 → 订单卡片 + 任务）===")
    card, _ = parse_chat(SCENARIO1_CHAT, store, mock=None if live else SCENARIO1_MOCK)
    print(card)

    print("\n=== 场景2：随口查（万博那单到哪了）===")
    print(query("万博那单到哪了？", store))

    print("\n=== 场景3：变更捕获（NMX 数量改 6000）===")
    card, _ = parse_chat(SCENARIO3_CHAT, store, mock=None if live else SCENARIO3_MOCK)
    print(card)

    print("\n=== 场景5：今日简报 ===")
    print(briefing(store))


def main():
    import argparse
    p = argparse.ArgumentParser(description="瓯单通 · 订单协同智能体")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("reset").help = "清空台账"
    sub.add_parser("demo").help = "Mock 演示（无需 API Key）"
    sub.add_parser("live").help = "真实 LLM 抽取（需设置 DEEPSEEK_API_KEY）"
    q = sub.add_parser("query")
    q.add_argument("text", help="口语查询，如 '万博那单到哪了'")
    sub.add_parser("briefing").help = "生成今日简报"
    args = p.parse_args()

    store = Store()
    if args.cmd == "reset":
        store.reset()
        print("已清空台账。")
    elif args.cmd == "demo":
        run_demo(store, live=False)
    elif args.cmd == "live":
        run_demo(store, live=True)
    elif args.cmd == "query":
        print(query(args.text, store))
    elif args.cmd == "briefing":
        print(briefing(store))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
