from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

from database import DatabaseManager, get_db_manager
from ollama_client import OllamaClient
from vector_store import VectorStore

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChatSQL Backend",
    description="自然语言转SQL的后端API服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DatabaseConfig(BaseModel):
    type: str
    host: str
    port: int
    database: str
    username: str
    password: str

class OllamaConfig(BaseModel):
    apiUrl: str = "http://localhost:11434"
    modelName: str = "llama3"
    temperature: float = 0.7
    maxTokens: int = 1000

class SQLGenerationRequest(BaseModel):
    question: str
    modelConfig: OllamaConfig

class SQLExecutionRequest(BaseModel):
    sql: str

class Response(BaseModel):
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None
# 初始化服务
db_manager = DatabaseManager()
ollama_client = OllamaClient()
vector_store = VectorStore()

@app.get("/")
async def root():
    return {"message": "ChatSQL Backend is running", "timestamp": datetime.now()}

@app.post("/api/db/connect", response_model=Response)
async def connect_database(config: DatabaseConfig):
    """连接数据库"""
    try:
        # 测试数据库连接
        connection_info = await db_manager.test_connection(config.dict())
        
        # 获取数据库元数据
        metadata = await db_manager.get_database_metadata(config.dict())
        
        # 存储元数据到向量数据库
        await vector_store.store_metadata(metadata)
        
        return Response(
            success=True,
            message="数据库连接成功",
            data={
                "connection_info": connection_info,
                "metadata": metadata
            }
        )
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return Response(
            success=False,
            message=f"数据库连接失败: {str(e)}"
        )

@app.get("/api/db/metadata", response_model=Response)
async def get_database_metadata():
    try:
        metadata = await db_manager.get_metadata()
        return Response(
            success=True,
            message="元数据获取成功",
            data={"metadata": metadata}
        )
    except Exception as e:
        logger.error(f"获取元数据失败: {str(e)}")
        return Response(
            success=False,
            message=f"获取元数据失败: {str(e)}"
        )

@app.post("/api/sql/generate", response_model=Response)
async def generate_sql(request: SQLGenerationRequest):
    try:
        if not db_manager.is_connected():
            return Response(
                success=False,
                message="请先连接数据库"
            )
        
        # 获取相关的数据库元数据
        relevant_metadata = await vector_store.search_relevant_metadata(request.question)
        
        # 使用Ollama生成SQL
        sql = await ollama_client.generate_sql(
            question=request.question,
            metadata=relevant_metadata,
            model_config=request.modelConfig.dict()
        )
        
        return Response(
            success=True,
            message="SQL生成成功",
            data={"sql": sql}
        )
    except Exception as e:
        logger.error(f"生成SQL失败: {str(e)}")
        return Response(
            success=False,
            message=f"生成SQL失败: {str(e)}"
        )

@app.post("/api/sql/execute", response_model=Response)
async def execute_sql(request: SQLExecutionRequest):
    try:
        if not db_manager.is_connected():
            return Response(
                success=False,
                message="请先连接数据库"
            )
        
        # 执行SQL查询
        result = await db_manager.execute_sql(request.sql)
        
        return Response(
            success=True,
            message="SQL执行成功",
            data=result
        )
    except Exception as e:
        logger.error(f"执行SQL失败: {str(e)}")
        return Response(
            success=False,
            message=f"执行SQL失败: {str(e)}"
        )

@app.post("/api/nl-query", response_model=Response)
async def natural_language_query(request: SQLGenerationRequest):
    try:
        if not db_manager.is_connected():
            return Response(
                success=False,
                message="请先连接数据库"
            )
        
        # 获取相关的数据库元数据
        relevant_metadata = await vector_store.search_relevant_metadata(request.question)
        
        # 使用Ollama生成SQL
        sql = await ollama_client.generate_sql(
            question=request.question,
            metadata=relevant_metadata,
            model_config=request.modelConfig.dict()
        )
        
        # 执行生成的SQL
        result = await db_manager.execute_sql(sql)
        
        return Response(
            success=True,
            message="自然语言查询成功",
            data={
                "sql": sql,
                "result": result
            }
        )
    except Exception as e:
        logger.error(f"自然语言查询失败: {str(e)}")
        return Response(
            success=False,
            message=f"自然语言查询失败: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )