<template>
  <el-container>
    <el-header>
      <div class="header-content">
        <h1>ChatSQL - 自然语言转SQL</h1>
      </div>
    </el-header>
    <el-main>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card title="数据库连接配置" shadow="hover">
            <el-form ref="dbForm" :model="dbConfig" label-width="100px">
              <el-form-item label="数据库类型">
                <el-select v-model="dbConfig.type" placeholder="请选择数据库类型">
                  <el-option label="MySQL" value="mysql"></el-option>
                  <el-option label="SQL Server" value="sqlserver"></el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="主机地址">
                <el-input v-model="dbConfig.host" placeholder="请输入主机地址"></el-input>
              </el-form-item>
              <el-form-item label="端口号">
                <el-input v-model.number="dbConfig.port" placeholder="请输入端口号"></el-input>
              </el-form-item>
              <el-form-item label="数据库名">
                <el-input v-model="dbConfig.database" placeholder="请输入数据库名"></el-input>
              </el-form-item>
              <el-form-item label="用户名">
                <el-input v-model="dbConfig.username" placeholder="请输入用户名"></el-input>
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="dbConfig.password" type="password" placeholder="请输入密码"></el-input>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="connectDB">连接数据库</el-button>
                <el-button @click="getDBMetadata" :disabled="!isConnected">获取元数据</el-button>
              </el-form-item>
            </el-form>
          </el-card>
          
          <el-card title="Ollama模型设置" shadow="hover" style="margin-top: 20px;">
            <el-form ref="ollamaForm" :model="ollamaConfig" label-width="120px">
              <el-form-item label="模型API链接">
                <el-input v-model="ollamaConfig.apiUrl" placeholder="请输入Ollama API链接"></el-input>
              </el-form-item>
              <el-form-item label="模型名称">
                <el-input v-model="ollamaConfig.modelName" placeholder="请输入模型名称"></el-input>
              </el-form-item>
              <el-form-item label="温度">
                <el-slider v-model="ollamaConfig.temperature" :min="0" :max="1" :step="0.1"></el-slider>
              </el-form-item>
              <el-form-item label="最大令牌数">
                <el-input-number v-model="ollamaConfig.maxTokens" :min="100" :max="10000" :step="100"></el-input-number>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="saveOllamaConfig">保存配置</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card title="自然语言查询" shadow="hover">
            <el-form ref="queryForm" :model="queryData" label-width="100px">
              <el-form-item label="输入查询">
                <el-input
                  v-model="queryData.question"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入自然语言查询"
                ></el-input>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="generateSQL" :disabled="!isConnected">生成SQL</el-button>
                <el-button @click="executeSQL" :disabled="!generatedSQL">执行SQL</el-button>
                <el-button @click="resetQuery">重置</el-button>
              </el-form-item>
            </el-form>
            
            <el-card title="生成的SQL" shadow="hover" style="margin-top: 20px;">
              <el-input
                v-model="generatedSQL"
                type="textarea"
                :rows="5"
                placeholder="生成的SQL将显示在这里"
                readonly
              ></el-input>
            </el-card>
            
            <el-card title="查询结果" shadow="hover" style="margin-top: 20px;">
              <el-table
                v-if="queryResult.length > 0"
                :data="queryResult"
                border
                stripe
                style="width: 100%;"
              >
                <el-table-column
                  v-for="(column, index) in queryColumns"
                  :key="index"
                  :prop="column"
                  :label="column"
                ></el-table-column>
              </el-table>
              <div v-else class="no-result">
                暂无查询结果
              </div>
            </el-card>
          </el-card>
        </el-col>
      </el-row>
    </el-main>
    <el-footer>
      ChatSQL © 2025
    </el-footer>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 响应式数据
const dbConfig = reactive({
  type: 'mysql',
  host: 'localhost',
  port: 3306,
  database: '',
  username: 'root',
  password: ''
})

const ollamaConfig = reactive({
  apiUrl: 'http://localhost:11434',
  modelName: 'llama3',
  temperature: 0.7,
  maxTokens: 1000
})

const queryData = reactive({
  question: ''
})

const generatedSQL = ref('')
const queryResult = ref([])
const queryColumns = ref([])
const isConnected = ref(false)

// 方法
const connectDB = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/db/connect', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(dbConfig)
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        isConnected.value = true
        ElMessage.success('数据库连接成功')
      } else {
        ElMessage.error(data.message || '数据库连接失败')
      }
    } else {
      ElMessage.error('服务器响应错误')
    }
  } catch (error) {
    console.error('连接数据库时出错:', error)
    ElMessage.error('连接数据库时出错，请检查后端服务是否运行')
  }
}

const getDBMetadata = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/db/metadata')
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        ElMessage.success('元数据获取成功')
        // 这里可以处理元数据，比如显示表结构
        console.log('数据库元数据:', data.data)
      } else {
        ElMessage.error(data.message || '元数据获取失败')
      }
    } else {
      ElMessage.error('服务器响应错误')
    }
  } catch (error) {
    console.error('获取元数据时出错:', error)
    ElMessage.error('获取元数据时出错，请检查后端服务是否运行')
  }
}

const saveOllamaConfig = () => {
  // 这里可以将配置保存到本地存储
  localStorage.setItem('ollamaConfig', JSON.stringify(ollamaConfig))
  ElMessage.success('Ollama配置保存成功')
}

const generateSQL = async () => {
  if (!queryData.question.trim()) {
    ElMessage.warning('请输入自然语言查询')
    return
  }
  
  try {
    const response = await fetch('http://localhost:8000/api/sql/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question: queryData.question,
        modelConfig: ollamaConfig
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        generatedSQL.value = data.data.sql
        ElMessage.success('SQL生成成功')
      } else {
        ElMessage.error(data.message || 'SQL生成失败')
      }
    } else {
      ElMessage.error('服务器响应错误')
    }
  } catch (error) {
    console.error('生成SQL时出错:', error)
    ElMessage.error('生成SQL时出错，请检查后端服务是否运行')
  }
}

const executeSQL = async () => {
  if (!generatedSQL.value.trim()) {
    ElMessage.warning('请先生成SQL')
    return
  }
  
  try {
    const response = await fetch('http://localhost:8000/api/sql/execute', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        sql: generatedSQL.value
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        queryResult.value = data.data.rows
        queryColumns.value = data.data.columns
        ElMessage.success('SQL执行成功')
      } else {
        ElMessage.error(data.message || 'SQL执行失败')
      }
    } else {
      ElMessage.error('服务器响应错误')
    }
  } catch (error) {
    console.error('执行SQL时出错:', error)
    ElMessage.error('执行SQL时出错，请检查后端服务是否运行')
  }
}

const resetQuery = () => {
  queryData.question = ''
  generatedSQL.value = ''
  queryResult.value = []
  queryColumns.value = []
}

// 页面加载时从本地存储恢复Ollama配置
onMounted(() => {
  const savedConfig = localStorage.getItem('ollamaConfig')
  if (savedConfig) {
    Object.assign(ollamaConfig, JSON.parse(savedConfig))
  }
})
</script>

<style scoped>
.header-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.header-content h1 {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.no-result {
  text-align: center;
  padding: 20px;
  color: #909399;
}
</style>