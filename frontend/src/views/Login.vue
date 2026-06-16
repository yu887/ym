<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>图书借阅系统</h2>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" label-width="80px">
            <el-form-item label="用户名">
              <el-input v-model="loginForm.username" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" @keyup.enter="handleLogin" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleLogin" style="width: 100%">登录</el-button>
            </el-form-item>
          </el-form>
          <div class="tips">
            <p>账号需要在管理员处申请</p>
          </div>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" label-width="80px">
            <el-form-item label="用户名">
              <el-input v-model="registerForm.username" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="registerForm.name" placeholder="请输入姓名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input v-model="registerForm.confirm_password" type="password" placeholder="请再次输入密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleRegister" style="width: 100%">注册</el-button>
            </el-form-item>
          </el-form>
          <div class="tips">
            <p>注册提示：</p>
            <p>用户名和密码不能相同</p>
            <p>密码需要确认输入两次</p>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const activeTab = ref('login')
    const loginForm = reactive({ username: '', password: '' })
    const registerForm = reactive({ username: '', password: '', confirm_password: '', name: '' })

    const handleLogin = async () => {
      if (!loginForm.username || !loginForm.password) {
        ElMessage.warning('请输入用户名和密码')
        return
      }
      try {
        const res = await api.post('/login', loginForm)
        localStorage.setItem('token', res.data.token)
        localStorage.setItem('user', JSON.stringify(res.data.user))
        ElMessage.success('登录成功')
        if (res.data.user.role === 'admin') {
          router.push('/admin')
        } else {
          router.push('/')
        }
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '登录失败')
      }
    }

    const handleRegister = async () => {
      if (!registerForm.username || !registerForm.password) {
        ElMessage.warning('请输入用户名和密码')
        return
      }
      if (registerForm.password !== registerForm.confirm_password) {
        ElMessage.warning('两次输入的密码不一致')
        return
      }
      if (registerForm.username === registerForm.password) {
        ElMessage.warning('用户名和密码不能相同')
        return
      }
      if (registerForm.password.length < 6) {
        ElMessage.warning('密码长度不能少于6位')
        return
      }
      try {
        const res = await api.post('/register', registerForm)
        localStorage.setItem('token', res.data.token)
        localStorage.setItem('user', JSON.stringify(res.data.user))
        ElMessage.success('注册成功')
        router.push('/')
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '注册失败')
      }
    }

    return { activeTab, loginForm, registerForm, handleLogin, handleRegister }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
}
h2 {
  text-align: center;
  margin-bottom: 20px;
}
.tips {
  margin-top: 20px;
  font-size: 12px;
  color: #999;
}
</style>
