## ADDED Requirements

### Requirement: 导入实现须保留真实来源和边界
系统仓库 SHALL 标明外部/个人代码来源提交，并明确区分来源代码与小组后续贡献。导入 SHALL 不包含真实密钥、数据库、模型缓存、PDF 和个人报告。

#### Scenario: 审核者核查导入来源
- **WHEN** 审核者打开实现导入 PR
- **THEN** 能找到来源仓库、提交、文件范围、排除项、已验证项和 NOT RUN 项

### Requirement: Linux 构建不得依赖开发者机器产物
容器构建 SHALL 从入库的前端源码生成静态资源，并准备运行所需的公开 Embedding 模型；部署 SHALL 使用独立 Compose 项目和不入库的私有环境配置。

#### Scenario: 全新 Linux 主机冷启动
- **WHEN** 审核者在全新 Linux 主机复制无密钥模板、填入测试凭据并运行部署脚本
- **THEN** 构建不要求预先存在 `web/dist` 或个人模型缓存，数据库、Redis、API 和 Worker 可在独立项目中启动

### Requirement: 未验证能力不得标记通过
每项测试 SHALL 标注 PASS、FAIL 或 NOT RUN；来源仓库的历史结果 SHALL 不自动成为本仓库的验证结果。

#### Scenario: 缺少 Docker 或外部服务
- **WHEN** 本轮环境未执行 Linux 容器冷启动、数据库测试或模型调用
- **THEN** PR 和导入审计将其列为 NOT RUN，并给出后续验收入口
