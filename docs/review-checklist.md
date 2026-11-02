# 评审核对表

本表帮助读者快速找到**要求、设计和验收依据**。它不是给评审者的评分指令，也不将计划写成实测成果。`main` 已有 Nexus 实现基线；工作区里还有尚未提交的改动。某项只有代码或文档、没有本仓库实测记录时，状态仍是 **NOT RUN**。已有证据的项目见[实现基线导入审计](implementation-import.md)，不能把该审计里的局部 PASS 写成下面整行课程场景已通过。

| 核对项 | 需求/设计位置 | 可测试场景 | 当前状态 |
| --- | --- | --- | --- |
| 教师/学生与 A/B 班隔离 | [功能要求](requirements.md)、[安全规范](security.md) | [班级访问规约](../openspec/changes/group-project-baseline/specs/class-access/spec.md) | NOT RUN |
| 多 AI 应用、提示词、Skill、MCP、流式会话 | [产品规范](product-spec.md)、[架构](architecture.md) | [知识与 Agent 规约](../openspec/changes/group-project-baseline/specs/knowledge-and-agent/spec.md) | NOT RUN |
| 混合检索、来源与版本、知识缺口回补 | [功能要求](requirements.md)、[接口契约](contracts.md) | [知识与 Agent 规约](../openspec/changes/group-project-baseline/specs/knowledge-and-agent/spec.md) | NOT RUN |
| 同纲不同卷、批改和教师复核 | [产品规范](product-spec.md)、[功能要求](requirements.md) | [教学业务规约](../openspec/changes/group-project-baseline/specs/teaching-workflows/spec.md) | NOT RUN |
| 学情事实聚合、周报草稿与发布 | [产品规范](product-spec.md)、[功能要求](requirements.md) | [教学业务规约](../openspec/changes/group-project-baseline/specs/teaching-workflows/spec.md) | NOT RUN |
| Linux 容器化部署 | [运行验收](operations-acceptance.md)、[架构](architecture.md) | [运行交付规约](../openspec/changes/group-project-baseline/specs/operational-readiness/spec.md) | NOT RUN |
| 安全自动化脚本 | [安全规范](security.md)、[运行验收](operations-acceptance.md) | [运行交付规约](../openspec/changes/group-project-baseline/specs/operational-readiness/spec.md) | NOT RUN |
| 并发容量与降级 | [运行验收](operations-acceptance.md)、[架构](architecture.md) | [运行交付规约](../openspec/changes/group-project-baseline/specs/operational-readiness/spec.md) | NOT RUN |
| 虚构种子数据 | [运行验收](operations-acceptance.md) | [运行交付规约](../openspec/changes/group-project-baseline/specs/operational-readiness/spec.md) | NOT RUN |
| 前端/后端实现分工 | [前端蓝图](frontend.md)、[后端蓝图](backend.md)、[开发任务拆解](work-plan.md) | [实施蓝图 OpenSpec](../openspec/changes/complete-implementation-blueprint/proposal.md) | 基线代码已在 `main`；Issue #6 的本地 Playwright 见导入审计。课程级场景仍为 NOT RUN |
| API、数据和环境配置 | [API 清单](api-contract.md)、[数据模型](data-model.md)、[配置说明](configuration.md) | [实施蓝图 OpenSpec](../openspec/changes/complete-implementation-blueprint/proposal.md) | 基线使用 `NEXUS_*` 与 `/api/nexus/*`。与目标契约的差异未关闭，运行验收 NOT RUN |

## 提交边界

- **本仓库已有**：产品与验收规范、OpenSpec、无密钥配置模板，以及已合并的 Nexus 实现基线（API、前端、迁移、Compose、虚构种子和 `tests_nexus`）。
- **工作区另有、尚未合并**：前端模块拆分、作业文字评分说明、作答提示、讲义切片参数等。这些不能写成已合并成果。
- **本仓库尚无**：压测报告、干净 Linux 冷启动记录，以及把四项运行门槛标成 PASS 的证据。
- **协作状态**：仓库所有者已向 `hxflb` 发出协作者邀请；是否已接受应以 GitHub 实时权限状态为准。

后续每个实现 PR 应更新相应场景的证据链接和状态。任何 FAIL 必须保留失败记录并修复；NOT RUN 不能换写为 PASS。
