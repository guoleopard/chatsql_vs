import asyncio
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import pymysql

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.connection_string = None
        self.db_type = None
        self._connected = False
    
    async def connect(self, config: Dict[str, Any]) -> bool:
        try:
            self.db_type = config.get('type', 'mysql')
            host = config.get('host', 'localhost')
            port = config.get('port', 3306)
            database = config.get('database', '')
            username = config.get('username', '')
            password = config.get('password', '')
            
            if self.db_type == 'mysql':
                self.connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            else:
                raise ValueError(f"不支持的数据库类型: {self.db_type}")
            
            # 测试连接
            test_engine = create_engine(self.connection_string)
            test_engine.connect().close()
            
            # 创建异步引擎
            self.engine = create_async_engine(self.connection_string, echo=True)
            
            self._connected = True
            logger.info(f"成功连接到 {self.db_type} 数据库")
            return True
            
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        return self._connected
    
    async def get_metadata(self) -> Dict[str, Any]:
        if not self._connected or not self.engine:
            raise Exception("数据库未连接")
        
        try:
            metadata = {
                "tables": [],
                "db_type": self.db_type
            }
            
            if self.db_type == 'mysql':
                # 获取表信息
                async with self.engine.connect() as conn:
                    # 获取所有表
                    result = await conn.execute(text("""
                        SELECT TABLE_NAME, TABLE_COMMENT 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = DATABASE()
                    """))
                    tables = result.fetchall()
                    
                    for table in tables:
                        table_name = table[0]
                        table_comment = table[1] or ""
                        
                        # 获取列信息
                        result = await conn.execute(text("""
                            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                            FROM INFORMATION_SCHEMA.COLUMNS 
                            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                            ORDER BY ORDINAL_POSITION
                        """), {"table_name": table_name})
                        columns = result.fetchall()
                        
                        table_info = {
                            "name": table_name,
                            "comment": table_comment,
                            "columns": []
                        }
                        
                        for column in columns:
                            column_info = {
                                "name": column[0],
                                "type": column[1],
                                "nullable": column[2] == "YES",
                                "default": column[3],
                                "comment": column[4] or ""
                            }
                            table_info["columns"].append(column_info)
                        
                        metadata["tables"].append(table_info)
            
            elif self.db_type == 'mysql':
                async with self.engine.connect() as conn:
                    # 获取所有表
                    result = await conn.execute(text("""
                        SELECT TABLE_NAME, TABLE_COMMENT 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = DATABASE()
                    """))
                    tables = result.fetchall()
                    
                    for table in tables:
                        table_name = table[0]
                        table_comment = table[1] or ""
                        
                        # 获取列信息
                        result = await conn.execute(text("""
                            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                            FROM INFORMATION_SCHEMA.COLUMNS 
                            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                            ORDER BY ORDINAL_POSITION
                        """), {"table_name": table_name})
                        columns = result.fetchall()
                        
                        table_info = {
                            "name": table_name,
                            "comment": table_comment,
                            "columns": []
                        }
                        
                        for column in columns:
                            column_info = {
                                "name": column[0],
                                "type": column[1],
                                "nullable": column[2] == "YES",
                                "default": column[3],
                                "comment": column[4] or ""
                            }
                            table_info["columns"].append(column_info)
                        
                        metadata["tables"].append(table_info)
            
            logger.info(f"成功获取数据库元数据，共 {len(metadata['tables'])} 个表")
            return metadata
            
        except Exception as e:
            logger.error(f"获取数据库元数据失败: {str(e)}")
            raise Exception(f"获取数据库元数据失败: {str(e)}")
    
    async def execute_sql(self, sql: str) -> Dict[str, Any]:
        if not self._connected or not self.engine:
            raise Exception("数据库未连接")
        
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text(sql))
                
                if sql.strip().upper().startswith('SELECT'):
                    rows = result.fetchall()
                    columns = list(result.keys())
                    
                    # 转换结果为字典列表
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, column in enumerate(columns):
                            row_dict[column] = row[i]
                        data.append(row_dict)
                    
                    return {
                        "columns": columns,
                        "rows": data,
                        "row_count": len(data)
                    }
                else:
                    # 非查询语句
                    await conn.commit()
                    return {
                        "message": "SQL执行成功",
                        "row_count": result.rowcount
                    }
                    
        except Exception as e:
            logger.error(f"执行SQL失败: {str(e)}")
            raise Exception(f"执行SQL失败: {str(e)}")

# 全局数据库管理器实例
db_manager = DatabaseManager()

async def get_db_manager() -> DatabaseManager:
    return db_manager