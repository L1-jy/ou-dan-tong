# -*- coding: utf-8 -*-
"""瓯单通 · 模块一 模拟群聊数据生成器 + 自检脚本（零第三方依赖，Python 3.8+）

接口约定（契约 1，见 01_方案与规划/接口与模块对接约定.md）：
    输出 data/chat_logs.json，结构：
    {
      "version": str,
      "generated": "YYYY-MM-DD",
      "groups": [
        {
          "scene_id": str,          # 场景唯一编号，如 S1-G1
          "scene_type": str,        # 五类 + 动态演进
          "title": str,             # 场景简述
          "group": str,             # 群名
          "messages": [
            {"group": str, "speaker": str, "time": "YYYY-MM-DD HH:MM", "text": str},
            ...
          ],                        # 组内按 time 升序
          "notes": [str, ...],      # 陷阱/设计说明
          "expected": {...}         # 预期抽取结果 + validator_target(ok|missing|conflict|abnormal)
        }
      ]
    }

用法：
    python gen_sim_chats.py             # 生成 + 自检（任一验收指标不通过则以非零码退出）
    python gen_sim_chats.py --check-only
    python gen_sim_chats.py --out <dir>

设计要点：
    - 确定性输出：语料为静态常量，无随机，重复运行字节级一致，便于回归。
    - 口语化陷阱：别称（法兰≈304法兰盘DN80）、残缺（"那批"）、口语时间（周五/下周）、
      多角色交叉（客户/业务员/车间/仓库/老板娘 5 类角色）。
    - 场景隔离：组间客户+产品组合互不复用，避免跨组实体污染。
异常处理：文件读写失败、schema/时序/覆盖校验失败均有明确报错与非零退出码。
"""

import json
import os
import sys

VERSION = "1.0"

# ---------------------------------------------------------------------------
# 语料：11 组场景（5 类 × 2 组 + 1 组长链动态演进）
# messages 以 (speaker, time, text) 三元组书写，输出时自动补 group 键。
# time 用 "YYYY-MM-DD HH:MM" 零填充格式，保证字符串比较 == 时间比较。
# ---------------------------------------------------------------------------

GROUPS = [
    # ============ 场景一：新建订单（要素齐全，正常成交） ============
    {
        "scene_id": "S1-G1",
        "scene_type": "新建订单",
        "title": "法兰盘下单（要素齐全）",
        "group": "永嘉精密机械对接群",
        "messages": [
            ("王总", "2026-10-20 09:12", "小陈，304 法兰盘 DN80 的 250 个，月底前能出吗"),
            ("小陈", "2026-10-20 09:20", "王总，能出，我记下了：法兰 DN80 250 件，交期 28 号，价格还是上次那个 18.5"),
            ("王总", "2026-10-20 09:26", "行，就这么定，别给我排到月底去"),
        ],
        "notes": ["产品别称：'法兰' 与正式名 '304法兰盘DN80' 并存，考验别称归一", "要素齐全：客户/产品/规格/数量/单价/交期 6 项完整"],
        "expected": {
            "entity": "订单", "entity_key_hint": "王总（永嘉××精密机械）+ 304法兰盘DN80",
            "fields": {"数量": "250", "单价": "18.5", "交期": "2026-10-28", "状态": "已确认"},
            "validator_target": "ok",
        },
    },
    {
        "scene_id": "S1-G2",
        "scene_type": "新建订单",
        "title": "断路器下单（数量+口语交期）",
        "group": "瓯越五金贸易对接群",
        "messages": [
            ("李姐", "2026-10-20 10:03", "小陈，DZ47-63 三相的 50 个，下周发，先报个价"),
            ("小陈", "2026-10-20 10:11", "李姐，DZ47-63 三相 50 个，单价 26，下周二 27 号发货到瓯越仓库哈"),
            ("李姐", "2026-10-20 10:15", "可以，就这么办"),
        ],
        "notes": ["口语交期'下周'需要近似换算，最终以业务员确认的 27 号为准", "客户名'李姐'为常用口语，全称'瓯越五金贸易'藏在群名/地址里"],
        "expected": {
            "entity": "订单", "entity_key_hint": "李姐（瓯越五金贸易）+ DZ47-63 三相断路器",
            "fields": {"数量": "50", "单价": "26", "交期": "2026-10-27", "状态": "已确认"},
            "validator_target": "ok",
        },
    },
    # ============ 场景二：多次迭代更新（改数量/交期） ============
    {
        "scene_id": "S2-G1",
        "scene_type": "多次迭代更新",
        "title": "法兰盘单 数量与交期变更",
        "group": "永嘉精密机械对接群",
        "messages": [
            ("王总", "2026-10-20 14:02", "小陈，法兰那单数量加 50，凑 300"),
            ("小陈", "2026-10-20 14:10", "收到，法兰 250→300 件"),
            ("王总", "2026-10-20 14:12", "交期也赶下，28 号太晚了，24 号周五给我"),
            ("小陈", "2026-10-20 14:18", "好的，交期改 10-24，我跟车间说下优先级"),
        ],
        "notes": ["同单两次变更：数量 250→300、交期 10-28→10-24", "必须命中已有单（S1-G1 主键：王总+法兰盘），不得新建"],
        "expected": {
            "entity": "订单", "entity_key_hint": "复用 S1-G1 实体",
            "fields": {"数量": "300", "交期": "2026-10-24"},
            "change_log": ["数量 250→300", "交期 10-28→10-24"],
            "validator_target": "ok",
        },
    },
    {
        "scene_id": "S2-G2",
        "scene_type": "多次迭代更新",
        "title": "断路器单 数量两改+交期提前",
        "group": "瓯越五金贸易对接群",
        "messages": [
            ("李姐", "2026-10-20 15:30", "小陈，DZ47 那个加到 80 个"),
            ("小陈", "2026-10-20 15:34", "收到，50→80"),
            ("李姐", "2026-10-20 16:02", "算了还是 65 个，客户临时砍了，别做多"),
            ("小陈", "2026-10-20 16:08", "行，按 65，交期还是 27 号？"),
            ("李姐", "2026-10-20 16:20", "改周五 24 号，客户催得急"),
        ],
        "notes": ["数量 50→80→65（先增后减），交期 27→24，履历应 3 条", "'还是 65 个'为口语数量表达，需正确抽取 65 而非多加一名"],
        "expected": {
            "entity": "订单", "entity_key_hint": "复用 S1-G2 实体",
            "fields": {"数量": "65", "交期": "2026-10-24"},
            "change_log": ["数量 50→80", "数量 80→65", "交期 10-27→10-24"],
            "validator_target": "ok",
        },
    },
    # ============ 场景三：缺失信息（缺数值/缺意图，触发追问） ============
    {
        "scene_id": "S3-G1",
        "scene_type": "缺失信息",
        "title": "法兰盘补排单（缺交期、单号歧义）",
        "group": "永嘉精密机械对接群",
        "messages": [
            ("王总", "2026-10-21 09:05", "小陈，法兰那批的货再帮我排上一批，我这边急"),
            ("小陈", "2026-10-21 09:14", "王总，您说的是法兰 DN80 那单加量吗？加多少个、交期什么时候？我跟车间好排"),
        ],
        "notes": ["'那批''加一批'指向不明：是 S1-G1 加量还是新单？缺数量、缺交期", "正确行为=缺失追问（missing），不得自行假设数量入库"],
        "expected": {
            "entity": "订单", "entity_key_hint": "疑似复用 S1-G1，但信息不足",
            "missing": ["数量", "交期", "是否改单"],
            "validator_target": "missing",
        },
    },
    {
        "scene_id": "S3-G2",
        "scene_type": "缺失信息",
        "title": "NMX-60 再走一批（仅产品名）",
        "group": "瓯越五金贸易对接群",
        "messages": [
            ("李姐", "2026-10-21 10:40", "小陈，NMX-60 再给我走一批"),
            ("小陈", "2026-10-21 10:46", "李姐，这批是新单还是补之前的？数量多少？"),
        ],
        "notes": ["只说产品名'NMX-60'，缺数量；并且是新建还是补单（S1-G2 是 DZ47，不匹配）意图不明", "正确行为=缺失追问"],
        "expected": {
            "entity": "订单", "entity_key_hint": "NMX-60（新实体，与既有 DZ47 单无关）",
            "missing": ["数量", "意向（新建 or 补单）"],
            "validator_target": "missing",
        },
    },
    # ============ 场景四：矛盾冲突（同一字段两个口径） ============
    {
        "scene_id": "S4-G1",
        "scene_type": "矛盾冲突",
        "title": "法兰盘数量 300 vs 280 打架",
        "group": "永嘉精密机械对接群",
        "messages": [
            ("王总", "2026-10-21 11:20", "小陈，法兰那单 28 号前我给你也说下，凑 300 个一起做"),
            ("老板娘", "2026-10-21 11:35", "小陈，王总那边我早上记的是 280 个，你怎么跟车间说 300？核实下，别做错"),
            ("小陈", "2026-10-21 11:50", "我这边记录是 300，王总 14 号改的，我再跟他确认一次并同步大家"),
        ],
        "notes": ["同一单数量出现 300（王总）与 280（老板娘）两个口径，必须冲突标红而非自动覆盖", "期待最终人工确认后落定，冲突期间不写台账（或标 pending）"],
        "expected": {
            "entity": "订单", "entity_key_hint": "复用 S1-G1/S2-G1 实体",
            "conflict": {"字段": "数量", "口径A": "300", "口径B": "280"},
            "validator_target": "conflict",
        },
    },
    {
        "scene_id": "S4-G2",
        "scene_type": "矛盾冲突",
        "title": "交期 25 号 vs 28 号冲突",
        "group": "车间排产群",
        "messages": [
            ("小陈", "2026-10-21 13:05", "大家注意，DZ47-63 那单跟客户说好 25 号出货，车间排一下"),
            ("陈工", "2026-10-21 13:22", "25 号做不出来，材料后天到，最快 28 号，你跟客户说说"),
            ("老周", "2026-10-21 13:30", "仓库这边 29 号能齐，供参考"),
            ("小陈", "2026-10-21 13:41", "我再去跟客户协商，交期先按 28 号备着"),
        ],
        "notes": ["对客承诺 25 号 vs 车间产能 28 号 vs 仓库 29 号，三方口径冲突", "正确行为=冲突标红，交期待确认后再覆盖"],
        "expected": {
            "entity": "订单", "entity_key_hint": "复用 S1-G2/S2-G2 实体（DZ47-63）",
            "conflict": {"字段": "交期", "口径A": "10-25", "口径B": "10-28", "口径C": "10-29"},
            "validator_target": "conflict",
        },
    },
    # ============ 场景五：明显异常（负数量 / 日期倒挂，拦截） ============
    {
        "scene_id": "S5-G1",
        "scene_type": "明显异常",
        "title": "数量改 -300（负数，疑似笔误）",
        "group": "瓯越五金贸易对接群",
        "messages": [
            ("李姐", "2026-10-21 15:00", "小陈，DZ47 那个数量给我改成 -300"),
            ("小陈", "2026-10-21 15:08", "李姐，数量改成负数系统记不了，您是打算减 300 还是取消？我按您的意思记录"),
        ],
        "notes": ["'-300'为明显异常负数量，正常业务不可能", "正确行为=异常拦截并反问意图（减量 or 取消），不自动写入"],
        "expected": {
            "entity": "订单", "entity_key_hint": "复用 S1-G2/S2-G2 实体",
            "abnormal": {"字段": "数量", "值": "-300", "原因": "负数量"},
            "validator_target": "abnormal",
        },
    },
    {
        "scene_id": "S5-G2",
        "scene_type": "明显异常",
        "title": "交期倒挂（10-19 早于下单日）",
        "group": "车间排产群",
        "messages": [
            ("陈工", "2026-10-21 16:10", "小陈，法兰那单你是不是写错了，交期给我写 10-19，今天都 21 号了"),
            ("老周", "2026-10-21 16:15", "对，19 号都过去了，肯定不对"),
            ("小陈", "2026-10-21 16:22", "我手滑写错了，实际是 24 号，我改回来"),
        ],
        "notes": ["交期早于当天（倒挂）触发异常拦截，提示录入错误", "随后人工纠正为 10-24，纠正后正常入库"],
        "expected": {
            "entity": "订单", "entity_key_hint": "复用 S1-G1/S2-G1 实体",
            "abnormal": {"字段": "交期", "值": "2026-10-19", "原因": "早于下单日/当天"},
            "validator_target": "abnormal",
        },
    },
    # ============ 场景六：动态演进样本（唯一一组，跨 3 轮变更） ============
    {
        "scene_id": "S6-E1",
        "scene_type": "动态演进",
        "title": "电机壳 Y2-132 订单 3 轮变更长链",
        "group": "永嘉精密机械对接群",
        "messages": [
            ("王总", "2026-10-20 09:40", "小陈，电机壳 Y2-132 的 400 个，11 月 9 号能交吗"),
            ("小陈", "2026-10-20 09:55", "王总，Y2-132 电机壳 400 个，11-09 交，没问题，给您排上"),
            ("王总", "2026-10-20 17:20", "小陈，电机壳改 500 个，交期最好赶 11 月 5 号，客户那边催"),
            ("小陈", "2026-10-21 09:02", "王总，改 500 收到；不过 11-05 产能不够，车间建议分两批：05 号先出 300，12 号出 200"),
            ("老板娘", "2026-10-21 09:30", "500 个全要，分两批可以：第一批 11-08 出 300，第二批 11-15 出 200，跟王总确认下"),
            ("王总", "2026-10-21 09:48", "可以，按老板娘说的来，11-08 一批 300，11-15 一批 200"),
        ],
        "notes": [
            "3 轮变更：数量 400→500；交期 11-09→11-05→（分批）11-08+11-15；方案由车间→老板娘协商落定",
            "履历应 ≥3 条；最新状态=数量500、分两批（11-08 出 300 / 11-15 出 200）",
            "测试要点：查询'那单到哪了'必须返回最终方案，而非 400 个的旧版本",
        ],
        "expected": {
            "entity": "订单", "entity_key_hint": "王总（永嘉××精密机械）+ 电机壳 Y2-132",
            "fields": {"数量": "500", "交期": "两批：11-08（300 件）/ 11-15（200 件）", "状态": "已确认"},
            "change_log": [
                "数量 400→500",
                "交期 11-09→11-05（提前）",
                "交期方案 → 分批 11-08(300)/11-15(200)",
            ],
            "validator_target": "ok",
        },
    },
]

# 五类场景 + 动态演进 的验收最低数量
MIN_PER_TYPE = 2          # 5 类业务场景各 ≥2 组
MIN_DYNAMIC = 1           # 动态演进 ≥1 组
MIN_GROUPS = 11           # 总组数下限
MIN_MSGS_PER_GROUP = 2    # 单组消息数下限

REQUIRED_KEYS = ("group", "speaker", "time", "text")
SCENE_TYPES = ("新建订单", "多次迭代更新", "缺失信息", "矛盾冲突", "明显异常")


# ---------------------------------------------------------------------------
# 校验：结构 / 时序 / 覆盖 三类，全部通过才返回 True
# ---------------------------------------------------------------------------

def validate(src, verbose=True):
    """对生成结果执行自检。src 为 build_groups() 产出的 groups list。"""
    errors = []

    # --- A2 结构校验：四键齐全且非空 ---
    seen_ids = set()
    for g in src:
        sid = g.get("scene_id", "")
        if sid in seen_ids:
            errors.append(f"[A2] 重复 scene_id: {sid}")
        seen_ids.add(sid)
        if g.get("scene_type") not in SCENE_TYPES + ("动态演进",):
            errors.append(f"[A2] {sid} 未知 scene_type: {g.get('scene_type')}")
        for m in g.get("messages", []):
            for k in REQUIRED_KEYS:
                if k not in m or not str(m[k]).strip():
                    errors.append(f"[A2] {sid} 消息缺字段/为空: {k} -> {m}")

    # --- A3 时序校验：组内 time 单调递增（零填充格式下字符串比较即时间比较） ---
    for g in src:
        times = [m["time"] for m in g.get("messages", [])]
        for i in range(1, len(times)):
            if times[i] <= times[i - 1]:
                errors.append(f"[A3] {g['scene_id']} 时间非递增: {times[i-1]} -> {times[i]}")

    # --- A4 覆盖与规模校验：A1 场景覆盖、A4 组规模 ---
    type_count = {t: 0 for t in SCENE_TYPES}
    dynamic_count = 0
    for g in src:
        if g["scene_type"] == "动态演进":
            dynamic_count += 1
        else:
            type_count[g["scene_type"]] = type_count.get(g["scene_type"], 0) + 1
        if len(g.get("messages", [])) < MIN_MSGS_PER_GROUP:
            errors.append(f"[A4] {g['scene_id']} 消息数 {len(g['messages'])} < {MIN_MSGS_PER_GROUP}")
    for t, c in type_count.items():
        if c < MIN_PER_TYPE:
            errors.append(f"[A1] 场景'{t}' 仅 {c} 组，需 ≥{MIN_PER_TYPE}")
    if dynamic_count < MIN_DYNAMIC:
        errors.append(f"[A1] 动态演进样本 {dynamic_count} 组，需 ≥{MIN_DYNAMIC}")
    if len(src) < MIN_GROUPS:
        errors.append(f"[A4] 总组数 {len(src)} < {MIN_GROUPS}")

    if verbose:
        print("=" * 62)
        print("瓯单通·模块一 模拟数据自检报告")
        print("=" * 62)
        for g in src:
            mark = "✓" if g["scene_type"] != "动态演进" else "◆"
            print(f"  {mark} {g['scene_id']:<6} {g['scene_type']:<8} "
                  f"{g['title'][:22]:<24} {len(g['messages'])} 条")
        print("-" * 62)
        print(f"  总组数        : {len(src)}   （要求 ≥{MIN_GROUPS}）")
        for t in SCENE_TYPES:
            print(f"  {t:<8} : {type_count[t]} 组   （要求 ≥{MIN_PER_TYPE}）")
        print(f"  动态演进     : {dynamic_count} 组   （要求 ≥{MIN_DYNAMIC}）")
        print("-" * 62)
        if errors:
            print(f"  校验未通过，{len(errors)} 处问题：")
            for e in errors:
                print(f"    ✗ {e}")
            print("=" * 62)
            return False
        print("  全部验收指标（A1~A4）通过，数据可交付。")
        print("=" * 62)
    return not errors


# ---------------------------------------------------------------------------
# 组装 / 导出
# ---------------------------------------------------------------------------

def build_groups():
    """将语料组装成契约 1 结构：把 (speaker, time, text) 三元组展开为完整消息 dict。"""
    groups = []
    for g in GROUPS:
        messages = []
        for speaker, time_, text in g["messages"]:
            messages.append({"group": g["group"], "speaker": speaker, "time": time_, "text": text})
        item = {
            "scene_id": g["scene_id"],
            "scene_type": g["scene_type"],
            "title": g["title"],
            "group": g["group"],
            "messages": messages,
            "notes": g.get("notes", []),
            "expected": g.get("expected", {}),
        }
        # A5：实体可关联性检查前置——每个 expected 里必须有 entity 或 entity_key_hint
        if not item["expected"].get("entity") and not item["expected"].get("entity_key_hint"):
            raise ValueError(f"{g['scene_id']} 缺 expected.entity / entity_key_hint，无法支撑模块二主键匹配")
        groups.append(item)
    return groups


def export_txt(groups):
    """导出人读纯文本版（可直接粘贴展示），用【场景】分割。"""
    lines = ["瓯单通 · 模块一 模拟群聊数据（全部为自建模拟内容，企业名已化名）", ""]
    for g in groups:
        lines.append(f"【{g['scene_id']} · {g['scene_type']}】{g['title']}")
        lines.append(f"群：{g['group']}    预期校验：{g['expected'].get('validator_target', '-')}")
        lines.append("─" * 52)
        for m in g["messages"]:
            lines.append(f"[{m['time']}] {m['speaker']}：{m['text']}")
        lines.append("")
    return "\n".join(lines)


