# Linux 一键容器部署

低内存服务器可先在工作站的 `web/` 运行 `pnpm install --frozen-lockfile && pnpm run build`，把同一提交的 `web/dist` 连同源码传到服务器，并在私有环境文件设置 `NEXUS_DOCKERFILE=Dockerfile.nexus.prebuilt`。该模式仍构建后端镜像，但避免在服务器编译前端；默认模式保持完整多阶段构建。

在 Linux x86_64、Docker Engine 与 Compose 插件可用的主机上，从仓库根目录运行：

```sh
sh deploy/nexus-deploy.sh
```

首次运行自动生成仅本机保存的 `.env.nexus.local`，权限由 `umask 077` 限制。文件内有随机数据库、签名和虚构演示账号密码；不要提交或复制到公开日志。需要其他端口时，在再次运行前修改 `NEXUS_PORT`。接入 DeepSeek 时仅在该私有文件填写 `OPENAI_API_KEY`。未配置时真实 AI 调用为 NOT RUN。

脚本检查 Docker、Compose、配置和端口，构建前端与后端镜像，启动 PostgreSQL/Redis，等待它们健康，执行迁移与幂等种子初始化，再启动 API/Worker/Scheduler 并等待 `/health`。可用 `sh deploy/nexus-deploy.sh --check` 只做预检。构建阶段需要访问 npm、PyPI 和公开嵌入模型源；首次构建可能较久。默认只有 API 的 8080 对外映射，数据库与 Redis 不开放宿主机端口。

网络受限时可在私有环境文件中设置 `NEXUS_NPM_REGISTRY`、`NEXUS_PIP_INDEX_URL` 为可访问的依赖镜像。若已有可信的 `BAAI/bge-small-zh-v1.5` FastEmbed 缓存，把缓存内容放进仓库根目录 `model-cache/`（该目录被 Git 忽略），并设置 `NEXUS_PREFETCH_MODEL=0`；否则保持默认值 `1`，在构建阶段下载模型。不得把模型文件提交到 Git。

部署后检查：

```sh
curl -f http://127.0.0.1:8080/health
docker compose --env-file .env.nexus.local -f docker-compose.nexus.yml ps
```

演示账号包含 `teacher_a`、`student_a1`、`student_b1`。教师和学生密码分别从私有环境文件中的 `NEXUS_TEACHER_PASSWORD`、`NEXUS_STUDENT_PASSWORD` 读取。重跑脚本不会重复创建账号，但会按环境文件更新这些种子账号的密码。不要在真实资料库中运行虚构种子初始化。

排错：脚本出现 FAIL 时会退出并保留容器、数据卷和日志；根据提示查看相应服务日志。不要用 `docker compose down -v` 排错。升级前备份数据库卷并核对迁移兼容性；回退时要同时考虑数据库版本。公网 HTTPS、备份恢复、并发容量和完整安全测试仍需单独验收。
