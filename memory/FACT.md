# 持久事实
## 项目文件规则
- 用户要求：不要保存任何文件到 C 盘；项目相关文件应保存在 `F:\kelaode\quanzidong` 或用户指定的 F 盘路径。
- 用户要求：开始/继续项目前先核对项目情况，尤其是 `git status`。
- 用户要求：每完成一个阶段就提交并推送到仓库 `https://github.com/zz9744813-lab/wudixeixaioshuo.git`。
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