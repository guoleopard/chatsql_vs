from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
import json
import aiomysql
import pyodbc
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

app = FastAPI(title="ChatSQL Backend", version="1.0")

# Database connection pool
DB_POOL = None
DB_METADATA = {}

# ChromaDB initialization
chroma_client = chromadb.PersistentClient(
    path="chroma_db",
    settings=Settings(
        anonymized_telemetry=False
    )
)

# Create embedding function (using default all-MiniLM-L6-v2)
default_embeddings = embedding_functions.DefaultEmbeddingFunction()

# Create or get collection
db_metadata_collection = chroma_client.get_or_create_collection(
    name="database_metadata",
    embedding_function=default_embeddings
)

class DBConfig(BaseModel):
    db_type: str
    host: str
    port: str
    username: str
    password: str
    database: str

class OllamaConfig(BaseModel):
    model_url: str
    model: str
    temperature: float
    max_tokens: int

class NLQueryRequest(BaseModel):
    natural_language: str
    ollama_config: OllamaConfig

class NLToSQLRequest(BaseModel):
    natural_language: str
    ollama_config: OllamaConfig

class ExecuteSQLRequest(BaseModel):
    sql: str

@app.post("/api/connect-db")
async def get_mysql_metadata() -> Dict[str, Any]:
    """Get metadata from MySQL database"""
    if not DB_POOL:
        raise HTTPException(status_code=500, detail="Not connected to MySQL database")
    
    try:
        async with DB_POOL.acquire() as conn:
            async with conn.cursor() as cur:
                # Get tables
                await cur.execute("SHOW TABLES")
                tables = [table[0] for table in await cur.fetchall()]
                
                metadata = {"tables": []}
                
                # Get columns for each table
                for table in tables:
                    await cur.execute(f"DESCRIBE {table}")
                    columns = []
                    for column in await cur.fetchall():
                        columns.append({
                            "name": column[0],
                            "type": column[1],
                            "nullable": column[2] == "YES",
                            "key": column[3],
                            "default": column[4],
                            "extra": column[5]
                        })
                    
                    metadata["tables"].append({
                        "name": table,
                        "columns": columns
                    })
                
                return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get MySQL metadata: {str(e)}")

def get_sqlserver_metadata() -> Dict[str, Any]:
    """Get metadata from SQL Server database"""
    if not DB_POOL or DB_POOL.get("type") != "sqlserver":
        raise HTTPException(status_code=500, detail="Not connected to SQL Server database")
    
    try:
        conn = pyodbc.connect(DB_POOL["conn_str"])
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = [table[0] for table in cursor.fetchall()]
        
        metadata = {"tables": []}
        
        # Get columns for each table
        for table in tables:
            cursor.execute(
                f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY "
                f"FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?",
                (table,)
            )
            columns = []
            for column in cursor.fetchall():
                columns.append({
                    "name": column[0],
                    "type": column[1],
                    "nullable": column[2] == "YES",
                    "default": column[3],
                    "key": column[4] if column[4] else None
                })
            
            metadata["tables"].append({
                "name": table,
                "columns": columns
            })
        
        conn.close()
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SQL Server metadata: {str(e)}")

def store_metadata_in_chromadb(metadata: Dict[str, Any], db_config: DBConfig) -> None:
    """Store database metadata in ChromaDB"""
    try:
        # Prepare documents and metadatas
        documents = []
        metadatas = []
        ids = []
        
        for table in metadata["tables"]:
            # Create document for each table
            doc = f"Table: {table['name']}\n"
            doc += "Columns:\n"
            for col in table["columns"]:
                doc += f"  - {col['name']} ({col['type']})"
                if col["key"] == "PRI":
                    doc += " (Primary Key)"
                if col["nullable"]:
                    doc += " (Nullable)"
                if col["default"]:
                    doc += f" (Default: {col['default']})"
                doc += "\n"
            
            documents.append(doc)
            
            # Add metadata for each table
            metadatas.append({
                "db_type": db_config.db_type,
                "db_host": db_config.host,
                "db_name": db_config.database,
                "table_name": table["name"]
            })
            
            # Create unique ID for each table
            ids.append(f"{db_config.db_type}_{db_config.host}_{db_config.database}_{table['name']}")
        
        # Add documents to ChromaDB
        db_metadata_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store metadata in ChromaDB: {str(e)}")

