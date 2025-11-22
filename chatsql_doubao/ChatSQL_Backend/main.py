from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlalchemy
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import ollama
import os
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="ChatSQL Backend", version="1.0")

# Database connection
db_engine: Optional[sqlalchemy.engine.Engine] = None

# ChromaDB setup
chroma_client = chromadb.Client(Settings(persist_directory="chroma_db"))
chroma_collection = chroma_client.create_collection(name="db_metadata", get_or_create=True)

# Pydantic models
class DBConfig(BaseModel):
    type: str
    host: str
    port: int
    database: str
    username: str
    password: str

class ModelConfig(BaseModel):
    apiUrl: str
    modelName: str
    temperature: float
    maxTokens: int

class GenerateSQLRequest(BaseModel):
    question: str
    modelConfig: ModelConfig

class ExecuteSQLRequest(BaseModel):
    sql: str

# Helper functions
def get_db_connection_url(config: DBConfig) -> str:
    if config.type == "mysql":
        return f"mysql+pymysql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
    elif config.type == "sqlserver":
        return f"mssql+pymssql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
    else:
        raise ValueError("Unsupported database type")

# API endpoints
@app.post("/api/db/connect")
async def connect_db(config: DBConfig):
    global db_engine
    try:
        # Create database engine
        db_url = get_db_connection_url(config)
        db_engine = create_engine(db_url)
        
        # Test connection
        with db_engine.connect():
            pass
        
        return {"success": True, "message": "Database connected successfully"}
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}
    except ValueError as e:
        return {"success": False, "message": str(e)}

@app.get("/api/db/metadata")
async def get_db_metadata():
    if not db_engine:
        return {"success": False, "message": "No database connection established"}
    
    try:
        # Get database metadata
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        
        metadata = []
        for table in tables:
            columns = inspector.get_columns(table)
            table_info = {
                "table": table,
                "columns": [{"name": col["name"], "type": str(col["type"])} for col in columns]
            }
            metadata.append(table_info)
        
        # Save metadata to ChromaDB
        chroma_collection.add(
            documents=[str(info) for info in metadata],
            metadatas=[{"table": table} for table in tables],
            ids=[f"table_{i}" for i in range(len(tables))]
        )
        
        return {"success": True, "data": metadata}
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

@app.post("/api/sql/generate")
async def generate_sql(request: GenerateSQLRequest):
    if not db_engine:
        return {"success": False, "message": "No database connection established"}
    
    try:
        # Get database metadata
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        
        # Prepare context for the model
        context = "Database tables and columns:\n"
        for table in tables:
            columns = inspector.get_columns(table)
            context += f"Table: {table}\n"
            context += "Columns:\n"
            for col in columns:
                context += f"  - {col['name']} ({col['type']})\n"
        
        # Generate SQL using Ollama
        ollama_response = ollama.generate(
            model=request.modelConfig.modelName,
            prompt=f"Generate a SQL query for the following request: '{request.question}'\n\nDatabase schema:\n{context}\n\nSQL query:",
            temperature=request.modelConfig.temperature,
            max_tokens=request.modelConfig.maxTokens
        )
        
        sql = ollama_response["response"].strip()
        
        return {"success": True, "data": {"sql": sql}}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/sql/execute")
async def execute_sql(request: ExecuteSQLRequest):
    if not db_engine:
        return {"success": False, "message": "No database connection established"}
    
    try:
        # Execute SQL query
        with db_engine.connect() as connection:
            result = connection.execute(text(request.sql))
            
            # Get columns
            columns = result.keys()
            
            # Get rows
            rows = result.fetchall()
            
            # Convert rows to dictionaries
            rows_dict = [{col: row[i] for i, col in enumerate(columns)} for row in rows]
            
            return {
                "success": True, 
                "data": {
                    "rows": rows_dict,
                    "columns": list(columns)
                }
            }
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
