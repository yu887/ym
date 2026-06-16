<template>
  <div class="admin">
    <el-container>
      <el-header>
        <div class="header-left">
          <h2>图书借阅系统 - 管理后台</h2>
        </div>
        <div class="header-right">
          <el-badge :value="pendingCount" class="item">
            <el-button type="primary" @click="activeTab = 'applications'">
              <el-icon><Document /></el-icon> 待审批
            </el-button>
          </el-badge>
          <span class="user-name">{{ user.name }}</span>
          <el-button @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="借阅审批" name="applications">
            <div style="margin-bottom: 15px">
              <el-select v-model="appStatusFilter" placeholder="申请状态" @change="getApplications" style="width: 150px">
                <el-option label="待审批" value="pending" />
                <el-option label="已通过" value="approved" />
                <el-option label="已拒绝" value="rejected" />
                <el-option label="全部" value="all" />
              </el-select>
            </div>
            <el-table
              :data="applications" 
              style="width: 100%"
              :table-layout="'fixed'"
              :cell-style="{ padding: '8px 0' }"
              :header-cell-style="{ padding: '8px 0' }"
            >
              <el-table-column label="申请人" min-width="120">
                <template #default="scope">
                  {{ scope.row.display_user_name || scope.row.user_name || scope.row.username || '未知用户' }}
                </template>
              </el-table-column>
              <el-table-column label="图书" min-width="200">
                <template #default="scope">
                  {{ scope.row.display_book_title || scope.row.book_title || scope.row.title || '未知图书' }}
                </template>
              </el-table-column>
              <el-table-column prop="application_date" label="申请时间" min-width="180" />
              <el-table-column label="状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="getAppStatusType(scope.row.status)">{{ getAppStatusText(scope.row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="240">
                <template #default="scope">
                  <el-button v-if="scope.row.status === 'pending'" type="success" size="small" @click="approve(scope.row.id)">通过</el-button>
                  <el-button v-if="scope.row.status === 'pending'" type="danger" size="small" @click="reject(scope.row.id)">拒绝</el-button>
                  <el-button v-if="scope.row.status !== 'pending'" type="info" size="small" @click="deleteApplication(scope.row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="借阅管理" name="records">
            <el-table 
              :data="borrowRecords" 
              style="width: 100%"
              :table-layout="'fixed'"
              :cell-style="{ padding: '8px 0' }"
              :header-cell-style="{ padding: '8px 0' }"
            >
              <el-table-column label="用户" min-width="120">
                <template #default="scope">
                  {{ scope.row.display_user_name || scope.row.user_name || scope.row.username || '未知用户' }}
                </template>
              </el-table-column>
              <el-table-column label="图书" min-width="200">
                <template #default="scope">
                  {{ scope.row.display_book_title || scope.row.book_title || scope.row.title || '未知图书' }}
                </template>
              </el-table-column>
              <el-table-column label="作者" min-width="120">
                <template #default="scope">
                  {{ scope.row.display_book_author || scope.row.book_author || scope.row.author || '未知作者' }}
                </template>
              </el-table-column>
              <el-table-column prop="borrow_date" label="借阅日期" min-width="150" />
              <el-table-column prop="due_date" label="到期日期" min-width="150" />
              <el-table-column prop="return_date" label="归还日期" min-width="150" />
              <el-table-column label="状态" min-width="160">
                <template #default="scope">
                  <div v-if="scope.row.status === 'borrowed' && scope.row.return_requested === 1 && scope.row.admin_confirm_returned !== 1">
                    <el-tag type="warning">等待双方确认</el-tag>
                  </div>
                  <div v-else>
                    <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="240">
                <template #default="scope">
                  <el-button
                    v-if="scope.row.status === 'borrowed' && scope.row.return_requested === 1 && scope.row.admin_confirm_returned !== 1"
                    type="success"
                    size="small"
                    @click="confirmReturn(scope.row.id)"
                  >
                    确认归还
                  </el-button>
                  <el-button
                    v-if="scope.row.status === 'borrowed' && scope.row.return_requested !== 1"
                    type="info"
                    size="small"
                    disabled
                  >
                    等待用户申请
                  </el-button>
                  <el-button
                    v-if="scope.row.status !== 'borrowed'"
                    type="danger"
                    size="small"
                    @click="deleteRecord(scope.row.id)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="图书管理" name="books">
            <div style="margin-bottom: 20px">
              <el-button type="primary" @click="openAddBook">添加图书</el-button>
            </div>
            <el-table 
              :data="books" 
              style="width: 100%"
              :table-layout="'fixed'"
              :cell-style="{ padding: '8px 0' }"
              :header-cell-style="{ padding: '8px 0' }"
            >
              <el-table-column prop="isbn" label="ISBN" min-width="150" />
              <el-table-column prop="title" label="书名" min-width="200" />
              <el-table-column prop="author" label="作者" min-width="120" />
              <el-table-column prop="category" label="分类" min-width="100" />
              <el-table-column prop="available_quantity" label="可借/总数" min-width="120">
                <template #default="scope">
                  {{ scope.row.available_quantity }} / {{ scope.row.total_quantity }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160">
                <template #default="scope">
                  <el-button type="primary" size="small" @click="openEditBook(scope.row)">编辑</el-button>
                  <el-button type="danger" size="small" @click="deleteBook(scope.row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="用户管理" name="users">
            <el-table 
              :data="users" 
              style="width: 100%"
              :table-layout="'fixed'"
              :cell-style="{ padding: '8px 0' }"
              :header-cell-style="{ padding: '8px 0' }"
            >
              <el-table-column prop="username" label="用户名" min-width="120" />
              <el-table-column prop="name" label="姓名" min-width="100" />
              <el-table-column prop="email" label="邮箱" min-width="180" />
              <el-table-column prop="role" label="角色" min-width="100">
                <template #default="scope">
                  <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'primary'">{{ scope.row.role === 'admin' ? '管理员' : '用户' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="注册时间" min-width="180" />
              <el-table-column label="操作" width="160">
                <template #default="scope">
                  <el-button type="primary" size="small" @click="openEditUser(scope.row)">编辑</el-button>
                  <el-button
                    v-if="scope.row.role !== 'admin' && scope.row.id !== user.id"
                    type="danger"
                    size="small"
                    @click="deleteUser(scope.row.id)"
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

    <el-dialog v-model="showBookDialog" :title="isEditingBook ? '编辑图书' : '添加图书'" width="500px">
      <el-form :model="bookForm" label-width="80px">
        <el-form-item label="ISBN">
          <el-input v-model="bookForm.isbn" />
        </el-form-item>
        <el-form-item label="书名">
          <el-input v-model="bookForm.title" />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="bookForm.author" />
        </el-form-item>
        <el-form-item label="出版社">
          <el-input v-model="bookForm.publisher" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="bookForm.category" allow-create filterable clearable placeholder="选择或输入分类">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="bookForm.total_quantity" :min="1" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="bookForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBookDialog = false">取消</el-button>
        <el-button type="primary" @click="saveBook">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showUserDialog" title="编辑用户" width="400px">
      <el-form :model="userForm" label-width="80px">
        <el-form-item label="姓名">
          <el-input v-model="userForm.name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="userForm.phone" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role">
            <el-option label="用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUserDialog = false">取消</el-button>
        <el-button type="primary" @click="saveUser">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import api from '../utils/api'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Admin',
  setup() {
    const router = useRouter()
    const user = ref(JSON.parse(localStorage.getItem('user') || '{}'))
    const activeTab = ref('applications')
    const applications = ref([])
    const borrowRecords = ref([])
    const books = ref([])
    const users = ref([])
    const categories = ref([])
    const pendingCount = ref(0)
    const appStatusFilter = ref('pending')

    // 图书表单（添加/编辑共用）
    const showBookDialog = ref(false)
    const isEditingBook = ref(false)
    const editingBookId = ref(null)
    const bookForm = reactive({
      isbn: '',
      title: '',
      author: '',
      publisher: '',
      category: '',
      total_quantity: 1,
      description: ''
    })

    // 用户编辑
    const showUserDialog = ref(false)
    const editingUserId = ref(null)
    const userForm = reactive({
      name: '',
      email: '',
      phone: '',
      role: 'user'
    })

    const fetchCategories = async () => {
      try {
        const res = await api.get('/categories')
        categories.value = res.data
      } catch (err) {
        // 静默失败
      }
    }

    const getApplications = async () => {
      try {
        const params = {}
        if (appStatusFilter.value !== 'all') {
          params.status = appStatusFilter.value
        }
        const res = await api.get('/admin/borrow-applications', { params })
        applications.value = res.data
        // 单独获取待审批总数（始终保持准确）
        if (appStatusFilter.value !== 'pending') {
          const pendingRes = await api.get('/admin/borrow-applications', { params: { status: 'pending' } })
          pendingCount.value = pendingRes.data.filter(a => a.status === 'pending').length
        } else {
          pendingCount.value = res.data.filter(a => a.status === 'pending').length
        }
      } catch (err) {
        ElMessage.error('获取申请列表失败')
      }
    }

    const getBorrowRecords = async () => {
      try {
        const res = await api.get('/admin/borrow-records')
        borrowRecords.value = res.data
      } catch (err) {
        ElMessage.error('获取借阅记录失败')
      }
    }

    const getBooks = async () => {
      try {
        const res = await api.get('/books')
        books.value = res.data
      } catch (err) {
        ElMessage.error('获取图书列表失败')
      }
    }

    const getUsers = async () => {
      try {
        const res = await api.get('/admin/users')
        users.value = res.data
      } catch (err) {
        ElMessage.error('获取用户列表失败')
      }
    }

    const approve = async (appId) => {
      try {
        await api.post(`/admin/borrow-applications/${appId}/approve`)
        ElMessage.success('审批通过')
        getApplications()
        getBorrowRecords()
        getBooks()
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '操作失败')
      }
    }

    const reject = async (appId) => {
      try {
        const { value: remark } = await ElMessageBox.prompt('请输入拒绝原因', '拒绝申请')
        await api.post(`/admin/borrow-applications/${appId}/reject`, { remark })
        ElMessage.success('已拒绝')
        getApplications()
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error(err.response?.data?.message || '操作失败')
        }
      }
    }

    const confirmReturn = async (recordId) => {
      try {
        await api.post(`/admin/borrow-records/${recordId}/confirm-return`)
        ElMessage.success('确认归还成功！')
        getBorrowRecords()
        getBooks()
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '操作失败')
      }
    }

    // 打开添加图书对话框
    const openAddBook = () => {
      isEditingBook.value = false
      editingBookId.value = null
      bookForm.isbn = ''
      bookForm.title = ''
      bookForm.author = ''
      bookForm.publisher = ''
      bookForm.category = ''
      bookForm.total_quantity = 1
      bookForm.description = ''
      showBookDialog.value = true
    }

    // 打开编辑图书对话框
    const openEditBook = (book) => {
      isEditingBook.value = true
      editingBookId.value = book.id
      bookForm.isbn = book.isbn || ''
      bookForm.title = book.title || ''
      bookForm.author = book.author || ''
      bookForm.publisher = book.publisher || ''
      bookForm.category = book.category || ''
      bookForm.total_quantity = book.total_quantity || 1
      bookForm.description = book.description || ''
      showBookDialog.value = true
    }

    const saveBook = async () => {
      try {
        if (isEditingBook.value) {
          await api.put(`/admin/books/${editingBookId.value}`, bookForm)
          ElMessage.success('更新成功')
        } else {
          await api.post('/admin/books', bookForm)
          ElMessage.success('添加成功')
        }
        showBookDialog.value = false
        getBooks()
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '操作失败')
      }
    }

    const deleteBook = async (bookId) => {
      try {
        await ElMessageBox.confirm('确定要删除此图书吗？', '提示', { type: 'warning' })
        await api.delete(`/admin/books/${bookId}`)
        ElMessage.success('删除成功')
        getBooks()
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    // 打开编辑用户对话框
    const openEditUser = (targetUser) => {
      editingUserId.value = targetUser.id
      userForm.name = targetUser.name || ''
      userForm.email = targetUser.email || ''
      userForm.phone = targetUser.phone || ''
      userForm.role = targetUser.role || 'user'
      showUserDialog.value = true
    }

    const saveUser = async () => {
      try {
        await api.put(`/admin/users/${editingUserId.value}`, userForm)
        ElMessage.success('用户更新成功')
        showUserDialog.value = false
        getUsers()
      } catch (err) {
        ElMessage.error(err.response?.data?.message || '操作失败')
      }
    }

    const deleteUser = async (userId) => {
      try {
        await ElMessageBox.confirm('确定要删除此用户吗？删除后该用户的所有借阅记录将被标记为已归还。', '提示', { type: 'warning' })
        await api.delete(`/admin/users/${userId}`)
        ElMessage.success('删除成功')
        getUsers()
        getBorrowRecords()
        getBooks()
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error(err.response?.data?.message || '删除失败')
        }
      }
    }

    const deleteApplication = async (appId) => {
      try {
        await ElMessageBox.confirm('确定要删除此申请吗？', '提示', { type: 'warning' })
        await api.delete(`/borrow-applications/${appId}`)
        ElMessage.success('删除成功')
        getApplications()
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    const deleteRecord = async (recordId) => {
      try {
        await ElMessageBox.confirm('确定要删除此借阅记录吗？', '提示', { type: 'warning' })
        await api.delete(`/admin/borrow-records/${recordId}`)
        ElMessage.success('删除成功')
        getBorrowRecords()
        getBooks()
      } catch (err) {
        if (err !== 'cancel') {
          ElMessage.error('删除失败')
        }
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

    const getAppStatusText = (status) => {
      const map = { pending: '待审批', approved: '已通过', rejected: '已拒绝' }
      return map[status] || status
    }

    const getAppStatusType = (status) => {
      const map = { pending: 'warning', approved: 'success', rejected: 'danger' }
      return map[status] || ''
    }

    const handleLogout = () => {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
    }

    onMounted(() => {
      fetchCategories()
      getApplications()
      getBorrowRecords()
      getBooks()
      getUsers()
    })

    return {
      user,
      activeTab,
      applications,
      borrowRecords,
      books,
      users,
      categories,
      pendingCount,
      appStatusFilter,
      showBookDialog,
      isEditingBook,
      editingBookId,
      bookForm,
      showUserDialog,
      editingUserId,
      userForm,
      getApplications,
      getBorrowRecords,
      getBooks,
      getUsers,
      approve,
      reject,
      confirmReturn,
      openAddBook,
      openEditBook,
      saveBook,
      deleteBook,
      openEditUser,
      saveUser,
      deleteUser,
      deleteApplication,
      deleteRecord,
      getStatusText,
      getStatusType,
      getAppStatusText,
      getAppStatusType,
      handleLogout
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
  margin-left: 20px;
}
</style>