def write_outputs(groups, out_dir):
    """写 chat_logs.json 与 chat_logs.txt；目录不存在则创建。出错抛 OSError。"""
    os.makedirs(out_dir, exist_ok=True)  # exist_ok 兼容 3.8+，create 失败会抛 OSError
    data = {
        "version": VERSION,
        "generated": "2026-10-20",
        "purpose": "瓯单通模块一·口语化群聊模拟数据集（契约1格式），供模块二抽取/模块四查询/模块五走查使用",
        "note_contract": "每条消息含 group/speaker/time/text 四键；数组=一次群聊记录；动态演进=同组按时间升序多轮消息",
        "groups": groups,
    }
    json_path = os.path.join(out_dir, "chat_logs.json")
    txt_path = os.path.join(out_dir, "chat_logs.txt")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(export_txt(groups))
    return json_path, txt_path


def main():
    args = [a for a in sys.argv[1:]]
    check_only = "--check-only" in args
    out_dir = "./data"
    if "--out" in args:
        i = args.index("--out")
        if i + 1 < len(args) and not args[i + 1].startswith("--"):
            out_dir = args[i + 1]

    try:
        if check_only:
            # 仅校验已存在的文件：从 chat_logs.json 读回再校验，保证与交付物一致
            src_path = os.path.join(out_dir, "chat_logs.json")
            with open(src_path, encoding="utf-8") as f:
                data = json.load(f)
            groups = data["groups"]
            print(f"读回 {src_path}（{len(groups)} 组）进行校验…")
        else:
            groups = build_groups()
            json_path, txt_path = write_outputs(groups, out_dir)
            print(f"已生成：\n  {json_path}\n  {txt_path}")

        ok = validate(groups)
        return 0 if ok else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"执行失败：{type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
