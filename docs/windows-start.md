# Windows 一键启动

先安装并启动 Docker Desktop，使用 Linux 容器。下载或克隆仓库后，双击根目录 `start.bat`。路径含空格也可使用；无需 WSL Shell、Python、Node 或 OpenSSL。

首次运行会在仓库根目录生成 `.env.nexus.local`，其中签名密钥、数据库和演示密码均随机生成，默认只监听 `127.0.0.1:8080`。该文件已被 Git 忽略，请保持私有。需要真实 AI 问答时在文件内填写 `OPENAI_API_KEY`，端口占用时修改 `NEXUS_PORT`，已有配置不会被脚本覆盖。

启动器依次构建镜像、启动数据库/Redis、执行迁移和种子初始化，最后启动 API/Worker/Scheduler。只有 API 健康后才打开浏览器。首次构建需要下载依赖和嵌入模型，请为 Docker Desktop 留出足够的内存和磁盘；内存不足时可参考 [Linux 部署说明](linux-deploy.md) 的预编译前端模式。

演示用户名为 `teacher_a`、`student_a1`、`student_b1`，教师和学生密码分别查看本地环境文件的 `NEXUS_TEACHER_PASSWORD`、`NEXUS_STUDENT_PASSWORD`。

命令行也可运行：

```bat
start.bat -Check
start.bat -NoBrowser
```

`-Check` 只执行环境预检（缺配置时仍会生成本地配置）；`-NoBrowser` 完成部署但不打开浏览器。失败返回非零退出码，双击启动时保留错误窗口；自动化可设置 `NEXUS_NO_PAUSE=1` 禁止暂停。脚本不删除数据卷，升级已有数据前请先备份。

本机没有 Docker Desktop，真实 Windows 容器构建/启动为 **NOT RUN**；语法与模拟 Docker 的流程验证单独记录，不代替真实运行。

本次在 Windows PowerShell 5.1 实测：脚本语法解析 PASS；BAT 在缺少 Docker 时返回 1 且不创建配置 PASS。使用模拟 Docker CLI 验证了含空格路径、首次随机配置与凭据不打印、重跑不改配置、迁移失败返回非零且不启动 API，均 PASS。真实浏览器自动打开及完整 Docker Desktop 冷启动仍为 NOT RUN。