async def connect_db(config: DBConfig):
    global DB_POOL, DB_METADATA
    try:
        if config.db_type == "mysql":
            DB_POOL = await aiomysql.create_pool(
                host=config.host,
                port=int(config.port),
                user=config.username,
                password=config.password,
                db=config.database,
                autocommit=True,
                minsize=1,
                maxsize=10
            )
            # Get and store metadata
            DB_METADATA = await get_mysql_metadata()
        elif config.db_type == "sqlserver":
            # For SQL Server, we'll use pyodbc (synchronous for now)
            # We'll create a connection string and test the connection
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={config.host},{config.port};"
                f"DATABASE={config.database};"
                f"UID={config.username};"
                f"PWD={config.password}"
            )
            conn = pyodbc.connect(conn_str)
            conn.close()
            DB_POOL = {"type": "sqlserver", "conn_str": conn_str}
            # Get and store metadata
            DB_METADATA = await asyncio.to_thread(get_sqlserver_metadata)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {config.db_type}")
        
        # Store metadata in ChromaDB
        await asyncio.to_thread(store_metadata_in_chromadb, DB_METADATA, config)
        
        return {"success": True, "message": "Database connected successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

async def get_sql_from_ollama(query: str, config: OllamaConfig) -> str:
    try:
        prompt = f"""将以下自然语言查询转换为SQL语句：
        {query}
        
        请只返回SQL语句，不要返回任何其他解释或说明。
        """
        
        payload = {
            "model": config.model,
            "prompt": prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(config.model_url, json=payload) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail="Failed to get SQL from Ollama")
                
                response_json = await response.json()
                return response_json["response"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SQL: {str(e)}")

async def execute_mysql_query(sql: str) -> Dict[str, Any]:
    if not DB_POOL:
        raise HTTPException(status_code=500, detail="Not connected to any database")
    
    try:
        async with DB_POOL.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql)
                columns = [desc[0] for desc in cur.description]
                result = await cur.fetchall()
                
                # Convert result to list of dictionaries
                data = [dict(zip(columns, row)) for row in result]
                
                return {
                    "columns": columns,
                    "data": data,
                    "row_count": len(data)
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

def execute_sqlserver_query(sql: str) -> Dict[str, Any]:
    if not DB_POOL or DB_POOL.get("type") != "sqlserver":
        raise HTTPException(status_code=500, detail="Not connected to SQL Server")
    
    try:
        conn = pyodbc.connect(DB_POOL["conn_str"])
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        result = cursor.fetchall()
        
        # Convert result to list of dictionaries
        data = [dict(zip(columns, row)) for row in result]
        
        conn.close()
        
        return {
            "columns": columns,
            "data": data,
            "row_count": len(data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/api/nl-query")
@app.post("/api/nl-to-sql")
async def nl_to_sql(request: NLToSQLRequest):
    try:
        # Get SQL from Ollama
        sql = await get_sql_from_ollama(request.natural_language, request.ollama_config)
        return {"success": True, "sql_query": sql}
    except Exception as e:
        # Extract detail from HTTPException if available
        detail = e.detail if hasattr(e, "detail") else str(e)
        return {"success": False, "message": detail}

@app.post("/api/execute-sql")
async def execute_sql(request: ExecuteSQLRequest):
    if not DB_POOL:
        raise HTTPException(status_code=500, detail="Not connected to any database")
    
    try:
        # Execute SQL query
        if isinstance(DB_POOL, aiomysql.Pool):
            query_result = await execute_mysql_query(request.sql)
        elif DB_POOL.get("type") == "sqlserver":
            # SQL Server uses synchronous execution
            query_result = await asyncio.to_thread(execute_sqlserver_query, request.sql)
        else:
            raise HTTPException(status_code=500, detail="Unknown database connection type")
        
        return {"success": True, "query_result": query_result}
    except Exception as e:
        # Extract detail from HTTPException if available
        detail = e.detail if hasattr(e, "detail") else str(e)
        return {"success": False, "message": detail}

@app.post("/api/nl-query")
async def nl_query(request: NLQueryRequest):
    if not DB_POOL:
        raise HTTPException(status_code=500, detail="Not connected to any database")
    
    try:
        # Get SQL from Ollama
        sql = await get_sql_from_ollama(request.natural_language, request.ollama_config)
        
        # Execute SQL query
        if isinstance(DB_POOL, aiomysql.Pool):
            query_result = await execute_mysql_query(sql)
        elif DB_POOL.get("type") == "sqlserver":
            # SQL Server uses synchronous execution
            query_result = await asyncio.to_thread(execute_sqlserver_query, sql)
        else:
            raise HTTPException(status_code=500, detail="Unknown database connection type")
        
        return {
            "success": True,
            "sql_query": sql,
            "query_result": query_result
        }
    except Exception as e:
        # Extract detail from HTTPException if available
        detail = e.detail if hasattr(e, "detail") else str(e)
        return {"success": False, "message": detail}

@app.get("/")
async def root():
    return {"message": "ChatSQL Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)