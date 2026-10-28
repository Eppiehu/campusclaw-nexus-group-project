# 配置与环境变量规范

本文件说明未来实现时配置项的含义与安全要求。[`.env.example`](../.env.example) 只提供**无密钥模板**，不能直接作为生产配置。变量命名在首个实现 PR 中与程序及 Compose 文件逐项核对，新增或改名须同步更新本文。

## 1. 配置原则

- 配置优先级：运行环境变量高于模板默认值；不在源码中写密钥或真实密码。
- 开发、测试、演示、生产使用独立凭据和数据库。所有密钥由部署者在本机私有 `.env` 或受控密钥系统提供，不提交 Git。
- 启动时校验必填项。生产环境缺少 JWT 签名密钥、数据库密码或公开地址时应拒绝启动；缺少模型密钥时非 AI 功能可运行，但 AI 接口须明确返回不可用，不能静默使用 mock。
- 前端构建变量只允许公开信息。`VITE_` 前缀会进入浏览器包，禁止放密码、Token 或 API Key。
- 修改配置后记录环境、镜像/提交版本和变更原因，不在日志打印完整值。

## 2. 变量清单

| 名称 | 所属服务 | 用途与约束 | 演示/默认策略 |
| --- | --- | --- | --- |
| `APP_ENV` | API/Worker | `development`、`test`、`demo`、`production` | 模板为 `demo` |
| `APP_PORT` | 网关 | 对外 HTTP 端口 | 8080，可改 |
| `PUBLIC_BASE_URL` | API/前端 | 浏览器可访问的完整地址，生产必须 HTTPS | 本地 `http://localhost:8080` |
| `POSTGRES_DB` | DB/API | 数据库名 | `campusclaw_nexus` |
| `POSTGRES_USER` | DB/API | 应用数据库用户 | `nexus_app` |
| `POSTGRES_PASSWORD` | DB/API | 数据库密码；必填、不得提交 | 空值，部署者填写 |
| `DATABASE_URL` | API/Worker | 可选的完整连接串；设置时覆盖分项配置 | 空值；日志不得打印 |
| `REDIS_URL` | API/Worker | 队列与临时状态连接地址 | 容器内 `redis://redis:6379/0` |
| `JWT_SIGNING_KEY` | API | JWT 签名密钥；生产必须随机、足够长 | 空值，部署者填写 |
| `JWT_ISSUER`、`JWT_AUDIENCE` | API | 令牌签发方和受众 | 固定为本项目名称 |
| `JWT_ACCESS_TTL_MINUTES` | API | 短期访问令牌有效期 | 15 |
| `JWT_REFRESH_TTL_DAYS` | API | 刷新凭据有效期及撤销记录期限 | 7 |
| `DEEPSEEK_API_KEY` | API/Worker | 外部模型凭据，仅服务器可见 | 空值；AI 功能不可用 |
| `DEEPSEEK_BASE_URL` | API/Worker | 模型接口地址；仅允许受控目标 | 项目认可的官方地址 |
| `DEEPSEEK_MODEL` | API/Worker | 会话模型标识 | 实现时锁定 |
| `EMBEDDING_BACKEND` | Worker | `local` 或经批准的外部嵌入服务 | `local` |
| `EMBEDDING_MODEL_ID` | Worker | 嵌入模型标识与版本 | 实现时锁定并校验 |
| `EMBEDDING_API_KEY` | Worker | 仅外部嵌入时需要 | 空值 |
| `MATERIAL_STORAGE_PATH` | API/Worker | 材料持久化目录 | 容器数据卷内路径 |
| `UPLOAD_MAX_MB` | API | 单文件大小上限 | 10，按实测调整 |
| `LLM_TIMEOUT_SECONDS` | API/Worker | 模型调用超时 | 60 |
| `MCP_TOOL_TIMEOUT_SECONDS` | API/Worker | 单次工具执行超时 | 15 |
| `MAX_LLM_CONCURRENCY` | API/Worker | 模型并发上限和过载保护 | 依据压测锁定 |
| `QUEUE_MAX_RETRIES` | Worker | 后台任务最大重试次数 | 3 |
| `LOG_LEVEL` | 全部 | 结构化日志级别 | `INFO`；不输出敏感值 |
| `SEED_DEMO_DATA` | 初始化 | 是否允许写入虚构演示数据 | 默认 `false` |
| `SEED_PASSWORD` | 初始化 | 演示账号临时密码；仅演示环境 | 空值，部署者填写 |
| `TEST_BASE_URL` | 测试脚本 | 测试目标；安全脚本须验证为隔离环境 | 空值，显式填写 |
| `VITE_API_BASE_URL` | 前端构建 | 同源 API 路径或公开 URL | `/api`，不含密钥 |

## 3. 令牌与浏览器配置

浏览器访问令牌只保存在内存，请求使用 `Authorization: Bearer`。刷新凭据使用 HttpOnly、SameSite=Lax Cookie；HTTPS 环境设置 Secure，本地 HTTP 演示环境使用单独的非生产配置。刷新/退出接口有 CSRF 防护或等效的同源校验。登录响应不把密钥或数据库信息发给前端。

## 4. 演示与生产差异

演示环境可使用虚构种子数据和本地 HTTP `localhost`。生产环境必须关闭种子数据入口、开启 HTTPS、使用独立密钥和备份策略。任何真实部署不得使用模板中的空值、示例账号密码或模拟模型响应冒充实际能力。

