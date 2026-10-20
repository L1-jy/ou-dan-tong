# 瓯单通 · WorkBuddy 网页智能体（可体验）

把订单/任务协同逻辑实现为本地可运行 Python 原型：逻辑、提示词、校验规则、数据模型与方案完全一致，
用本地 JSON 存储替代外部数据表，用 DeepSeek（OpenAI 兼容）API 替代平台 LLM 节点。
本目录自带零依赖网页界面，可直接作为「可体验智能体」交付与演示。

## 目录结构
```
ou_dan_tong/
  config.py         模型/运行配置（Key 走环境变量）
  llm.py            极简 OpenAI 兼容调用（零依赖）
  prompts.py        提示词骨架 + 卡片/查询/简报文案
  store.py          本地 JSON 存储（订单/任务台账）
  validator.py      确定性校验 + 变更比对
  extractor.py      LLM 结构化抽取（支持 mock）
  agent.py          编排：parse_chat / query / briefing + handle_message 意图路由
  sim_chats.py      模拟群聊 + Mock 抽取
  main.py           CLI 入口
  web_app.py        零依赖网页服务（仅用标准库）
  static/index.html 聊天界面（含订单/任务台账面板）
  test_pipeline.py  全链路自测
  runtime/          运行时数据（orders.json / tasks.json，自动生成）
```

## 一、网页智能体（推荐交付形态）
```bash
cd ou_dan_tong
python web_app.py
# 浏览器打开 http://127.0.0.1:8000
```
- 队友/评委直接粘贴群聊、问「XX 那单到哪了」、说「出今日简报」即可体验。
- 未配置 Key 自动进入「模拟模式」（用预置数据演示完整流程，免费）。
- 配置 `DEEPSEEK_API_KEY` 后自动切换「真实模式」（真实抽取任意群聊）。

## 二、命令行快速验证（无需 Key）
```bash
python main.py reset      # 清空台账
python main.py demo       # 跑场景演示（Mock 抽取）
python test_pipeline.py   # 全链路自测
```

## 三、接入真实模型（DeepSeek）
```bash
export DEEPSEEK_API_KEY="sk-xxxx"
python web_app.py         # 此时为真实模式，可抽取任意群聊
```
也可对接任意 OpenAI 兼容端点（智谱/通义/MiniMax）：设置
`OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL`，并把调用改为 `LLM("openai")`。

## 设计要点
- 防幻觉：所有回复带 `source_excerpt` 原文依据；简报数字全部来自台账查询，LLM 不编数。
- 变更捕获：同 客户+产品 在途单 → UPDATE 并追加 `changes` 履历，状态只进不退。
- 缺失跳过：缺客户/产品的 order 行丢弃并提示人工确认。

## 下一步
1. 让队友 A 用 `sim_chats.py` 模板扩充 5-8 组带陷阱的演示数据（模块一·模拟数据构建）。
2. 真实跑通后用 `runtime/orders.json` 截图作为「真台账」证据。
3. 演示录屏 + 数据 JSON 备份，防现场翻车。
