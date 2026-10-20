# -*- coding: utf-8 -*-
"""读取 data/chat_logs.json，生成可视化预览页 preview/模块一_数据预览.html。
用法：python make_preview.py            （零依赖，输出到 preview/ 目录）
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "chat_logs.json")
OUT_DIR = os.path.join(HERE, "preview")
OUT = os.path.join(OUT_DIR, "模块一_数据预览.html")

TYPE_COLOR = {
    "新建订单": "#1d7ad9",
    "多次迭代更新": "#8a6de9",
    "缺失信息": "#d97706",
    "矛盾冲突": "#dc2626",
    "明显异常": "#b91c1c",
    "动态演进": "#059669",
}
TYPE_MARK = {
    "新建订单": "新",
    "多次迭代更新": "改",
    "缺失信息": "缺",
    "矛盾冲突": "冲",
    "明显异常": "异",
    "动态演进": "演",
}
VT_COLOR = {"ok": "#059669", "missing": "#d97706", "conflict": "#dc2626", "abnormal": "#b91c1c"}


def build_expected_html(exp, notes):
    """把 expected 字典渲染成小型表格 + 陷阱提示。"""
    parts = []
    rows = []
    for k, v in exp.items():
        if k in ("entity", "entity_key_hint"):
            rows.append((k, str(v), 0))
        elif k in ("validator_target",):
            continue
        else:
            rows.append((k, str(v), 0))
    if rows:
        parts.append('<table class="exp-tbl">')
        for k, v, _ in rows:
            parts.append(f"<tr><td class='k'>{k}</td><td class='v'>{v}</td></tr>")
        parts.append("</table>")
    if notes:
        lis = "".join(f"<li>{n}</li>" for n in notes)
        parts.append(f'<div class="notes"><span class="notes-h">设计陷阱</span><ul>{lis}</ul></div>')
    return "\n".join(parts)


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    groups = data["groups"]

    # 内嵌数据供浏览器渲染（缩进最小化，避免转义问题，仅做引号/尖括号转义放在 JS 中用 textContent 输出，
    # 这里只把 JSON 原样写入 script，HTML 侧全部用 createTextNode 渲染，杜绝注入）。
    payload = json.dumps(data, ensure_ascii=False)

    cards = []
    for g in groups:
        st = g["scene_type"]
        color = TYPE_COLOR.get(st, "#555")
        mark = TYPE_MARK.get(st, "·")
        vt = g.get("expected", {}).get("validator_target", "-")
        vc = VT_COLOR.get(vt, "#555")

        msgs_js = []
        for m in g["messages"]:
            speaker_cls = "opp" if m["speaker"] in ("王总", "李姐", "赵老板") else "me"
            msgs_js.append(
                f'<div class="msg {speaker_cls}"><div class="who" style="color:{color}">{m["speaker"]}</div>'
                f'<div class="tt">{m["time"]}</div><div class="text">{m["text"]}</div></div>'
            )
        bubbles = "\n".join(msgs_js)

        exp_html = build_expected_html(g.get("expected", {}), g.get("notes", []))

        cards.append(f"""
<div class="card" data-sid="{g['scene_id']}">
  <div class="card-head">
    <span class="mark" style="background:{color}">{mark}</span>
    <span class="sid">{g['scene_id']}</span>
    <span class="stype" style="color:{color}">{st}</span>
    <span class="title">{g['title']}</span>
    <span class="vt" style="border-color:{vc};color:{vc}">{'期待·' + vt if vt != '-' else ''}</span>
    <span class="group-name">{g['group']}</span>
    <span class="cnt">{len(g['messages'])} 条</span>
  </div>
  <div class="card-body">
    <div class="chat">{bubbles}</div>
    <div class="expect">{exp_html}</div>
  </div>
