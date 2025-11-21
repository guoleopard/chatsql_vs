# ChatSQL - 自然语言转SQL项目

一个基于Vue3 + ElementPlus和Python + FastAPI的自然语言转SQL项目，支持MySQL和SQL Server数据库。

## 项目结构

```
ChatSQL/
├── ChatSQL_Frontend/          # 前端项目
│   ├── src/
│   │   ├── App.vue           # 主应用组件
│   │   ├── main.js           # 应用入口
│   │   └── style.css         # 全局样式
│   ├── index.html            # HTML模板
│   ├── package.json          # 前端依赖
│   └── vite.config.js        # Vite配置
├── ChatSQL_Backend/           # 后端项目
│   ├── main.py               # 主应用文件
│   ├── .env                  # 环境变量
│   ├── venv/                 # Python虚拟环境
│   └── chroma_db/            # ChromaDB向量数据库存储
└── README.md                 # 项目说明文档
```

## 功能特性

### 前端功能
- 数据库连接配置（支持MySQL、SQL Server）
- Ollama模型设置（模型名称、温度、最大令牌数）
- 连接数据库并获取元数据
- 自然语言输入框
- 执行查询并显示结果
- 显示生成的SQL语句

### 后端功能
- FastAPI服务
- 数据库连接管理
- 数据库元数据读取
- 向量数据库存储元数据（ChromaDB）
- Ollama模型集成
- 自然语言转SQL
- SQL执行与结果返回

## 环境要求

- Python 3.8+
- Node.js 16+
- Ollama（已安装并运行）
- MySQL或SQL Server数据库

## 安装与运行

### 1. 启动Ollama

```bash
ollama serve
```

### 2. 运行后端

```bash
cd ChatSQL_Backend
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py
```

后端服务将在 http://localhost:8000 启动

### 3. 运行前端

```bash
cd ChatSQL_Frontend
npm install
npm run dev
```

前端服务将在 http://localhost:5173 启动

## 使用说明

1. 在前端配置数据库连接信息
2. 点击"连接数据库"按钮
3. 配置Ollama模型参数（可选）
4. 在自然语言输入框中输入查询请求
5. 点击"执行查询"按钮
6. 查看生成的SQL语句和查询结果

## API接口

### 连接数据库
```
POST /connect-db
```

### 自然语言转SQL
```
POST /nl-to-sql
```

### 执行SQL
```
POST /execute-sql
```

### 自然语言查询（完整流程）
```
POST /nl-query
```

## 技术栈

### 前端
- Vue 3
- Element Plus
- Axios
- Vite

### 后端
- FastAPI
- Uvicorn
- SQLAlchemy
- PyMySQL
- python-dotenv
- Ollama
- ChromaDB

## 注意事项

1. 确保Ollama服务已启动
2. 确保数据库服务可访问
3. 第一次连接数据库时会将元数据存储到向量数据库
4. 向量数据库文件存储在 `ChatSQL_Backend/chroma_db/` 目录下