from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import asyncio
from threading import Thread

from database_manager import DatabaseManager
from ollama_client import OllamaClient
from vector_store import VectorStore

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])

db_manager = DatabaseManager()
ollama_client = OllamaClient()
vector_store = VectorStore()

@app.route("/")
def root():
    return {"message": "ChatSQL Backend is running", "timestamp": datetime.now()}

@app.route("/api/connect-db", methods=["POST"])
def connect_database():
    try:
        config = request.json
        logger.info(f"Attempting to connect to {config.get('db_type')} database")
        
        success = db_manager.connect(config)
        if not success:
            return jsonify({"success": False, "message": "数据库连接失败"})
        
        metadata = db_manager.get_database_metadata()
        if metadata:
            vector_store.store_metadata(metadata)
            logger.info("Database metadata stored in vector store")
        
        return jsonify({"success": True, "message": "数据库连接成功"})
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return jsonify({"error": f"数据库连接错误: {str(e)}"}), 500

@app.route("/api/nl-to-sql", methods=["POST"])
def natural_language_to_sql():
    try:
        request_data = request.json
        natural_language = request_data.get("natural_language", "")
        ollama_config = request_data.get("ollama_config", {})
        
        logger.info(f"Converting natural language to SQL: {natural_language}")
        
        metadata = vector_store.get_relevant_metadata(natural_language)
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sql_query = loop.run_until_complete(
            ollama_client.nl_to_sql(natural_language, metadata, ollama_config)
        )
        loop.close()
        
        return jsonify({"success": True, "sql_query": sql_query})
        
    except Exception as e:
        logger.error(f"NL to SQL conversion error: {str(e)}")
        return jsonify({"error": f"自然语言转SQL错误: {str(e)}"}), 500

@app.route("/api/execute-sql", methods=["POST"])
def execute_sql():
    try:
        request_data = request.json
        sql_query = request_data.get("sql_query", "")
        logger.info(f"Executing SQL query: {sql_query}")
        
        result = db_manager.execute_query(sql_query)
        
        return jsonify({
            "success": True,
            "query_result": result
        })
        
    except Exception as e:
        logger.error(f"SQL execution error: {str(e)}")
        return jsonify({"error": f"SQL执行错误: {str(e)}"}), 500

@app.route("/api/nl-query", methods=["POST"])
def natural_language_query():
    try:
        request_data = request.json
        natural_language = request_data.get("natural_language", "")
        ollama_config = request_data.get("ollama_config", {})
        
        logger.info(f"Processing natural language query: {natural_language}")
        
        metadata = vector_store.get_relevant_metadata(natural_language)
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sql_query = loop.run_until_complete(
            ollama_client.nl_to_sql(natural_language, metadata, ollama_config)
        )
        loop.close()
        
        if not sql_query:
            return jsonify({
                "success": False,
                "message": "无法生成SQL查询"
            })
        
        query_result = db_manager.execute_query(sql_query)
        
        return jsonify({
            "success": True,
            "sql_query": sql_query,
            "query_result": query_result
        })
        
    except Exception as e:
        logger.error(f"Natural language query error: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"查询执行错误: {str(e)}"
        })

@app.route("/api/health")
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)