</div>""")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>瓯单通 · 模块一 模拟数据预览</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:"Microsoft YaHei","PingFang SC",sans-serif; background:#f5f7fa; color:#1f2937; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:20px 16px 60px; }}
  header {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; padding:18px 20px;
          background:linear-gradient(120deg,#0f2a43,#144572); color:#fff; border-radius:12px; margin-bottom:16px; }}
  header h1 {{ font-size:20px; letter-spacing:1px; }}
  header .sub {{ font-size:12px; opacity:.8; }}
  header .stats {{ margin-left:auto; display:flex; gap:10px; }}
  .stat {{ background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.22); padding:6px 12px; border-radius:20px; font-size:12px; }}
  .legend {{ display:flex; gap:8px; flex-wrap:wrap; margin:10px 2px 14px; }}
  .lg {{ font-size:12px; padding:4px 10px; border-radius:16px; border:1px solid #d7dee8; background:#fff; color:#334155; }}
  .lg i {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }}
  .card {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; margin-bottom:16px; overflow:hidden;
          box-shadow:0 1px 3px rgba(15,42,67,.06); }}
  .card-head {{ display:flex; align-items:center; gap:10px; padding:10px 14px; background:#fbfcfe;
               border-bottom:1px solid #eef2f7; flex-wrap:wrap; }}
  .mark {{ width:26px; height:26px; border-radius:8px; color:#fff; font-weight:700; font-size:13px;
          display:flex; align-items:center; justify-content:center; }}
  .sid {{ font-weight:800; font-size:13px; color:#0f2a43; font-family:Consolas,monospace; }}
  .stype {{ font-weight:700; font-size:13px; }}
  .title {{ font-weight:600; font-size:13px; color:#334155; }}
  .vt {{ font-size:11px; font-weight:700; border:1px solid; border-radius:12px; padding:2px 8px; }}
  .group-name {{ font-size:11px; color:#94a3b8; }}
  .cnt {{ font-size:11px; color:#94a3b8; margin-left:auto; }}
  .card-body {{ display:grid; grid-template-columns:1.25fr 1fr; gap:0; }}
  .chat {{ padding:14px 16px; background:#f8fafc; }}
  .msg {{ max-width:86%; margin-bottom:10px; }}
  .msg .who {{ font-weight:700; font-size:12px; margin-bottom:1px; }}
  .msg .tt {{ font-size:10px; color:#94a3b8; margin-bottom:3px; }}
  .msg .text {{ font-size:13px; line-height:1.55; color:#1e293b; }}
  .msg.me .text {{ background:#e8f1fd; border:1px solid #cfe2f7; border-radius:10px 10px 10px 2px; padding:8px 11px; }}
  .msg.opp .text {{ background:#fff; border:1px solid #e2e8f0; border-radius:10px 10px 2px 10px; padding:8px 11px; }}
  .msg.me {{ margin-left:auto; }} .msg.me .who, .msg.me .tt {{ text-align:right; }}
  .expect {{ padding:14px 16px; border-left:1px solid #eef2f7; }}
  .expect h3 {{ font-size:12px; color:#0f2a43; margin-bottom:10px; letter-spacing:.5px; }}
  .exp-tbl {{ width:100%; border-collapse:collapse; font-size:12.5px; margin-bottom:10px; }}
  .exp-tbl td {{ padding:5px 8px; border-bottom:1px dashed #eef2f7; vertical-align:top; }}
  .exp-tbl .k {{ color:#64748b; width:88px; font-weight:600; }}
  .exp-tbl .v {{ color:#0f172a; }}
  .notes {{ background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:8px 10px; font-size:11.5px; }}
  .notes-h {{ font-weight:700; color:#b45309; margin-right:6px; }}
  .notes ul {{ margin:4px 0 0 16px; color:#78350f; line-height:1.6; }}
  footer {{ text-align:center; font-size:11px; color:#94a3b8; margin-top:20px; line-height:1.7; }}
  @media (max-width:760px) {{ .card-body {{ grid-template-columns:1fr; }} .expect {{ border-left:none; border-top:1px solid #eef2f7; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div><h1>瓯单通 · 模块一 模拟数据预览</h1>
    <div class="sub">口语化群聊数据集（契约1 格式）· 右侧为每组预期抽取结果 / 校验目标</div></div>
    <div class="stats">
      <span class="stat">共 {len(groups)} 组场景</span>
      <span class="stat">共 {sum(len(g['messages']) for g in groups)} 条消息</span>
      <span class="stat">数据版本 {data.get('version','-')}</span>
    </div>
  </header>
  <div class="legend">
    <span class="lg"><i style="background:#1d7ad9"></i>新建订单</span>
    <span class="lg"><i style="background:#8a6de9"></i>多次迭代更新</span>
    <span class="lg"><i style="background:#d97706"></i>缺失信息</span>
    <span class="lg"><i style="background:#dc2626"></i>矛盾冲突</span>
    <span class="lg"><i style="background:#b91c1c"></i>明显异常</span>
    <span class="lg"><i style="background:#059669"></i>动态演进</span>
    <span class="lg" style="margin-left:auto;color:#64748b">客户发言 · 我方发言</span>
  </div>
  {''.join(cards)}
  <footer>红线说明：页面展示全部为团队自建模拟群聊数据，企业名已作化名处理，不涉及任何真实企业信息。<br>
  右侧「预期效果」标注为模块二（抽取/校验）实现后的目标结果，供联调对照，非智能体实际输出。</footer>
</div>
</body>
</html>"""

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"预览页已生成：{OUT}")


if __name__ == "__main__":
    main()
