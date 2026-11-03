# 教师可配置 MCP 连接

本变更对应 Issue #9，只支持 Streamable HTTP。五个内置 stdio 工具保持原有行为。

## 运维登记

在私有环境配置 `NEXUS_MCP_SERVERS` JSON，例如：

```json
{"course-library":{"url":"https://mcp.example.edu/mcp","classes":["A"],"tools":["lookup"],"credential_ref":"NEXUS_MCP_SECRET_LIBRARY_A"}}
```

域名是示例，必须替换为课程批准的服务。`credential_ref` 指向环境变量，仅接受 `NEXUS_MCP_SECRET_*` 名称；真实凭据不放 JSON、数据库、前端或仓库。每班使用独立凭据与授权，外部服务必须校验班级身份并隔离其资源。无凭据服务可省略引用。配置修改或凭据轮换后需重新测试。

默认 HTTPS 公网地址；教师只能选择别名，不能输入 URL 或命令。拒绝 URL 内凭据、查询串、片段、重定向及解析到私网/元数据地址的端点。部署者负责选择可信域名与固定 DNS；这不等于通用网络沙箱。仅显式隔离测试可设置 `NEXUS_MCP_ALLOW_LOOPBACK=1`，允许回环 HTTP，生产保持关闭。

## 教师使用

在“应用与技能”的 MCP 连接区登记、测试，查看工具名和输入模式。只有运维白名单允许且模式有效的工具会出现；在应用编辑页勾选工具，失效的旧绑定可取消勾选移除。停用后立即拒绝调用，再启用需重新测试。失败状态可读，不显示远端堆栈或凭据。

## 实际接口

均在 `/api/nexus` 下，保留当前项目路径：

| 方法和路径 | 行为 |
| --- | --- |
| GET `/mcp/servers` | 本班教师可用服务器别名 |
| GET/POST `/mcp/connections` | 教师列表/登记 `{name,server_key}` |
| POST `/mcp/connections/:id/test` | 工具发现；成功 200，失败 502 并失效旧快照 |
| PATCH `/mcp/connections/:id` | 教师启停 `{enabled}` |
| GET `/mcp/tools` | 本班教师已测试工具目录及模式 |
| POST `/agents`、PATCH `/agents/:id` | 复用 `tools` 字段绑定 `ext_<连接ID>__<工具名>` |

未登录 401、学生管理 403、跨班连接防枚举 404，绑定无效工具 400。模型不能选择地址或修改身份参数。每次运行重新检查 JWT、应用当前绑定、连接班级、启用/测试状态、配置指纹和模式。

对外只发送指定工具参数和服务端注入的 `X-Nexus-Class-Id`、`X-Nexus-Role`、`X-Nexus-User-Id`。不发送本地 JWT、全库、历史或模板。调用结果按 tool_call_id 返回并限长；外部审计只记工具、ID 和状态，不记参数/结果原文。接收方须按专用凭据校验上下文，不能单独信任可伪造的 HTTP 头。

## 模型与迁移

新增 `mcp_connections` 表（迁移 `0005_mcp_connections`）：class_id、name、server_key、credential_ref、state、enabled、fingerprint、tools、创建时间。fingerprint 包含受控配置及凭据变化的摘要，仅内部比较；API 不返回它或凭据引用。tools 保存批准的模式快照；应用复用现有 JSON tools 字段。升级前备份，原工具绑定保持使用。

## 验证

`python -m pytest tests_nexus/test_external_mcp.py -q` 使用临时 SQLite（仅授权相关表）及真实回环 FastMCP HTTP 服务，凭据和问题均虚构。验证发现、实际调用、白名单、参数篡改、班级/角色/绑定、停用/轮换失效、异常脱敏、内置分派和轮次上限。SQLite 不代替 PostgreSQL 迁移与全量业务测试，后者交 PR CI。

公网第三方服务、真实教学资料外发、真实模型触发 MCP 和生产部署均 NOT RUN。本 Issue 未改生产环境。

实际记录：[GitHub Actions](https://github.com/Eppiehu/campusclaw-nexus-group-project/actions/runs/41575356807) 验证实现提交 `c95e661`，后端45项测试全部 PASS，无跳过；包含 PostgreSQL 新库迁移及模拟既有0004结构的升级。前端冻结安装、类型检查及生产构建 PASS。本机6项隔离测试 PASS；本机没有 PostgreSQL，迁移测试由上述 CI 补足。
