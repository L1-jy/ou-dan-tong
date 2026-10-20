# 瓯单通 · WorkBuddy 网页智能体（可体验）

把订单/任务协同逻辑实现为本地可运行 Python 原型：逻辑、提示词、校验规则、数据模型与方案完全一致，
用本地 JSON 存储替代外部数据表，用 DeepSeek（OpenAI 兼容）API 替代平台 LLM 节点。
本目录自带零依赖网页界面，可直接作为「可体验智能体」交付与演示。

## 目录结构
```
ou_dan_tong/
  config.py         模型/运行配置（Key 走环境变量）
  contracts.py      契约单一真相源（契约1/2/3/4：Message/ChangeSegment/订单·任务/ValidationResult）
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

## 模块二 · 变更识别与记录（核心设计 / 工作流程 / 实现方式）

> 归属：队友A。对应 `contracts.py` + `validator.py` + `prompts.py`。评委点名的「缺失/冲突/异常」三难
> 点即落在此模块，输出契约 4 的 `ValidationResult {status, message, patch}`。

**核心设计**
- 单一真相源 `contracts.py`：冻结契约 1（聊天输入）、契约 2（变更片段）、契约 3（订单/任务记录）、
  契约 4（校验结果）。全员 `import`，改字段须走 PR 且向后兼容。
  （注：契约模块本名 `types.py`，因与 Python 标准库 `types` 同名冲突、无法被本地覆盖，重命名为
  `contracts.py`，功能不变，已在《接口与模块对接约定》备案。）
- 判定优先级：**异常(abnormal) → 冲突(conflict) → 缺失(missing) → 正常(ok)**，四级短路。

**工作流程**（`agent.parse_chat` 编排）
1. `extractor` 把群聊抽成订单/任务行 → `validator.validate_extraction` 做类型规整。
2. 对每条订单调用 `validator.classify_order(o, existing, order_date)` 做四级判定：
   - 异常：数量负数/交期格式错/交期早于下单日 → **直接拦截，不写入**，卡片 red 提示。
   - 冲突：与在途单同字段数值矛盾、且来单**无变更动词**（改/变更为…）→ **不覆盖**，标记 `flags.conflict` 待人工确认。
   - 缺失：新建订单缺数量/交期 → **登记占位单**（状态「待补充」）+ 追问话术，台账可见。
   - 正常：带变更动词的更新 / 无矛盾的新建 → `apply_change` 落库并留痕。
3. 异常/冲突/缺失均以卡片话术 + 台账 `flags` 双重呈现，演示时评委一眼可见。

**实现方式**
- `validator.classify_order` 纯函数、零依赖、可单测，不依赖 LLM；`change_verb` 由
  `source_excerpt` 是否含「改/变更为/调成…」判定，以此区分「正常更新」与「矛盾断言」。
- 自测：`python test_validator.py` —— 单元级断言五类陷阱判定正确，并端到端演示一段含陷阱群聊；
  另需 `python test_pipeline.py` 保证全链路无回归。

## 下一步
1. 模块三（状态维护·队友D）/ 模块四（查询应答·队友C）基于 `contracts.py` 契约并行接入。
2. 真实跑通后用 `runtime/orders.json` 截图作为「真台账」证据。
3. 演示录屏 + 数据 JSON 备份，防现场翻车。
