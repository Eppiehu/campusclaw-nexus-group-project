# 设计：路由拆分而不改认证协议

保留现有 `/api/nexus/*` 和 Bearer 令牌。Flask 已经会把未知前端路径回退到 `index.html`，因此使用 Vue Router 的 history 模式，刷新可以由原地址恢复。Pinia 的 `session` 只保存 `/login` 或 `/me` 返回的用户，页面不提交 `class_id`。

教师页面继续对教师隐藏学生导航。学生直接打开这些地址时，页面向对应的教师接口发一次请求，并展示服务端错误。学生上传使用原来的 `POST /materials`，不在浏览器里把 403 改写成成功。

Playwright 不启动内置服务器，也不提供默认主机。`PLAYWRIGHT_BASE_URL` 缺省即失败；主机不是 localhost 或环回地址时，还必须设置 `E2E_CONFIRM_ISOLATED=yes`。口令只从 `E2E_TEACHER_PASSWORD` 和 `E2E_STUDENT_PASSWORD` 读取。

离开会话页时中断尚未完成的 SSE。令牌仍在 `localStorage`，因为服务端还没有可配合的刷新接口。
