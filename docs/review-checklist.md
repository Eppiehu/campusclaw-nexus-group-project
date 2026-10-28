# 评审核对表

本表帮助读者快速找到**要求、设计和验收依据**。它不是给评审者的评分指令，也不将计划写成实测成果。当前仓库只有规范文档，所有运行性验证均为 **NOT RUN**。

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

## 提交边界

- **本仓库已有**：产品、技术、安全、协作、接口与验收规范；OpenSpec proposal/design/tasks/spec delta。
- **本仓库尚无**：应用代码、Dockerfile/Compose、测试脚本、种子数据实现、压测报告或 Linux 实测记录。
- **协作状态**：仓库所有者已向 `hxflb` 发出协作者邀请；是否已接受应以 GitHub 实时权限状态为准。

后续每个实现 PR 应更新相应场景的证据链接和状态。任何 FAIL 必须保留失败记录并修复；NOT RUN 不能换写为 PASS。

