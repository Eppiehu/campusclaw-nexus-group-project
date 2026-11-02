# 服务器升级验证

本次将小组主分支 `b823bb0` 的业务实现及部署分支的低内存构建支持部署到既有服务器 8088。服务器为 Ubuntu 24.04、2 vCPU、2 GiB RAM、Docker Compose 2.40.3。

完整前端容器构建在该主机上造成内存压力，本次停止该构建，改在工作站按冻结锁文件完成 `vue-tsc` 和 Vite 构建，再使用 `Dockerfile.nexus.prebuilt` 构建服务器镜像。模型来自该主机既有的公开 FastEmbed 缓存；运行时离线加载。该记录不代表无缓存主机的完整冷启动已通过。

| 验证 | 结果 |
| --- | --- |
| 工作站冻结锁文件安装、类型检查与生产前端构建 | PASS |
| Linux prebuilt 模式镜像构建 | PASS |
| 旧数据库备份恢复到新版独立卷并执行迁移 | PASS |
| 迁移前后账号、材料、材料版本数量 | PASS：5、3、6，分别一致 |
| 既有种子账号幂等初始化 | PASS：created none / refreshed none |
| 公网 8088 首页、health | PASS：均为 200 |
| teacher_a、student_a1、student_b1 登录并读取本班材料 | PASS |
| 未登录访问材料 | PASS：401 |
| API、数据库、Redis 健康状态 | PASS |
| Worker 和 Scheduler | PASS：均运行；Worker 正在监听 nexus 队列 |
| 升级前待执行任务 | PASS：无待执行任务，18 条均 succeeded |
| 原站应用容器 | PASS：保持运行，原端口映射保留 |
| 一键脚本语法及配置预检 | PASS |
| 无缓存主机完整冷启动、重启持久化、完整安全回归、并发压测、真实 AI 调用、HTTPS | NOT RUN |

旧 Nexus 应用容器已停止，旧数据卷和旧镜像仍保留。数据库和配置备份仅存服务器私有目录，未提交到 Git。新版只接管 8088，未更改原站 80/443 配置。
