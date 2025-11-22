from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime

from database_manager import DatabaseManager
from ollama_client import OllamaClient
from vector_store import VectorStore

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ChatSQL Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_manager = DatabaseManager()
ollama_client = OllamaClient()
vector_store = VectorStore()

@app.get("/")
async def root():
    return {"message": "ChatSQL Backend is running", "timestamp": datetime.now()}

@app.post("/api/connect-db")
async def connect_database(config: Dict[str, Any]):
    try:
        logger.info(f"Attempting to connect to {config.get('db_type')} database")
        
        success = db_manager.connect(config)
        if not success:
            return {"success": False, "message": "数据库连接失败"}
        
        metadata = db_manager.get_database_metadata()
        if metadata:
            vector_store.store_metadata(metadata)
            logger.info("Database metadata stored in vector store")
        
        return {"success": True, "message": "数据库连接成功"}
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库连接错误: {str(e)}")

@app.post("/api/nl-to-sql")
async def natural_language_to_sql(request: Dict[str, Any]):
    try:
        natural_language = request.get("natural_language", "")
        ollama_config = request.get("ollama_config", {})
        
        logger.info(f"Converting natural language to SQL: {natural_language}")
        
        metadata = vector_store.get_relevant_metadata(natural_language)
        
        sql_query = await ollama_client.nl_to_sql(
            natural_language,
            metadata,
            ollama_config
        )
        
        return {"success": True, "sql_query": sql_query}
        
    except Exception as e:
        logger.error(f"NL to SQL conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"自然语言转SQL错误: {str(e)}")

@app.post("/api/execute-sql")
async def execute_sql(request: Dict[str, Any]):
    try:
        sql_query = request.get("sql_query", "")
        logger.info(f"Executing SQL query: {sql_query}")
        
        result = db_manager.execute_query(sql_query)
        
        return {
            "success": True,
            "query_result": result
        }
        
    except Exception as e:
        logger.error(f"SQL execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"SQL执行错误: {str(e)}")

@app.post("/api/nl-query")
async def natural_language_query(request: Dict[str, Any]):
    try:
        natural_language = request.get("natural_language", "")
        ollama_config = request.get("ollama_config", {})
        
        logger.info(f"Processing natural language query: {natural_language}")
        
        metadata = vector_store.get_relevant_metadata(natural_language)
        
        sql_query = await ollama_client.nl_to_sql(
            natural_language,
            metadata,
            ollama_config
        )
        
        if not sql_query:
            return {
                "success": False,
                "message": "无法生成SQL查询"
            }
        
        query_result = db_manager.execute_query(sql_query)
        
        return {
            "success": True,
            "sql_query": sql_query,
            "query_result": query_result
        }
        
    except Exception as e:
        logger.error(f"Natural language query error: {str(e)}")
        return {
            "success": False,
            "message": f"查询执行错误: {str(e)}"
        }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)