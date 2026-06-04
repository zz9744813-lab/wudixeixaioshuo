# 持久事实

## 项目文件规则
- 用户要求：不要保存任何文件到 C 盘；项目相关文件应保存在 `F:\kelaode\quanzidong` 或用户指定的 F 盘路径。
- 用户要求：开始/继续项目前先核对项目情况，尤其是 `git status`。
- 用户要求：每完成一个阶段就提交并推送到仓库 `https://github.com/zz9744813-lab/wudixeixaioshuo.git` (origin) 或 `https://github.com/zz9744813-lab/xiaoshuozuizhongban.git` (xiaoshuozuizhongban)，按需选 remote。
- 工具使用经验：Read 工具读取普通文本/代码文件时不要传 `pages: ""`，空字符串会报 `Invalid pages parameter`；只有读取 PDF 且需要页码时才传合法页码。

## 项目前端关键事实
- 路由表（App.js）：所有页面必须在 `<Route>` 里注册，否则点击 `<Link>` 会进入空 main 区（不是 crash，但视觉上像崩溃）。**新增页面后必须确认路由已注册**。
- bible 路由前缀：后端 `bible.py` 用 `prefix="/api"` 注册，**不是** `/api/bible`。正确路径是 `/api/projects/{id}/bible` 和 `/api/projects/{id}/bible/characters` 等。前端 `BibleEditor.jsx` 原本写成 `/bible/projects/...` 是错的（404）。
- BibleEditor 缺 `useToast()` 初始化：`useToast` 被 import 但从未调用，错误路径下 catch 块调用 `toast.error` 会抛 ReferenceError。这是"详情页面就会崩溃"的真正根因——用户点"编辑世界观"按钮后跳到 BibleEditor，错误的 API 路径返回 404，catch 块里 `toast` 未初始化直接 crash。
- 5xx 错误的 axios 显示：FastAPI 的 `ResponseValidationError`（Pydantic 响应模型失败）会被 Starlette 兜底为纯文本 500，axios 无法解析 JSON 就显示"Network Error"。修复：middleware 加 `@app.exception_handler(ResponseValidationError)` 返回标准 JSON 错误结构。
- **JSX 子表达式是 eager 求值**（不是 lazy）：`{x && <Foo />}` 里的 JSX（包括 `React.createElement` 调用）会在父组件 render 时立即求值。所以 `<AsyncState isEmpty={!x}><div>{x.status}...</div></AsyncState>` 在 `x = null` 时仍然会抛 `Cannot read properties of null (reading 'status')`，因为表达式在父 render 时已经被求值了，根本到不了 AsyncState 的 if 分支。**JSX 内部对可能为 null 的对象做属性访问必须用可选链 `?.` 或显式 null check**——`AsyncState` 的 `isEmpty` 保护不了子表达式，只保护子元素的渲染。

## 后端关键事实
- **FastAPI 路由顺序很关键**：FastAPI 按定义顺序匹配。**固定路径必须在参数化路由 `/{xxx}` 之前注册**，否则 `GET /dimensions`、`GET /best-practices` 这类请求会被 `GET /{evolution_id}` 吞掉，参数 'dimensions' 无法解析为 int → 返回 422，错误信息 `field: path.xxx_id`。原 evolution.py 就是这个 bug，导致 Darwin 中心维度下拉框一直是空的。
- **axios 第二个参数是 body，第三个才是 config**：很多代码误把 fetch-style `{ method, headers, body }` 当成 body 传给 `api.post(url, ...)`，导致后端收到 `{"method":"POST","headers":{...},"body":"..."}` 这种垃圾 body → 422。修正：直接传业务对象，必要时第三个参数传 config。
- **重复的 `await api.post` 会导致双发 + 二次 404**：EvolutionCenter / FeedbackCenter / PromptTemplates 三处都有，体感像"页面跳来跳去"或"toast 一直闪"。

