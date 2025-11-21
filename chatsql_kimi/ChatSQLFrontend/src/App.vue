<template>
  <div id="app">
    <el-container>
      <el-header>
        <h1>ChatSQL - 自然语言转SQL</h1>
      </el-header>
      
      <el-main>
        <el-row :gutter="20">
          <!-- 数据库连接配置 -->
          <el-col :span="8">
            <el-card>
              <template #header>
                <span>数据库连接配置</span>
              </template>
              <el-form :model="dbConfig" label-width="100px">
                <el-form-item label="数据库类型">
                  <el-select v-model="dbConfig.db_type" placeholder="选择数据库类型">
                    <el-option label="MySQL" value="mysql"></el-option>
                    <el-option label="SQL Server" value="sqlserver"></el-option>
                  </el-select>
                </el-form-item>
                <el-form-item label="主机地址">
                  <el-input v-model="dbConfig.host" placeholder="localhost"></el-input>
                </el-form-item>
                <el-form-item label="端口">
                  <el-input v-model="dbConfig.port" placeholder="3306"></el-input>
                </el-form-item>
                <el-form-item label="用户名">
                  <el-input v-model="dbConfig.username" placeholder="root"></el-input>
                </el-form-item>
                <el-form-item label="密码">
                  <el-input v-model="dbConfig.password" type="password"></el-input>
                </el-form-item>
                <el-form-item label="数据库名">
                  <el-input v-model="dbConfig.database" placeholder="数据库名称"></el-input>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="connectDatabase" :loading="connecting">
                    连接数据库
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>

          <!-- Ollama模型配置 -->
          <el-col :span="8">
            <el-card>
              <template #header>
                <span>Ollama模型设置</span>
              </template>
              <el-form :model="ollamaConfig" label-width="120px">
                <el-form-item label="模型API链接">
                  <el-input v-model="ollamaConfig.model_url" placeholder="http://localhost:11434/api/generate"></el-input>
                </el-form-item>
                <el-form-item label="模型名称">
                  <el-input v-model="ollamaConfig.model" placeholder="llama2"></el-input>
                </el-form-item>
                <el-form-item label="温度">
                  <el-slider v-model="ollamaConfig.temperature" :min="0" :max="1" :step="0.1"></el-slider>
                </el-form-item>
                <el-form-item label="最大令牌数">
                  <el-input-number v-model="ollamaConfig.max_tokens" :min="100" :max="2048"></el-input-number>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>

          <!-- 查询结果 -->
          <el-col :span="8">
            <el-card>
              <template #header>
                <span>连接状态</span>
              </template>
              <el-alert
                v-if="connectionStatus"
                :title="connectionStatus.title"
                :type="connectionStatus.type"
                :description="connectionStatus.message"
                show-icon
              ></el-alert>
            </el-card>
          </el-col>
        </el-row>

        <!-- 自然语言输入和查询 -->
        <el-row :gutter="20" style="margin-top: 20px;">
          <el-col :span="24">
            <el-card>
              <template #header>
                <span>自然语言查询</span>
              </template>
              <el-form>
                <el-form-item label="输入查询">
                  <el-input
                    v-model="naturalLanguage"
                    type="textarea"
                    :rows="3"
                    placeholder="请输入您的查询需求，例如：查询所有用户的姓名和邮箱"
                  ></el-input>
                </el-form-item>
                <el-form-item>
                  <el-button type="success" @click="executeQuery" :loading="querying" :disabled="!isConnected">
                    执行查询
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
        </el-row>

        <!-- 生成的SQL和查询结果 -->
        <el-row :gutter="20" style="margin-top: 20px;" v-if="sqlQuery || queryResult">
          <el-col :span="12">
            <el-card>
              <template #header>
                <span>生成的SQL语句</span>
              </template>
              <el-input
                v-model="sqlQuery"
                type="textarea"
                :rows="6"
                readonly
                placeholder="生成的SQL语句将在这里显示"
              ></el-input>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <template #header>
                <span>查询结果</span>
              </template>
              <div v-if="queryResult">
                <el-table :data="queryResult.data" style="width: 100%" max-height="300">
                  <el-table-column
                    v-for="column in queryResult.columns"
                    :key="column"
                    :prop="column"
                    :label="column"
                  ></el-table-column>
                </el-table>
                <p style="margin-top: 10px; color: #909399;">
                  共 {{ queryResult.row_count }} 行数据
                </p>
              </div>
              <div v-else>
                <p style="color: #909399;">查询结果将在这里显示</p>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'App',
  data() {
    return {
      dbConfig: {
        db_type: 'mysql',
        host: 'localhost',
        port: '3306',
        username: 'root',
        password: '',
        database: ''
      },
      ollamaConfig: {
        model_url: 'http://localhost:11434/api/generate',
        model: 'llama2',
        temperature: 0.7,
        max_tokens: 512
      },
      naturalLanguage: '',
      connecting: false,
      querying: false,
      isConnected: false,
      connectionStatus: null,
      sqlQuery: '',
      queryResult: null
    }
  },
  methods: {
    async connectDatabase() {
      this.connecting = true
      try {
        const response = await axios.post('/api/connect-db', this.dbConfig)
        if (response.data.success) {
          this.isConnected = true
          this.connectionStatus = {
            title: '连接成功',
            type: 'success',
            message: '数据库连接成功，可以开始查询了！'
          }
        } else {
          this.connectionStatus = {
            title: '连接失败',
            type: 'error',
            message: response.data.message || '数据库连接失败'
          }
        }
      } catch (error) {
        this.connectionStatus = {
          title: '连接错误',
          type: 'error',
          message: error.response?.data?.detail || '连接数据库时发生错误'
        }
      } finally {
        this.connecting = false
      }
    },

    async executeQuery() {
      if (!this.naturalLanguage.trim()) {
        this.$message.warning('请输入查询需求')
        return
      }

      this.querying = true
      try {
        const response = await axios.post('/api/nl-query', {
          natural_language: this.naturalLanguage,
          ollama_config: this.ollamaConfig
        })
        
        if (response.data.success) {
          this.sqlQuery = response.data.sql_query
          this.queryResult = response.data.query_result
          this.$message.success('查询执行成功')
        } else {
          this.$message.error(response.data.message || '查询执行失败')
        }
      } catch (error) {
        this.$message.error(error.response?.data?.detail || '执行查询时发生错误')
      } finally {
        this.querying = false
      }
    }
  }
}
</script>