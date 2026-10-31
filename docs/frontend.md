# 前端开发蓝图

本文件规定前端结构。目标栈为 Vue 3、TypeScript、Vite、Vue Router、Pinia、Element Plus、ECharts。当前 `web/` 已把原来的单页拆成路由和 Pinia，并保留 `/api/nexus/*`。前端只负责交互与展示，权限和分数仍以服务端为准。浏览器令牌仍放在 `localStorage`，刷新协议不在本次范围，见[导入差异](implementation-import.md)。

## 1. 页面与路由

| 页面/路由 | 主要用户 | 主要内容 | 所需 API |
| --- | --- | --- | --- |
| 登录 `/login` | 全部 | 账号登录、错误提示；仅当构建时配置了演示口令环境变量才显示预置账号 | 认证 |
| 工作台 `/` | 全部 | 当前身份、班级、待办、任务状态 | 当前用户、任务 |
| 讲义 `/materials`、`/materials/:id` | 全部 | 本班材料列表、搜索、正文、版本与引用定位 | 材料、检索 |
| 上传与版本 `/materials/new` | 教师 | 标题、班级、TXT/MD/文字型 PDF、索引状态 | 上传、版本、任务 |
| AI 应用 `/apps`、`/apps/:id/settings` | 教师 | 应用、提示词、知识范围、Skill/MCP 绑定、测试与启停 | 应用配置 |
| 会话 `/apps/:id/chat`、`/conversations/:id` | 全部 | 多轮消息、SSE 输出、引用和工具状态 | 会话、SSE |
| 知识缺口 `/gaps`、`/gaps/:id` | 教师 | 候选问题、热度、审核、回补与前后对照 | 缺口、材料 |
| 作业 `/assignments`、`/assignments/:id` | 全部 | 教师模板与发卷；学生本人实例、提交及结果 | 作业、提交、批改 |
| 批改复核 `/grading/:id` | 教师 | AI 初评、Rubric、证据、最终分和理由 | 批改、复核 |
| 周报 `/reports`、`/reports/:id` | 全部 | 事实统计、草稿、编辑、审核发布；学生只看已发布 | 周报 |
| 审计与任务 `/jobs`、`/audit` | 教师 | 异步任务状态、失败与重试、可见审计摘要 | 任务、审计 |

具体路由可在实现 PR 中调整，但页面能力和权限不得减少。教师导航与学生导航分别展示；直接输入受限 URL 时也必须由 API 拒绝。

当前已落地的地址：`/login`、`/`、`/materials`、`/materials/new`、`/materials/:id`、`/conversations`、`/conversations/:id`、`/apps`、`/gaps`、`/assignments`、`/reports`、`/jobs`、`/audit`。应用编辑、批改复核和周报详情仍在对应页面内完成，没有再拆成单独的设置页或 `/grading/:id`。学生打开 `/materials/new` 可以提交上传，结果展示服务端的 403。

## 2. 目录与模块职责

- `src/router`：路由表和登录守卫。守卫只根据本地是否持有令牌决定去留，不代替服务端鉴权。
- `src/api.ts`：统一请求、Bearer 令牌和 HTTP 错误文案。组件不拼接主机名。尚未实现刷新接口。
- `src/stores`：`session` 保存服务端返回的身份，`catalog` 保存当前班级的列表，`chat` 保存会话。身份里的 `role` 和 `class_id` 只来自登录或 `/me`，页面不提交班级编号。
- `src/views`：登录、工作台、讲义、会话、应用、缺口、作业、周报、任务和审计。
- `src/components`：登录后的框架、教师页的服务端拒绝提示、成绩分布图。
- 请求和响应仍沿用现有 JSON，没有另建一套与后端冲突的字段。

## 3. 交互与状态

- 目标仍是把访问令牌只放在内存，并用 HttpOnly 刷新凭据续期。当前基线没有这个接口，所以登录后仍把服务端签发的 Bearer 令牌放在 `localStorage` 的 `nexus-token`。刷新时先请求 `/me` 恢复身份，再进入原路由。退出会通知服务端撤销并清除本地令牌。这项差异不能靠前端单独发明刷新接口来关闭。
- 每个异步操作展示 `queued/running/succeeded/failed`，失败提供任务编号和可阅读原因；重试前确认是否会生成重复记录。
- SSE 事件分别处理消息片段、引用、工具开始/完成、结束与错误。离开页面时中断连接；断线不能把上一会话事件插入新会话。
- 材料正文在页面内可读，引用可定位到片段；下载作为额外入口。Markdown 和模型输出必须安全渲染，不能执行嵌入脚本。
- 所有提交按钮防重复，表单给出字段级错误，危险操作（撤回、发布、改最终分）显示影响范围并要求二次确认。
- 搜索、列表和图表都以服务端已授权结果为准；不同班级切换时清除旧缓存，避免瞬间展示上一班数据。

## 4. 前端验收

Playwright 目标仍包括教师与学生主路径、未登录跳转、跨班或他人资源拒绝、SSE 错误、索引失败、发卷失败、周报草稿不可见和移动端基本可用性。不得只用静态假数据通过端到端测试。

本次已提交的用例在 `web/e2e/`：未登录进入登录页、登录后回到原地址、教师/学生导航与退出、错误口令、刷新后留在讲义页、学生打开任务页收到「权限不足」、学生上传收到「权限不足」、A 班上传后的正文可见且 B 班列表没有该标题。SSE、索引失败、发卷失败、周报草稿和移动端尚未覆盖。

在 `web/` 运行。地址和口令只从环境读取，仓库里不放 `.env`。本机隔离栈可以直接测；非本机地址必须再确认这是隔离环境，避免打到公网或生产。

```text
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
# 本机示例。口令使用该环境自己的虚构种子，不写入仓库。
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 E2E_TEACHER_PASSWORD=... E2E_STUDENT_PASSWORD=... pnpm run e2e
```

PowerShell 用 `$env:PLAYWRIGHT_BASE_URL`、`$env:E2E_TEACHER_PASSWORD` 和 `$env:E2E_STUDENT_PASSWORD`。可选覆盖用户名：`E2E_TEACHER_USER`（默认 `teacher_a`）、`E2E_STUDENT_USER`（默认 `student_a1`）、`E2E_STUDENT_B_USER`（默认 `student_b1`）。非本机隔离地址还要设置 `E2E_CONFIRM_ISOLATED=yes`。未设置 `PLAYWRIGHT_BASE_URL` 时测试会直接失败，不会选择默认主机。

正文用例要等索引完成，因此隔离环境需要可用的 Worker。索引失败时该用例失败，不能改记为通过。未实际运行的项目保持 NOT RUN。
