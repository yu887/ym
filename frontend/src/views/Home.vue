<template>
  <div class="home">
    <el-container>
      <el-header>
        <div class="header-left">
          <h2>图书借阅系统</h2>
        </div>
        <div class="header-right">
          <el-badge :value="unreadCount" class="item">
            <el-button @click="showNotifications = true">
              <el-icon><Bell /></el-icon> 通知
            </el-button>
          </el-badge>
          <el-dropdown @command="handleCommand">
            <span class="user-name">{{ user.name }}</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="图书查询" name="books">
            <div class="search-bar">
              <el-input v-model="keyword" placeholder="搜索书名/作者/ISBN" clearable style="width: 300px; margin-right: 10px" />
              <el-select v-model="category" placeholder="选择分类" clearable style="width: 200px; margin-right: 10px">
                <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
              </el-select>
              <el-button type="primary" @click="searchBooks">搜索</el-button>
            </div>
            <el-row :gutter="20" style="margin-top: 20px">
              <el-col v-for="book in books" :key="book.id" :span="6">
                <el-card shadow="hover" class="book-card">
                  <h3>{{ book.title }}</h3>
                  <p>作者: {{ book.author }}</p>
                  <p>分类: {{ book.category }}</p>
                  <p>库存: {{ book.available_quantity }} / {{ book.total_quantity }}</p>
                  <el-button type="primary" @click="borrowBook(book)" :disabled="book.available_quantity <= 0" style="width: 100%; margin-top: 10px">
                    {{ book.available_quantity > 0 ? '申请借阅' : '暂无库存' }}
                  </el-button>
                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>
          <el-tab-pane label="借阅记录" name="records">
            <el-table
              :data="borrowRecords"
              style="width: 100%"
              :table-layout="'fixed'"
              :cell-style="{ padding: '8px 0' }"
              :header-cell-style="{ padding: '8px 0' }"
            >
              <el-table-column prop="title" label="书名" min-width="200" />
              <el-table-column prop="author" label="作者" min-width="120" />
              <el-table-column prop="borrow_date" label="借阅日期" min-width="150" />
              <el-table-column prop="due_date" label="到期日期" min-width="150" />
              <el-table-column prop="return_date" label="归还日期" min-width="150" />
              <el-table-column label="状态" min-width="150">
                <template #default="scope">
                  <div v-if="scope.row.status === 'borrowed' && scope.row.return_requested === 1">
                    <el-tag type="warning">等待管理员确认</el-tag>
                  </div>
                  <div v-else>
                    <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" min-width="150">
                <template #default="scope">
                  <el-button
                    v-if="scope.row.status === 'borrowed' && scope.row.return_requested !== 1"
                    type="primary"
                    size="small"
                    @click="requestReturn(scope.row)"
                  >
                    申请归还
                  </el-button>
                  <el-button
                    v-if="scope.row.status === 'borrowed' && scope.row.return_requested === 1"
                    type="info"
                    size="small"
                    disabled
                  >
                    等待管理员确认
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="我的申请" name="applications">
            <el-table
              :data="myApplications"
              style="width: 100%"
              :table-layout="'fixed'"
              :cell-style="{ padding: '8px 0' }"
              :header-cell-style="{ padding: '8px 0' }"
            >
              <el-table-column label="图书" min-width="200">
                <template #default="scope">
                  {{ scope.row.book_title || '未知图书' }}
                </template>
              </el-table-column>
              <el-table-column prop="application_date" label="申请时间" min-width="180" />
              <el-table-column label="状态" min-width="120">
                <template #default="scope">
                  <el-tag :type="getAppStatusType(scope.row.status)">{{ getAppStatusText(scope.row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="备注" min-width="150">
                <template #default="scope">
                  {{ scope.row.remark || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="scope">
                  <el-button
                    v-if="scope.row.status === 'pending'"
                    type="danger"
                    size="small"
                    @click="cancelApplication(scope.row.id)"
                  >
                    取消申请
                  </el-button>
                  <el-button
                    v-if="scope.row.status !== 'pending'"
                    type="info"
                    size="small"
                    @click="deleteApplication(scope.row.id)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-main>
    </el-container>

    <el-dialog v-model="showChangePassword" title="修改密码" width="400px">
      <el-form :model="passwordForm" label-width="100px">
        <el-form-item label="旧密码">
          <el-input v-model="passwordForm.old_password" type="password" placeholder="请输入旧密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirm_password" type="password" placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePassword = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="showNotifications" title="通知中心" size="400px">
      <div v-if="notifications.length === 0">暂无通知</div>
      <el-timeline v-else>
        <el-timeline-item v-for="notif in notifications" :key="notif.id" :type="notif.is_read ? '' : 'primary'">
          <h4>{{ notif.title }}</h4>
          <p>{{ notif.content }}</p>
          <p style="color: #999; font-size: 12px">{{ notif.created_at }}</p>
          <el-button v-if="!notif.is_read" size="small" @click="markRead(notif.id)">标为已读</el-button>
          <el-button size="small" type="danger" @click="deleteNotification(notif.id)">删除</el-button>
        </el-timeline-item>
      </el-timeline>
    </el-drawer>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import api from '../utils/api'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

export default {
  name: 'Home',
  setup() {
    const router = useRouter()
    const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
    const activeTab = ref('books')
    const keyword = ref('')
    const category = ref('')
    const categories = ref([])
    const books = ref([])
    const borrowRecords = ref([])
    const notifications = ref([])
    const myApplications = ref([])
    const showNotifications = ref(false)
    const unreadCount = ref(0)

    // 修改密码
    const showChangePassword = ref(false)
    const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

    const fetchCategories = async () => {
      try {
        const res = await api.get('/categories')
        categories.value = res.data
      } catch (err) {
        // 静默失败
      }
    }

    const searchBooks = async () => {
      try {
        const res = await api.get('/books', {
          params: { keyword: keyword.value, category: category.value }
        })
        books.value = res.data
      } catch (err) {
        ElMessage.error('获取图书列表失败')
      }
    }

    const borrowBook = async (book) => {
      try {
        await api.post('/borrow-applications', { book_id: book.id })
        ElMessage.success('借阅申请已提交，请等待管理员审核')
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '申请失败')
      }
    }

    const getBorrowRecords = async () => {
        try {
            const res = await api.get('/borrow-records')
            borrowRecords.value = res.data
        } catch (err) {
            ElMessage.error('获取借阅记录失败')
        }
    }

    const requestReturn = async (record) => {
        try {
            await api.post(`/borrow-records/${record.id}/request-return`)
            ElMessage.success('归还申请已提交，请等待管理员确认')
            getBorrowRecords()
        } catch (err) {
            ElMessage.error(err.response?.data?.message || '申请失败')
        }
    }

    const getNotifications = async () => {
      try {
        const res = await api.get('/notifications')
        notifications.value = res.data
        unreadCount.value = res.data.filter(n => !n.is_read).length
      } catch (err) {
        ElMessage.error('获取通知失败')
      }
    }

    const markRead = async (notifId) => {
      try {
        await api.put(`/notifications/${notifId}/read`)
        getNotifications()
      } catch (err) {
        ElMessage.error('操作失败')
      }
    }

    const deleteNotification = async (notifId) => {
      try {
        await api.delete(`/notifications/${notifId}`)
        ElMessage.success('通知已删除')
        getNotifications()
      } catch (err) {
        ElMessage.error('删除失败')
      }
    }

    const getMyApplications = async () => {
      try {
        const res = await api.get('/borrow-applications')
        myApplications.value = res.data
      } catch (err) {
        ElMessage.error('获取申请列表失败')
      }
    }

    const cancelApplication = async (appId) => {
      try {
        await api.delete(`/borrow-applications/${appId}`)
        ElMessage.success('申请已取消')
        getMyApplications()
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '取消失败')
      }
    }

    const deleteApplication = async (appId) => {
      try {
        await api.delete(`/borrow-applications/${appId}`)
        ElMessage.success('已删除')
        getMyApplications()
      } catch (err) {
        ElMessage.error('删除失败')
      }
    }

    const getAppStatusText = (status) => {
      const map = { pending: '待审批', approved: '已通过', rejected: '已拒绝' }
      return map[status] || status
    }

    const getAppStatusType = (status) => {
      const map = { pending: 'warning', approved: 'success', rejected: 'danger' }
      return map[status] || ''
    }

    const handleChangePassword = async () => {
      if (!passwordForm.old_password || !passwordForm.new_password) {
        ElMessage.warning('请填写完整信息')
        return
      }
      if (passwordForm.new_password !== passwordForm.confirm_password) {
        ElMessage.warning('两次输入的新密码不一致')
        return
      }
      if (passwordForm.new_password.length < 6) {
        ElMessage.warning('新密码长度不能少于6位')
        return
      }
      try {
        await api.put('/change-password', {
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password
        })
        ElMessage.success('密码修改成功，请重新登录')
        showChangePassword.value = false
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        router.push('/login')
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '修改失败')
      }
    }

    const getStatusText = (status) => {
      const map = { borrowed: '借阅中', returned: '已归还', overdue: '已逾期' }
      return map[status] || status
    }

    const getStatusType = (status) => {
      const map = { borrowed: 'primary', returned: 'success', overdue: 'danger' }
      return map[status] || ''
    }

    const handleCommand = (command) => {
      if (command === 'logout') {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        router.push('/login')
      } else if (command === 'changePassword') {
        passwordForm.old_password = ''
        passwordForm.new_password = ''
        passwordForm.confirm_password = ''
        showChangePassword.value = true
      }
    }

    onMounted(() => {
      fetchCategories()
      searchBooks()
      getBorrowRecords()
      getNotifications()
      getMyApplications()
    })

    return {
        user,
        activeTab,
        keyword,
        category,
        categories,
        books,
        borrowRecords,
        myApplications,
        notifications,
        showNotifications,
        unreadCount,
        showChangePassword,
        passwordForm,
        searchBooks,
        borrowBook,
        getBorrowRecords,
        getNotifications,
        getMyApplications,
        cancelApplication,
        deleteApplication,
        deleteNotification,
        markRead,
        getStatusText,
        getStatusType,
        getAppStatusText,
        getAppStatusType,
        handleCommand,
        requestReturn,
        handleChangePassword
    }
  }
}
</script>

<style scoped>
.el-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.header-left h2 {
  margin: 0;
}
.user-name {
  cursor: pointer;
  margin-left: 20px;
}
.search-bar {
  margin-bottom: 20px;
}
.book-card {
  margin-bottom: 20px;
}
.book-card h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
}
.book-card p {
  margin: 5px 0;
  font-size: 14px;
  color: #666;
}
</style>
