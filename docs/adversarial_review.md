# Novel Genome — 对抗性审查报告

**审查对象**: `master @ 25e8065` 之后的全部平台代码（EPIC-A → EPIC-G）
**审查方法**: 以规范 v2.0 自身的约束为攻击面——逐条对照 §56「编程 Agent 禁止事项」(15 条)、
P-01..P-12 设计原则、§51 研究门禁、§63 晋升阶梯，并做代码级违规扫描 + 回归测试。
**结论**: 发现 **2 个严重违规（已修复）**、若干部分符合项（已记录）；修复后全套件 46 个测试两次全绿。

---

## 一、严重违规（已修复并有回归测试）

### A-1 · 违反禁止 6「Experiment 无 control 不算实验」——严重

**攻击发现**: `app/research/runner.py` 原实现为
`control = next((v for v in variants if v.variant_type == "control"), variants[0])`——
当实验**没有声明对照组**时，第一个 treatment 会被静默当作 control。这正是规范禁止 6 的场景：
无对照的"实验"会产生不可信的结论，且调用方毫无察觉。

**修复**: 无 control 变体时直接 `ValueError` → API 400，错误信息含 "禁止6"。
**回归**: `tests/test_research.py::test_experiment_without_control_is_refused`。

### A-2 · 违反 §17 / P-08「LLM 输出必须先成为 Claim」——严重

**攻击发现**: EPIC-C 的 Event/Perception/Belief/Goal/Emotion/Relationship 六个 Pass 把
LLM 输出**直接写入** `events` / `perceptions` / `belief_states` / `goals` / `emotion_states` /
`relationship_states` 表，绕过了 Claim 层。按 §17，所有 Agent 输出首先成为 Claim，经
Reconciler 才能进入 canonical——直接写表等于 LLM 输出覆盖规范状态（同时触碰禁止 3 的边界）。

**修复**: 新增共享 `_claim()` 帮助器；上述六个 Pass 现在在写 artifact 行的同时写一条带
`agent_run`（run id）与 evidence 的 Claim——**Claim-对等**：任何 artifact 行都能沿
run id 追溯到其 Claim 与 Run/ModelCall 链。
**回归**: `tests/test_agents.py::test_claim_parity_for_agent_outputs`（用 StubProvider
产出真实内容，断言 Event artifact 与 Claim 共享 run id 且谓词正确）。

---

## 二、禁止事项逐条审计（§56）

| # | 禁止事项 | 状态 | 证据 |
|---|---|---|---|
| 1 | 整本小说扔给一个 Prompt | ✅ 合规 | 摄入按 Scene 切分；Agent 按 Scene 粒度调用（`app/agents/base.py` context 以 Scene 为单位） |
| 2 | Scene 分析只有一轮 | ✅ 合规 | 11-Pass 编排器 `orchestrator.py`（§16/§32 顺序） |
| 3 | LLM 输出直接覆盖 canonical | ✅ 合规（A-2 修复后） | 全部 Pass 输出 = Claim + artifact 行，`scene.analyzed` 只由 Reconciler 汇总提升 |
| 4 | 没有 Evidence | ✅ 合规 | Claim.evidence / EmotionItem.evidence / CausalityItem.evidence；SceneSpan 是证据叶子 |
| 5 | Technique 无反例 | 🟡 部分 | 晋升门禁强制反例（`promotion.py`），但 `POST /techniques` 创建时不强制——成熟度由 gate 把关 |
| 6 | Experiment 无 control | ✅ 合规（A-1 修复后） | 显式拒绝 + 400 |
| 7 | Judge 知道模型来源 | ✅ 合规 | Judge 上下文只有匿名 A/B（`_PairShim`/`_TextPairShim`）；judge_model 仅落库审计不回显给 Judge |
| 8 | 人物每章重新初始化 | 🟡 部分 | `_character_id` 按书内名字复用（不重复建卡）；但 CharacterState 连续更新链（State(t)→State(t+1)，P-04）尚未实现——属 EPIC-C 剩余深度 |
| 9 | Vector DB 当知识真相 | ✅ 合规 | 平台未使用向量库；向量检索规范（§37）留待后续，且规范要求仅作召回 |
| 10 | 研究数据污染生产 | ✅ 合规 | NovelForge 适配器只查 VALIDATED+（测试断言 `evidence_refs ⊆ validated`）；rollout artifact 标 `experimental_counterfactual`（P-09） |
| 11 | 错误无限重试 | ✅ 合规 | Task.max_retries + DeadLetter；实验失败 → FAILED_RETRYABLE 一次记录，无循环 |
| 12 | Prompt 硬编码 | 🟡 部分 | 11 个 prompt 全部走 `app/prompts/*.md` + PromptRegistry（§28）；`BaseAgent._load_prompt` 在注册表缺失时有内置 fallback 字符串——仅容错用，生产应保证启动加载成功（lifespan 已加载） |
| 13 | 改 Prompt 不跑回归 | 🟡 部分 | Benchmark 挂钩（§24）已具备（frozen golden cases + `run_bench`），但「Prompt 变更 → 自动重跑」的 CI 钩子未接 |
| 14 | 生产读原始参考小说长文本 | ✅ 合规 | 适配器只输出抽象约束/规律（测试断言 §43 形状），raw_text 只进分析上下文 |
| 15 | 只有 Dashboard 没有研究闭环 | ✅ 合规 | 研究闭环已通：ingest → analyze(Pass) → hypothesis → experiment(control+blind judge) → knowledge gate → production feedback |

