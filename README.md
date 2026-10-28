# CampusClaw Nexus｜智能教学平台开发小组作业

这是课程开发小组作业的**需求与设计仓库**。项目拟在 CampusClaw 课程基础上建设可运行的教师端和学生端，形成“讲义—学习助手—作业”的完整业务路径，并扩展知识缺口回补、同纲不同卷和学情周报。

**当前阶段：方案与接口规约。仓库暂不包含应用代码，也不把其他仓库中的个人实现计为本小组已交付成果。** 实际开发、成员贡献和验收结果以本仓库后续的 Issue、提交、PR 与测试记录为准。

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
- 本仓库初始提交仅含 Markdown 文档；实现代码需经小组确认后再通过 PR 引入。

需求依据：小组选题说明《CampusClaw Nexus：基于 Agentic RAG、MCP 与人机协同知识演进的智能教学平台》。本文档将其整理为开发可执行的要求；如课程后续规则变化，以小组确认后的修订记录为准。

