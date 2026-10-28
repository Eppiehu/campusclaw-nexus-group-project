# REST 与 SSE 接口清单（规划版）

本清单约定前后端分工和权限。URL/字段属于拟定契约；实现前通过 OpenSpec 和 PR 确认，不能把本文当作已有接口。API 前缀为 `/api`，除登录、刷新和健康检查外均要求认证。资源 ID 使用不易猜测的标识，但**不可猜测不代替授权**。

## 1. 通用约定

- 请求和响应使用 JSON；文件上传使用 `multipart/form-data`；下载返回原文件流；SSE 返回 `text/event-stream`。
- 分页列表统一包含项目、游标/页码与总数或下一页标记；排序字段白名单化。
- 错误统一返回 `code`、`message`、`request_id`；400 参数错误、401 未认证、403 无权限、404 不存在、409 状态冲突、413 文件超限、415 格式不支持、429 限流、503 依赖不可用。
- 创建/发布/重试类请求使用幂等键，重复提交返回同一业务结果或明确的 409；后台任务返回任务 ID 和可轮询状态。
- JWT 的 `role`/`class_id` 信息只用于客户端展示；服务端还要查询当前成员关系与资源归属。学生不能通过提交班级参数扩大范围。

## 2. 认证与任务

| 方法与路径 | 用途 | 权限与关键行为 |
| --- | --- | --- |
| `GET /health` | 进程存活 | 公开；200 不代表依赖全部就绪 |
| `GET /ready` | 数据库、Redis、迁移就绪 | 部署探针；不泄露内部连接细节 |
| `POST /api/auth/login` | 凭据登录，返回访问令牌与公开身份 | 公开；失败 401；刷新凭据放 HttpOnly Cookie |
| `POST /api/auth/refresh` | 换短期访问令牌 | 受刷新凭据和同源/CSRF 校验保护 |
| `POST /api/auth/logout` | 撤销令牌与刷新凭据 | 已登录；重复退出可幂等 |
| `GET /api/auth/me` | 当前身份、角色与可用班级 | 已登录；从服务端成员关系生成 |
| `GET /api/jobs/:id` | 任务状态、进度、脱敏错误 | 仅任务创建者或本班授权教师 |
| `POST /api/jobs/:id/retry` | 失败任务重试 | 仅授权教师；幂等且受重试上限约束 |

## 3. 材料、知识库与 Agent

| 方法与路径 | 用途 | 权限与关键行为 |
| --- | --- | --- |
| `GET /api/materials` | 本班材料列表与查询 | 按服务端班级过滤 |
| `POST /api/materials` | 新建材料并上传文件 | 教师；校验 TXT/MD/文字型 PDF、大小与内容 |
| `GET /api/materials/:id` | 元数据与生效版本 | 本班授权用户 |
| `GET /api/materials/:id/content` | 页面内查看正文 | 本班授权用户；安全渲染 |
| `GET /api/materials/:id/download` | 下载原文件 | 本班授权用户；再次检查版本和撤回状态 |
| `POST /api/materials/:id/versions` | 上传新版本并索引 | 本班教师；旧版保持生效直到成功切换 |
| `GET /api/materials/:id/versions` | 查看版本和索引状态 | 本班授权用户；学生只看允许版本 |
| `POST /api/materials/:id/withdraw` | 撤回材料 | 本班教师；保留审计与历史引用 |
| `POST /api/search` | 班级内混合检索 | 仅授权活动版本；结果含版本、片段、出处 |
| `GET /api/apps` | 可用 AI 应用 | 按班级与发布状态过滤 |
| `POST /api/apps`、`PATCH /api/apps/:id` | 新建/配置应用 | 本班教师；提示词、知识范围、Skill/MCP 白名单版本化 |
| `POST /api/apps/:id/test` | 测试应用配置 | 本班教师；标记测试结果与真实模型/替身 |
| `GET /api/conversations`、`POST /api/conversations` | 会话列表/创建 | 用户本人；绑定班级与应用配置版本 |
| `GET /api/conversations/:id` | 消息、工具结果与引用 | 会话所有者或授权教师 |
| `POST /api/conversations/:id/messages/stream` | 发送消息并流式接收 | 使用 Bearer 的 fetch；事件含消息片段、引用、工具状态、结束/错误 |
| `GET /api/citations/:id` | 引用片段详情 | 会话与材料双重鉴权，指向不可变版本 |

Skill/MCP 的拟定接口如下。具体字段与可执行格式在单独实现变更中锁定，未经审核的上传内容不能直接运行。

| 方法与路径 | 用途 | 权限与关键行为 |
| --- | --- | --- |
| `GET /api/skills`、`POST /api/skills` | 列表/上传技能定义 | 本班教师；限制格式、大小和来源，默认禁用 |
| `POST /api/skills/:id/validate` | 静态校验与隔离测试 | 本班教师；返回检查报告，不直接启用 |
| `POST /api/skills/:id/enable`、`POST /api/skills/:id/disable` | 启停已审核技能 | 本班教师；配置版本化、保留审计 |
| `GET /api/mcp/tools` | 可用工具目录 | 按当前身份和应用绑定过滤 |
| `POST /api/mcp/connections/test` | 测试外部工具连接 | 经授权的教师/管理员；只测试允许的服务器和工具，凭据不回显 |
| `PATCH /api/apps/:id/bindings` | 绑定知识库、Skill 和 MCP 工具 | 本班教师；保存版本与白名单 |

## 4. 知识缺口、作业与周报

| 方法与路径 | 用途 | 权限与关键行为 |
| --- | --- | --- |
| `GET /api/gaps`、`GET /api/gaps/:id` | 本班候选缺口与证据 | 教师；不跨班归并 |
| `POST /api/gaps/:id/review` | 确认或驳回 | 本班教师；记录理由和时间 |
| `POST /api/gaps/:id/replenish` | 补充材料并建立索引 | 本班教师；任务完成后才标已补入 |
| `GET /api/gaps/:id/comparison` | 回补前后检索对照 | 本班教师；固定测试问题与材料版本 |
| `GET /api/assignments` | 教师模板/学生本人作业列表 | 按角色、班级、所有者过滤 |
| `POST /api/assignment-templates` | 创建模板与 Rubric | 本班教师；参数范围和评分规则校验 |
| `POST /api/assignment-templates/:id/publish` | 异步发卷 | 本班教师；每名学生实例独立状态 |
| `GET /api/assignments/:id` | 题目实例 | 学生本人或任教教师；学生不得读取标准答案 |
| `POST /api/assignments/:id/submissions` | 提交本人作业 | 本人且在允许时间；幂等防重复 |
| `GET /api/grades/:id` | AI 初评与允许公开的结果 | 本人或本班教师；未公开最终分不对学生展示 |
| `POST /api/grades/:id/review` | 教师复核/最终分 | 本班教师；保留原分、理由与版本 |
| `GET /api/reports`、`GET /api/reports/:id` | 周报列表/详情 | 教师看草稿；学生只看已发布本班报告 |
| `POST /api/reports/generate` | 聚合事实并生成草稿 | 本班教师；返回任务 ID |
| `POST /api/reports/:id/publish` | 教师发布 | 本班教师；核对事实版本与审核记录 |

## 5. SSE 事件与审计

流事件至少包括 `message.delta`、`citation`、`tool.started`、`tool.finished`、`message.completed` 和 `error`，各事件携带会话 ID 与事件序号；断线重试不得重复执行有副作用工具。模型调用审计记录应用/模板版本、检索片段 ID、工具调用 ID、耗时和结果状态，不记录密钥或完整敏感输入。

