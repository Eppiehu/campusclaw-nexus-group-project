<template>
  <div class="login-page">
    <section class="login-intro">
      <div class="eyebrow">静态预览</div>
      <h1>不登录查看<br>登录后的页面。</h1>
      <p>这里的姓名、讲义和成绩都是虚构数据。<br>按钮不会访问服务器。</p>
    </section>
    <section class="login-box">
      <div class="login-form">
        <h2>选择要看的身份</h2>
        <p class="muted">仅本地开发服务器可用，正式构建会回到登录页。</p>
        <router-link class="preview-choice" to="/preview/teacher">教师 · teacher_a · A 班</router-link>
        <router-link class="preview-choice" to="/preview/student">学生 · student_a1 · A 班</router-link>
      </div>
    </section>
  </div>
</template>
