## ADDED Requirements

### Requirement: Windows 一键启动

Windows 用户 SHALL 能通过仓库根目录 `start.bat` 调用 PowerShell 5.1，复用现有 Compose 完成配置、构建、迁移及健康等待。脚本 SHALL 保留已有配置、不打印凭据，并只在 API 健康后打开本机地址。

#### Scenario: Windows 首次启动

- **WHEN** Docker Desktop 的 Linux 引擎已运行且配置不存在
- **THEN** 生成随机私有配置，默认监听 127.0.0.1:8080，部署健康后打开浏览器

#### Scenario: Docker 不可用或迁移失败

- **WHEN** Docker 缺失、引擎非 Linux 或迁移失败
- **THEN** 返回非零状态；不打开浏览器，迁移失败后不启动 API

### Requirement: 一条命令部署 Nexus 隔离栈

部署者在支持 Docker Compose 的 Linux 主机运行 `sh deploy/nexus-deploy.sh`，系统 SHALL 创建私有随机演示配置（仅在缺失时）、检查配置与端口、构建镜像、完成迁移和种子初始化，并等待 API 健康。脚本 SHALL 在任一失败时返回非零状态，保留现有数据卷，不停止其他 Compose 项目。

#### Scenario: 首次部署

- **WHEN** 私有配置不存在且默认端口未占用
- **THEN** 脚本生成权限受限的配置并在健康检查通过后返回零状态，不在输出中显示密码

#### Scenario: 端口被其他服务占用

- **WHEN** 新项目尚无 API 容器而目标端口被占用
- **THEN** 脚本在构建或更改容器前退出，并提示改用其他端口

#### Scenario: 初始化或健康失败

- **WHEN** 迁移、种子或 API 健康检查失败
- **THEN** 脚本返回非零状态，保留容器和数据卷供排错

#### Scenario: 网络受限但已有可信模型缓存

- **WHEN** 部署者在私有配置中选择依赖镜像并提供本地 FastEmbed 缓存
- **THEN** 构建可以跳过模型下载，缓存不进入 Git 仓库
