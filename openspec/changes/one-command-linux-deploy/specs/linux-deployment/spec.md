## ADDED Requirements

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
