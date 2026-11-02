# Windows 一键启动

先安装并启动 Docker Desktop，使用 Linux 容器。下载或克隆仓库后，双击根目录 `start.bat`。路径含空格也可使用；无需 WSL Shell、Python、Node 或 OpenSSL。

首次运行会在仓库根目录生成 `.env.nexus.local`，其中签名密钥、数据库和演示密码均随机生成，默认只监听 `127.0.0.1:8080`。该文件已被 Git 忽略，请保持私有。需要真实 AI 问答时在文件内填写 `OPENAI_API_KEY`，端口占用时修改 `NEXUS_PORT`，已有配置不会被脚本覆盖。

`start.bat` 是日常入口：已有镜像时跳过构建，只启动已有服务或补建缺失服务，保留现有容器，不执行迁移、不重置账号。首次空数据库才执行迁移和演示账号初始化，判断依据是数据库中的实际账号，而不是本地标记文件。只有 API 健康后才打开浏览器。

首次构建需要下载依赖和嵌入模型，请为 Docker Desktop 留出足够的内存和磁盘；内存不足时可参考 [Linux 部署说明](linux-deploy.md) 的预编译前端模式。

拉取新版代码后，先备份数据，再运行 **`update.bat`**：构建完成后暂停应用、执行数据库迁移（`--migrate-only`，不运行种子账号更新），然后启动新版。迁移失败时应用保持停止，需按错误排查或从备份回退。日常打开页面不要运行更新入口。

数据库与 Redis 使用 Compose 命名卷持久化，关闭启动窗口或浏览器不会停止后台容器。主机重启后启动 Docker Desktop；服务按 `unless-stopped` 策略恢复，也可再次运行 `start.bat`。保留 `.env.nexus.local` 与数据卷，资料、账号和作业可持续使用；不要执行 `down -v` 删除数据卷。

演示用户名为 `teacher_a`、`student_a1`、`student_b1`，教师和学生密码分别查看本地环境文件的 `NEXUS_TEACHER_PASSWORD`、`NEXUS_STUDENT_PASSWORD`。

命令行也可运行：

```bat
start.bat -Check
start.bat -NoBrowser
update.bat -NoBrowser
```

`-Check` 只执行环境预检（缺配置时仍会生成本地配置）；`-NoBrowser` 完成启动但不打开浏览器。失败返回非零退出码，双击启动时保留错误窗口；自动化可设置 `NEXUS_NO_PAUSE=1` 禁止暂停。脚本不删除数据卷。

本机没有 Docker Desktop，真实 Windows 容器构建/启动为 **NOT RUN**；语法与模拟 Docker 的流程验证单独记录，不代替真实运行。

本次在 Windows PowerShell 5.1 实测：脚本语法解析 PASS；BAT 在缺少 Docker 时返回 1 且不创建配置 PASS。使用模拟 Docker CLI 验证了含空格路径、首次随机配置与凭据不打印、重跑不改配置、迁移失败返回非零且不启动 API，均 PASS。真实浏览器自动打开及完整 Docker Desktop 冷启动仍为 NOT RUN。

持续运行修订另验证：模拟已有数据库的日常启动不执行 build、迁移、seed 或容器重建 PASS；显式更新只执行迁移、失败时不启动新版 PASS。真实数据卷跨重启持久化仍为 NOT RUN。
