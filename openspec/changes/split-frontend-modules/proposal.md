# 变更：拆分 Nexus 前端模块

## 背景

导入基线把教师和学生的页面集中在 `web/src/App.vue`。Issue #6 要求 `hxflb` 按前端蓝图拆出页面，用 Vue Router 和 Pinia 管理导航与共享状态，并补上只指向隔离环境的 Playwright。浏览器令牌刷新不在本次范围。

## 范围

拆分登录、工作台、讲义、会话、应用、知识缺口、作业、周报、任务和审计页面。刷新后停留在原路由。学生导航不显示教师入口；学生仍可向 `/materials/new` 提交上传，页面展示服务端 403。端到端测试必须显式给出基地址，本机以外的地址还要确认是隔离环境。

## 验收

- `pnpm install --frozen-lockfile` 与 `pnpm run build` 可以通过。
- 未运行隔离栈时，Playwright 记为 NOT RUN，不把设计说明写成通过。
- 不提交 `dist/`、`node_modules/`、`.env`、真实口令或测试产物。
- 不新增后端接口，也不把 `localStorage` 令牌改成未存在的刷新协议。
