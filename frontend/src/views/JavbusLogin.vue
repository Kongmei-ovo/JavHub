<template>
  <div class="javbus-login">
    <h1>JavBus 登录</h1>
    
    <div class="login-tip">
      <p>登录 JavBus 可以获取更多磁力链接和高清资源</p>
      <p>你的登录信息只会保存在本地，不会上传到任何服务器</p>
    </div>

    <div v-if="loading" class="loading">正在登录...</div>
    
    <div v-else-if="loginStatus.logged_in" class="logged-in">
      <p class="success">✅ 已登录 JavBus</p>
      <p>Cookies: {{ loginStatus.cookies.join(', ') }}</p>
      <el-button type="danger" @click="logout">退出登录</el-button>
    </div>
    
    <div v-else class="login-form">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="JavBus 用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="login" :loading="loading">登录</el-button>
        </el-form-item>
      </el-form>
      
      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="success" class="success">{{ success }}</div>
    </div>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'JavbusLogin',
  data() {
    return {
      form: {
        username: '',
        password: ''
      },
      loading: false,
      loginStatus: {
        logged_in: false,
        cookies: []
      },
      error: '',
      success: ''
    }
  },
  mounted() {
    this.checkLoginStatus()
  },
  methods: {
    async checkLoginStatus() {
      try {
        const resp = await api.javbusLoginStatus()
        this.loginStatus = resp.data
      } catch (e) {
        console.error('Failed to check login status:', e)
      }
    },
    async login() {
      if (!this.form.username || !this.form.password) {
        this.error = '请输入用户名和密码'
        return
      }
      
      this.loading = true
      this.error = ''
      this.success = ''
      
      try {
        const resp = await api.javbusLogin(this.form.username, this.form.password)
        if (resp.data.success) {
          this.success = '登录成功！'
          this.checkLoginStatus()
        } else {
          this.error = resp.data.message || '登录失败'
        }
      } catch (e) {
        this.error = '登录失败: ' + (e.response?.data?.detail || e.message)
      } finally {
        this.loading = false
      }
    },
    async logout() {
      try {
        await api.javbusLogout()
        this.loginStatus = { logged_in: false, cookies: [] }
        this.success = '已退出登录'
      } catch (e) {
        this.error = '退出失败'
      }
    }
  }
}
</script>

<style scoped>
.javbus-login {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
}
.login-tip {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
  color: #606266;
}
.login-tip p {
  margin: 5px 0;
  font-size: 14px;
}
.logged-in {
  text-align: center;
  padding: 20px;
  background: #f0f9eb;
  border-radius: 4px;
}
.logged-in .success {
  color: #67c23a;
  font-size: 18px;
  margin-bottom: 10px;
}
.error {
  color: #f56c6c;
  margin-top: 10px;
  padding: 10px;
  background: #fef0f0;
  border-radius: 4px;
}
.success {
  color: #67c23a;
  margin-top: 10px;
  padding: 10px;
  background: #f0f9eb;
  border-radius: 4px;
}
.loading {
  text-align: center;
  padding: 40px;
  color: #909399;
}
</style>