## P4 运维状态
- 两个 git remote：origin (wudixeixaioshuo) 和 xiaoshuozuizhongban，均需推送。
- 已修复所有 SQLAlchemy metadata 保留字冲突：OutlineNode (node_meta), ChapterVersion/MemoryItem/SystemLog (extra_meta)。
- Docker Compose 已修复：移除 worker 服务、修复 healthcheck、修复 VITE_API_URL、添加 start_period。
- events router 已修正：从 `prefix="/api"` 改为通过 api_router 的 prefix 统一处理。
- Docker 当前环境不可用，需用户手动验证 docker-compose up。
- 待完成：日志配置、监控端点、Docker 本地验证。

## P7 调度中心 — Agent 模型路由矩阵 (2026-06-04)
按 NF2 plan 实施 4 个 phase + Phase 5 前端 UI, 3 个 commit:
  - 0856e6a P7 Phase 1-4 后端 (model_routing_events + 7 endpoints + manual 锁 + circuit-breaker)
  - fa8d805 P7 Phase 5 前端 (AgentMatrix + AgentDetailModal + AutoAssignModal)
  - 8c40304 pre-existing ESLint 清理 (24 文件 no-unused-vars)

**两表模型** (扩展现有, 不重建):
  - `model_roles` (全局/project_id IS NULL): assignment_mode (auto/manual),
    allowed_provider_ids, preferred_quality, max_cost_per_million,
    min_context_tokens, require_json, require_streaming, fallback_enabled,
    updated_by
  - `model_routing_events`: id/role/task_id/project_id/assignment_mode/
    selected_provider_id/candidates_json/decision_reason/
    fallback_used/fallback_chain_json

**manual 锁强制逻辑** (`_get_model_role_lock` 在 `LLMRouter.generate` 起手):
  - manual + 锁定 provider 有 route → routes 过滤到只剩该 provider
  - manual + 锁定 provider 无 route + fallback=0 → 抛 LLMRouterAllProvidersFailed
  - manual + 锁定 provider 无 route + fallback=1 → 走原 routes fallback
  - auto → 保持 priority/weight 选路

**评分公式** (priority 40 + health 30 + latency 15 + role_preference 10 - mock_penalty 50):
  - priority 越低越好: ≤10=40, ≤50=30, ≤100=20, >100=10
  - health 用 success_rate * 30, 连续失败 ≥3 扣 10
  - mock/stub 强制 -50 惩罚

**踩坑 (长期保留)**:
  - `_get_routes_for_role` 后**不能**在 generate() 开头用 `LLMRouter(self.db)._is_circuit_open(r)` 这种 self 调用
    来过滤, 会触发 self 未初始化的栈; 用 `self._is_circuit_open` 即可
  - `LLMRouteResult` 字段名 `routing_event_id` (不是 `routing_id`); result 内已 attach,
    调用方直接用
  - `record_routing_decision` 接受 `assignment_mode` 字符串 (不锁 model_role 表),
    是事件表的事后记录, 不影响主流程
  - `_record_routing_event` 抛错不能影响主调用, try/except 包裹 + logger.warning
  - Phase 1 seed 二次跑会 UNIQUE 冲突 (`agent_model_bindings`); 修法:
    `DELETE FROM agent_model_bindings WHERE agent_role_id NOT IN (SELECT id FROM agent_roles)`
  - TaskDetail.jsx 等文件 line offset 修后, 改前先 `Read(file_path, offset=X)` 拿真实行号

**e2e 测试模式** (verify_phase1/3/4.py):
  - mock `_call_provider` 用 `unittest.mock.patch.object(router, "_call_provider", side_effect=fake_call)`
  - fake_call 接受 `route, **kwargs`, 返回 LLMRouteResult
  - 每次 seed 一个独立 role (Phase 4 用 critic, Phase 1/3 用 planner), 不污染
  - `reset_X_state(db)` helper 在每个 T 前清空路由统计

**前端 ESLint 清理** (commit 8c40304):
  - CI=true build 把 warnings 当 errors, 必须 0 warning 才能过
  - `// eslint-disable-next-line no-unused-vars` 比 `_` 前缀更通用 (react-app preset 不识别 _)
  - 删 unused import 时**先 grep 确认 JSX 没用**, 第一次太激进把 Techniques 的 `api` 删了导致 is not defined
  - 一次性清理 24 个文件 70+ 处, 总 diff +83/-56 行
>>>>>>> d620c03 (docs(FACT.md): 记录 P7 调度中心 4 phase + Phase 5 前端的核心经验)
