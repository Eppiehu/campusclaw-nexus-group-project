# CampusClaw Nexus｜智能教学平台开发小组作业

这是课程开发小组作业的**需求与设计仓库**。项目拟在 CampusClaw 课程基础上建设可运行的教师端和学生端，形成“讲义—学习助手—作业”的完整业务路径，并扩展知识缺口回补、同纲不同卷和学情周报。

**当前阶段：在规约基础上引入 Nexus 实现基线，继续按小组 Issue/PR 完成差异修复与验收。** 代码来源、改动、排除项和未达标事项见[实现基线导入审计](docs/implementation-import.md)。个人仓库中的既有实现只计为来源，不冒充两名成员共同完成的开发；实际贡献以本仓库后续的提交、PR 和审核记录为准。

## 当前实现与运行入口

本仓库包含 Python/Flask API、Vue 前端、PostgreSQL/pgvector 迁移、Redis/RQ Worker、LangGraph、MCP 工具、虚构种子账号及隔离测试。它是**待小组复核的实现基线**；完整满足目标规约、Linux 冷启动、并发容量和 HTTPS 尚待逐项验证。

在有 Docker Compose 的全新 Linux 环境，复制 `.env.nexus.example` 为**不入库**的 `.env.nexus.local`，填写随机签名密钥、数据库密码和虚构演示账号密码，然后运行 `sh deploy/nexus-deploy.sh`。脚本先构建前端与本地嵌入模型镜像，再启动数据库和 Redis、执行迁移/种子初始化，最后启动 API、Worker 和 Scheduler。默认对外端口为 8080，可通过 `NEXUS_PORT` 调整；`/health` 用于检查数据库与 Redis。构建阶段需能下载 Python/Node 依赖和公开嵌入模型。当前尚未在干净 Linux 主机实际执行上述流程，不能据此标记 PASS。

不要把 `.env.nexus.local`、真实密钥、数据库、模型缓存、PDF 或截图提交到版本库。组内开发流程与尚未对齐的目标见[实施审计](docs/implementation-import.md)。

## 文档导航

- [功能与权限要求](docs/requirements.md)：角色、课程基线、三项新增业务及失败路径。
- [技术框架与架构](docs/architecture.md)：拟采用的技术栈、模块边界、数据与部署约束。
- [实施阶段与验收](docs/delivery.md)：交付顺序、可复现的验收场景和证据要求。
- [小组协作约定](docs/collaboration.md)：分工原则、Issue/PR 流程和贡献记录。
- [产品规范](docs/product-spec.md)：目标用户、页面与核心流程、交互规则和验收条件。
- [接口与数据契约](docs/contracts.md)：关键实体、权限边界和接口行为。
- [安全规范](docs/security.md)：认证授权、班级隔离、文件与模型工具安全、凭据和审计要求。
- [AI 开发规则](AGENTS.md)：供参与开发的 AI 助手遵守的项目约束。
- [PR 提交模板](.github/pull_request_template.md)：把需求、影响、验证与风险纳入每次评审。
- [OpenSpec 变更](openspec/changes/group-project-baseline/proposal.md)：小组项目基线的变更范围与验收标准。
- [Linux 部署与四项验收门槛](docs/operations-acceptance.md)：容器部署、安全测试、并发压测和虚构种子数据。
- [评审核对表](docs/review-checklist.md)：需求、规约、验收证据和当前状态的对应关系。
- [OpenSpec 设计](openspec/changes/group-project-baseline/design.md)、[任务](openspec/changes/group-project-baseline/tasks.md)与[能力规约](openspec/changes/group-project-baseline/specs)：决策、待办及可测试场景。
- [前端开发蓝图](docs/frontend.md)、[后端开发蓝图](docs/backend.md)：页面、模块、状态、Agent 与任务执行的实现边界。
- [API 清单](docs/api-contract.md)、[数据模型](docs/data-model.md)：接口方法、权限、关键字段和约束。
- [配置与环境变量](docs/configuration.md)、[无密钥配置模板](.env.example)、[Linux 部署方案](docs/linux-deploy.md)：如何配置、构建、迁移、初始化与验收。
- [开发任务拆解](docs/work-plan.md)：工作包、依赖、两人协作与完成定义。
- [实现基线导入审计](docs/implementation-import.md)：代码来源、已验证项和与目标规约的差异。

## 项目目标

1. 教师与学生使用真实账号和持久化数据完成班级内的讲义、问答、作业和批改流程。
2. AI 回答能够追溯材料出处；缺少证据时登记候选知识缺口，由教师审核和补充。
3. 每位学生获得独立题目实例，按本人题目的服务端标准答案批改，并保留人工复核。
4. 学情周报的数字由程序统计，AI 只负责解释和建议，教师审核后发布。
5. 交付可部署、可测试、可审计的系统；公网 HTTPS 是最终目标，未完成前不得写成已验收。
6. 在老师提供的 Linux 环境中完成容器化冷启动、自动化安全测试、并发性能实测和种子数据验收。

## 约束

- 服务端按当前登录身份和班级校验每次资源访问，不能仅靠前端隐藏数据。
- 密钥、账号密码、真实学生数据和部署凭据不得提交到仓库。
- 实现代码通过独立分支和 PR 引入；成员需分别认领后续变更，不能将导入的个人项目算作两人共同开发。

需求依据：小组选题说明《CampusClaw Nexus：基于 Agentic RAG、MCP 与人机协同知识演进的智能教学平台》。本文档将其整理为开发可执行的要求；如课程后续规则变化，以小组确认后的修订记录为准。
