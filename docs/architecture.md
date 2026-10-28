# 技术框架与架构

以下是**拟采用的框架要求**；目标大版本用于统一开发方向，补丁版本、镜像摘要和完整依赖在实现 PR 中锁定，不把选型写作已部署事实。

| 层次 | 拟采用技术 | 责任边界 |
| --- | --- | --- |
| Web 前端 | Vue 3、TypeScript 5.x、Vite、Vue Router、Pinia、Element Plus、ECharts | 教师/学生页面、交互状态、统计展示 |
| 业务 API | Python 3.12、Flask 3.x、SQLAlchemy 2.x、Alembic、Gunicorn | REST/SSE 接口、事务、迁移与业务校验 |
| 认证与授权 | JWT Bearer、RBAC | 令牌撤销、角色和班级资源隔离 |
| 数据与检索 | PostgreSQL 16+、pgvector、全文检索、本地或经批准的 Embedding、RRF | 业务持久化、材料版本、混合检索与引用 |
| Agent 与模型 | DeepSeek API、LangGraph、Pydantic | 会话编排、SSE、Skill、结构化结果校验 |
| 外部工具与任务 | MCP Python SDK、Redis 7+、RQ Worker | 工具调用、索引、发卷、批改及周报任务 |
| 质量与部署 | OpenSpec、pytest、Playwright、GitHub Actions、Docker Compose、Nginx | 规约、测试、CI、容器运行与 HTTPS 入口 |

## 分层关系

教师/学生 Web → Flask API 与权限层 → Agent、Skill、RAG 和 MCP 服务 → 异步 Worker → PostgreSQL/pgvector、Redis 与材料文件存储。

- **权限先于检索或工具执行**：班级范围来自已认证身份，不能信任客户端自报的班级。
- **数据先于模型解释**：检索证据、标准答案、评分事实与周报统计由程序产生；模型输出须校验或供教师复核。
- **版本先于切换**：新讲义索引成功后才将其设为生效版本，旧问答引用锚定原片段。
- **任务先持久化后入队**：后台任务记录排队、运行、失败和重试，避免队列故障时丢失业务状态。

## 接口与数据契约

接口组、拟定路径与错误码见 [API 清单](api-contract.md)；实体、关系、约束和索引见 [数据模型](data-model.md)。首轮开发前仍需通过 OpenSpec/PR 锁定最终字段和迁移。接口变更先更新契约，再更新实现和测试。

## 部署边界

目标环境为 Linux + Docker Compose，API、Worker、PostgreSQL 和 Redis 分服务运行；数据库与 Redis 不直接暴露公网。使用独立数据卷、备份与健康检查。Nginx/HTTPS 属于最终交付目标，需在域名、证书和端到端验证完成后单独标记通过。

交付时需包含可复现构建的 Dockerfile、Compose 文件、无密钥的环境变量示例、数据库迁移与虚构数据初始化入口。容器以非特权用户运行，服务间依赖以健康状态和重试处理；只开放 Web 入口，数据库及队列保留在内部网络。老师在全新 Linux 环境执行冷启动时，不应需要项目成员手工改源码或导入私有文件。

并发容量以实测决定。API 应设置连接池、请求超时、上传限制与队列背压；模型调用、索引和批改任务应有并发上限，避免外部模型限流拖垮普通页面。压测分别记录非 AI API、SSE 对话和后台任务的吞吐、延迟、错误率及资源占用。详细门槛见 [Linux 部署与四项验收门槛](operations-acceptance.md)。

完整实施分层见 [前端蓝图](frontend.md) 与 [后端蓝图](backend.md)；所需配置见 [配置与环境变量](configuration.md)，Linux 冷启动步骤见 [部署方案](linux-deploy.md)。

