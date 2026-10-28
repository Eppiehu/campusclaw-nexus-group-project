# Design

## Context

项目当前只有规范和无密钥模板，尚无应用代码。技术栈已规划为 Vue 3/TypeScript 前端、Flask API、PostgreSQL/pgvector、LangGraph、Redis/RQ 与 Docker Compose；此变更要把它转成可分工、可配置、可验收的蓝图。

## Goals / Non-Goals

**Goals:** 定义页面、模块、API、实体、配置、部署和工作包之间的映射；保持班级隔离与真实运行结果可核对。

**Non-Goals:** 不实现软件、不生成含密钥的 `.env`、不宣称 Linux 或性能验收通过。

## Decisions

1. 前端使用 Vue Router/Pinia 管理路由和短期身份状态；访问令牌只留在内存，刷新凭据使用同源 HttpOnly Cookie。服务端仍是授权唯一依据。
2. Flask Blueprint 只处理请求边界，服务层处理业务，仓储层访问数据库，Pydantic 校验输入和模型结构化结果。Worker 承担耗时索引、发卷、批改和周报。
3. 所有 API 使用统一 JSON 错误和请求 ID；SSE 通过携带 Bearer 的 POST fetch 流返回，工具事件与结果必须可关联。
4. PostgreSQL 保存业务事实、不可变版本与审计，pgvector 保存授权材料片段向量，Redis 不作为成绩或最终状态的唯一存储。
5. Compose 只暴露 Web 入口，数据库/Redis 内网运行；`.env.example` 中所有秘密值为空。无模型密钥时非 AI 功能可用、AI 明确不可用。
6. 具体依赖版本由首个实现 PR 锁定；本文只规定目标大版本和功能边界，避免文档与实际锁文件不一致。

## Risks / Trade-offs

- 无密钥模板不能直接启动完整 AI 功能；部署者需要安全提供真实凭据并单独验证。
- 规划的路径和字段可能随实现调整；必须先改契约、再改代码和测试。
- 只写蓝图不等于老师 Linux 环境可运行；所有运行性场景仍为 NOT RUN。

