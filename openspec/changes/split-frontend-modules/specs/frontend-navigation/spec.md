## ADDED Requirements

### Requirement: 刷新后停留在原页面
已登录用户刷新浏览器时，前端 SHALL 先用现有令牌恢复服务端身份，再显示刷新前的路由。未持有令牌时，受保护路由 SHALL 进入登录页，并在登录成功后回到原先请求的地址。

#### Scenario: 刷新讲义页
- **WHEN** 已登录用户在 `/materials` 刷新浏览器
- **THEN** 页面仍显示讲义知识库，而不是登录页

#### Scenario: 未登录访问作业页
- **WHEN** 访客直接打开 `/assignments`
- **THEN** 前端进入登录页；登录成功后打开作业页

### Requirement: 角色导航不能代替服务端拒绝
教师和学生 SHALL 看到各自的导航。学生直接打开教师页面或提交讲义上传时，前端 SHALL 调用现有接口，并展示服务端返回的拒绝原因。前端 SHALL NOT 自行提交 `class_id`。

#### Scenario: 学生上传讲义
- **WHEN** 学生在 `/materials/new` 提交讲义
- **THEN** 页面展示服务端的权限不足，不显示上传成功

#### Scenario: 其他班级看不到本班讲义
- **WHEN** A 班教师上传一份新讲义后，B 班学生打开讲义列表
- **THEN** 列表中不出现该讲义标题

### Requirement: 端到端测试不得默认访问公网
Playwright SHALL 在缺少 `PLAYWRIGHT_BASE_URL` 时立即失败。非本机地址 SHALL 再要求显式确认隔离环境。测试口令 SHALL 只来自环境变量。

#### Scenario: 未指定地址
- **WHEN** 运行端到端测试时没有 `PLAYWRIGHT_BASE_URL`
- **THEN** 测试在打开浏览器前失败，并且不会请求任何默认公网主机
