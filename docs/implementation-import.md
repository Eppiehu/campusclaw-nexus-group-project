# Nexus 实现基线导入审计

## 来源与归属

本次实现基线取自维护者的个人仓库 [Eppiehu/campusclaw-coursework](https://github.com/Eppiehu/campusclaw-coursework)，本地来源提交为 `a770f6a`（2026-10-25）。这是已有个人实践的有来源复用，**不是两名组员共同新写的代码**。后续组员各自完成的功能、修复、测试和评审，以本仓库 Issue/PR 留痕。代码被复制到本仓库后，其功能与验收状态以本仓库的运行结果为准，不继承个人仓库的历史 PASS。

## 导入范围

- `app/nexus/`、必要的文本切片/Embedding/Skill 解析模块，以及独立的 Flask 入口。
- `web/` 中 Vue/TypeScript 源码和锁文件；不提交 `dist`、`node_modules` 或包缓存。
- PostgreSQL/pgvector 迁移、Redis/RQ Worker/Scheduler、虚构种子账号、Nexus 测试。
- 独立的 Dockerfile/Compose、无密钥 `.env.nexus.example`、GitHub Actions 检查和部署脚本。

不导入课程旧版 MySQL/Qdrant/SQLite 实现、个人作业报告、PDF、截图、数据库、上传文件、模型缓存、真实 `.env` 或生产部署凭据。个人仓库的演示材料和完整运行记录不作为本组交付证据。

## 为独立仓库所作调整

1. `app/__init__.py` 仅导出 Nexus Flask 应用，避免导入旧课程模块。
2. Dockerfile 在构建阶段生成 Vue 静态资源并下载公开的本地 Embedding 模型，运行时不依赖开发者机器上的 `web/dist` 或模型缓存。
3. Compose 项目名与镜像名改为 `campusclaw-nexus-group`，默认外部端口 8080；数据库和 Redis 不向宿主机暴露端口。
4. 部署/备份脚本以当前仓库为根目录，避免对个人项目的固定服务器目录产生依赖。

## 与小组目标规约的差异

| 范围 | 导入基线实际状态 | 小组目标与后续工作 |
| --- | --- | --- |
| 前端组织 | Vue 3/TypeScript/Vite/Element Plus/ECharts，主要页面集中于 `web/src/App.vue` | 按[前端蓝图](frontend.md)拆分模块，补 Vue Router、Pinia 与 Playwright E2E |
| API 契约 | 使用 `/api/nexus/*` 和 `NEXUS_*` 配置；另有 `OPENAI_API_KEY` | 与[API 清单](api-contract.md)、[配置规范](configuration.md)统一或经 OpenSpec 修订目标 |
| 浏览器认证 | Bearer JWT 保存在 `localStorage`，令牌吊销由服务端检查 | 改为短期内存令牌及受保护刷新机制；复核 CSRF、失效和跨班场景 |
| 镜像与依赖 | 依赖范围而非完整锁定，构建时在线获取前端包、Python 包及公开模型 | 锁定镜像摘要/依赖，做干净 Linux 冷启动与离线失败提示 |
| 发布入口 | 独立 HTTP 8080 演示端口 | 域名、HTTPS、反向代理和备份恢复仍需验收 |
| 安全与容量 | 有服务端权限测试、任务与并发限制的基础实现 | 增补隔离环境安全脚本、跨班/失败路径、并发压测与实测门槛 |

上述差异不得通过修改 README 文案掩盖。每项应由负责人建 Issue，先更新 OpenSpec，再以可复现测试和 PR 收敛。

## 本次验证

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 选定文件的明文密钥/私钥模式扫描 | PASS | 未发现真实 API Key、SSH 私钥或个人服务器口令；CI 中仅有明确标注的虚构测试密码 |
| Python 源码语法编译 | PASS | 本地运行 `python -m compileall -q app scripts tests_nexus migrations` |
| Vue 类型检查与构建 | PASS | 在来源相同的 `web/` 源码上运行 `vue-tsc --noEmit` 与 `vite build`；产物未入库 |
| PostgreSQL/Redis 业务测试 | NOT RUN | 本轮本机没有隔离的服务环境；以 PR 的 CI 结果为准，不能提前声明通过 |
| Docker 镜像构建与 Linux 冷启动 | NOT RUN | 本轮无本地 Docker；需在全新 Linux 上按 README 实测 |
| 外部 DeepSeek/MCP、并发和 HTTPS | NOT RUN | 需要授权的隔离环境、配置和原始验收记录 |

## 下一步组内分工

维护者负责解释导入代码的架构、修正容器/接口问题；`hxflb` 选择并认领独立工作包，例如前端模块拆分与端到端测试，或安全脚本与跨班验收。真实负责人以 Issue 认领为准，不能由本文替组员确认贡献。两人互审 PR 后再合并。
