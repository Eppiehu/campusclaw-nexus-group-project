# 技术框架与架构

以下是**拟采用的框架要求**；具体版本和依赖在实现 PR 中锁定，不把选型写作已部署事实。

| 层次 | 拟采用技术 | 责任边界 |
| --- | --- | --- |
| Web 前端 | Vue 3、TypeScript、Vite、Element Plus、ECharts | 教师/学生页面、交互状态、统计展示 |
| 业务 API | Python、Flask、SQLAlchemy、Alembic | REST 接口、事务、迁移与业务校验 |
| 认证与授权 | JWT Bearer、RBAC | 令牌撤销、角色和班级资源隔离 |
| 数据与检索 | PostgreSQL、pgvector、全文检索、Embedding、RRF | 业务持久化、材料版本、混合检索与引用 |
| Agent 与模型 | DeepSeek API、LangGraph、Pydantic | 会话编排、SSE、Skill、结构化结果校验 |
| 外部工具与任务 | MCP Python SDK、Redis、RQ Worker | 工具调用、索引、发卷、批改及周报任务 |
| 质量与部署 | OpenSpec、pytest、Playwright、GitHub Actions、Docker Compose、Nginx | 规约、测试、CI、容器运行与 HTTPS 入口 |

## 分层关系

教师/学生 Web → Flask API 与权限层 → Agent、Skill、RAG 和 MCP 服务 → 异步 Worker → PostgreSQL/pgvector、Redis 与材料文件存储。

- **权限先于检索或工具执行**：班级范围来自已认证身份，不能信任客户端自报的班级。
- **数据先于模型解释**：检索证据、标准答案、评分事实与周报统计由程序产生；模型输出须校验或供教师复核。
- **版本先于切换**：新讲义索引成功后才将其设为生效版本，旧问答引用锚定原片段。
- **任务先持久化后入队**：后台任务记录排队、运行、失败和重试，避免队列故障时丢失业务状态。

## 接口与数据契约待定项

首轮开发前通过 OpenSpec/PR 固定用户、班级、材料版本、Agent、会话、Skill、作业实例、提交、知识缺口、周报和审计记录的字段；同时明确错误码、幂等约束及跨班访问策略。接口变更先更新契约，再更新实现和测试。

## 部署边界

目标环境为 Linux + Docker Compose，API、Worker、PostgreSQL 和 Redis 分服务运行；数据库与 Redis 不直接暴露公网。使用独立数据卷、备份与健康检查。Nginx/HTTPS 属于最终交付目标，需在域名、证书和端到端验证完成后单独标记通过。