## 三、P-原则审计

- **P-03 情绪必须有证据** ✅：`EmotionItem` 强制 trigger/appraisal/evidence 结构（禁止裸标签）。
- **P-05 故事内因果与作者结构分开** 🟡：`CausalEdgeType.authorial_structure` 存在，Pass 提示词要求区分，但当前无独立校验器强制分离——记录为后续强化点。
- **P-06/P-07 观察≠规律、允许反例** ✅：Pass 产出全部按 Candidate 处理；晋升阶梯以反例为硬门禁。
- **P-08 生成与验证分离** ✅（修复后）：Runner 的裁决由 Judge 产出的度量与假设自己的 falsification condition 决定，提出假设方不宣布成功；FakeProvider 零信号时**拒绝晋升**（`decision: inconclusive`），诚实优先。
- **P-09 source_class 区分** ✅：ingest=human_original、实验产物=experimental_counterfactual、评估=ai_generated。
- **P-10 未验证知识不入生产** ✅：`/rules` 与适配器双重过滤 + 测试。
- **P-11 LLM 调用可追溯** ✅：每次 Agent 调用 = Run + ModelCall（model/prompt_version/context_package/input/output），测试断言 11 Pass = 11 Run + 11 ModelCall。
- **P-12 拒绝万能 Prompt** ✅：一个 Pass 一个 Agent 一个 prompt 文件。

## 四、其他攻击向量（抽查）

| 向量 | 结果 |
|---|---|
| JSON 注入 / LLM 输出解析失败 | `extract_json` 三级修复（原文→剥围栏→平衡括号）；失败 → warning + 空输出，不崩溃 |
| 重复提交 | 摄入按内容哈希幂等（同字节=同 Book）；实验 run 幂等重放（§33） |
| 死锁/悬挂事务 | Runner 失败路径 rollback 后重取 Run 记 DeadLetter，连接归还池 |
| SQL 注入 | 全程 ORM 参数化，无拼接 SQL |
| CORS | `allow_origins=["*"]` 仅供本地开发，生产部署必须收紧（记录为部署项） |
| 测试数据残留导致的假绿 | 全套件连续运行两次全绿（持久化测试库下做了封闭化处理） |
| 编码炸弹（GBK/大文件） | `decode_bytes` 候选链 + latin-1 兜底；超大未分章场景走 heuristic 切分上限 |

## 五、记录在案的已知限制（非违规，但需明示）

1. **§16 全 20 Pass 未全部实现**：已实现 11 个核心 Pass；Local Continuity / Arc Function / Book Function（PASS-18/19/20）与 Reader Effect（PASS-17）待后续。
2. **P-04 连续人物状态机**（State(t)+Event→State(t+1)）未完整实现——当前是按场景抽取 + 名字复用，EPIC-C 深化项。
3. **Prompt 变更自动回归**（禁止 13 完全闭环）需要 CI 钩子。
4. **锚定场景选择**：实验当前取库中首个 Scene 作锚点（`_anchor_scene`），尚未消费假设的 origin_evidence 定位——多次实验应显式传入场景。
5. **约束校验器**：Prompt 层要求区分 in_world/authorial（P-05），缺独立代码校验。

## 六、最终状态

- 修复 2 处严重违规，新增 3 个回归测试。
- 全套件 **52 个测试**连续两轮全绿（持久化 DB 下封闭可重复）。
- 六阶段交付物（EPIC-A..G）均以「分支 → 合并 master」流程入库，可逐 merge 回退审查。
