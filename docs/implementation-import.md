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

## 相对已合并 main 的工作区改动

下面是 2026-11-02 工作区相对 `origin/main` 的差异，尚未提交。只记录代码里已经存在的行为；没有实测的项目保持 NOT RUN。

### 前端

- `web/src/App.vue` 改为路由出口。页面、Pinia 和只接受显式隔离地址的 Playwright 在 `web/src`、`web/e2e`。这是 Issue #6 的范围。
- 新增讲义上传的应用范围步骤、学习助手默认打开最近会话、助手 Markdown 展示、学生错题记录和独立作答页、教师参数确认与变量插入按钮。
- 新增依赖 `markdown-it`、`dompurify`。`web/src/ScoreChart.vue` 移到 `web/src/components/ScoreChart.vue`。

### 后端、数据和脚本

- 迁移 `0003_chunk_options`：材料版本保存上传时选择的切片参数。
- 迁移 `0004_answer_hint`：作业增加作答提示。学生作答时可见；批改请求不包含它。截止前学生看不到评分说明和参考答案。
- 评分说明由合计 100 分的分项改为 1 至 2000 字的文字。模型返回一个 0 到 100 的总分和评语；学生最终数值与标准答案不一致时，总分最高记 40。旧的分项数组只在读取时转成文字。
- 种子账号已存在时，会按当前环境中的虚构口令校正角色、班级和口令。空的进程环境变量才会从 `.env.nexus.local` 补上，已有值不被覆盖。
- Worker 增加每秒一次的到期批改扫描。Linux、WSL 或容器内运行；Windows 本机仍拒绝启动 Worker。

对应规约在 `openspec/changes/split-frontend-modules`、`openspec/changes/text-grading-rubric` 和 `openspec/changes/assignment-hint-and-late-answer`。课程目标文档里的分项 Rubric、`/grading/:id` 等仍是小组目标，不因这次实现自动改写。

## 与小组目标规约的差异

| 范围 | 导入基线实际状态 | 小组目标与后续工作 |
| --- | --- | --- |
| 前端组织 | 已合并的 `main` 仍把页面集中在 `web/src/App.vue`。路由拆分、Pinia 和 Playwright 在未提交工作区；2026-11-02 的 8 项本地结果见下方验证表，不能写成已合并 | 令牌刷新、SSE/失败路径和移动端仍按[前端蓝图](frontend.md)继续补齐，这些用例保持 NOT RUN |
| API 契约 | 使用 `/api/nexus/*` 和 `NEXUS_*` 配置；另有 `OPENAI_API_KEY` | 与[API 清单](api-contract.md)、[配置规范](configuration.md)统一或经 OpenSpec 修订目标 |
| 浏览器认证 | Bearer JWT 保存在 `localStorage`，令牌吊销由服务端检查 | 改为短期内存令牌及受保护刷新机制；复核 CSRF、失效和跨班场景 |
| 镜像与依赖 | 依赖范围而非完整锁定，构建时在线获取前端包、Python 包及公开模型 | 锁定镜像摘要/依赖，做干净 Linux 冷启动与离线失败提示 |
| 发布入口 | 独立 HTTP 8080 演示端口 | 域名、HTTPS、反向代理和备份恢复仍需验收 |
| 安全与容量 | 有服务端权限测试、任务与并发限制的基础实现 | 增补隔离环境安全脚本、跨班/失败路径、并发压测与实测门槛 |

上述差异不得通过修改 README 文案掩盖。每项应由负责人建 Issue，先更新 OpenSpec，再以可复现测试和 PR 收敛。

## 本次验证

下表中的 CI 结果属于已经合并的导入基线，不能当成当前工作区后端改动的通过记录。

| 项目 | 结果 | 证据/限制 |
| --- | --- | --- |
| 选定文件的明文密钥/私钥模式扫描 | PASS | 未发现真实 API Key、SSH 私钥或个人服务器口令；CI 中仅有明确标注的虚构测试密码 |
| Python 源码语法编译 | PASS | 本地运行 `python -m compileall -q app scripts tests_nexus migrations` |
| Vue 类型检查与构建 | PASS | 2026-11-02 在当前 `web/` 运行 `pnpm run build`；产物未入库 |
| 锁定依赖安装 | PASS | 2026-11-02 在 `web/` 运行 `pnpm install --frozen-lockfile` |
| Issue #6 Playwright | PASS | 2026-11-02，`PLAYWRIGHT_BASE_URL=http://127.0.0.1:8081`，`PLAYWRIGHT_CHANNEL=msedge`，8 passed。Playwright 自带 Chromium 的下载未完成。跨班用例留下标题以「隔离讲义」开头的材料 17、18、19 |
| 当前工作区的 pytest | NOT RUN | 评分说明、作答提示和切片参数的服务端测试没有在这份工作区重跑 |
| SSE、索引失败、发卷失败、周报草稿、移动端 | NOT RUN | 不在 Issue #6 的必测列表里 |
| PostgreSQL/Redis 业务测试 | PASS | [PR #5 的 Nexus checks](https://github.com/Eppiehu/campusclaw-nexus-group-project/actions/runs/41202412884) 后端 Job 在 GitHub Actions 的隔离 PostgreSQL/Redis 服务中完成 `pytest tests_nexus -q`；本机未运行该测试 |
| Vue CI 构建 | PASS | 同一工作流的前端 Job 完成 `pnpm install --frozen-lockfile` 和 `pnpm run build` |
| Docker 镜像构建与 Linux 冷启动 | NOT RUN | 本轮无本地 Docker；需在全新 Linux 上按 README 实测 |
| 外部 DeepSeek/MCP、并发和 HTTPS | NOT RUN | 需要授权的隔离环境、配置和原始验收记录 |

## 下一步组内分工

维护者负责解释导入代码的架构、修正容器/接口问题；`hxflb` 选择并认领独立工作包，例如前端模块拆分与端到端测试，或安全脚本与跨班验收。真实负责人以 Issue 认领为准，不能由本文替组员确认贡献。两人互审 PR 后再合并。
