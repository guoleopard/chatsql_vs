import sqlalchemy as sa
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.engine import Engine
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.connection_info: Optional[Dict[str, Any]] = None
        
    def connect(self, config: Dict[str, Any]) -> bool:
        try:
            db_type = config.get('db_type', 'mysql')
            host = config.get('host', 'localhost')
            port = config.get('port', '3306')
            username = config.get('username', '')
            password = config.get('password', '')
            database = config.get('database', '')
            
            if db_type == 'mysql':
                connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            elif db_type == 'sqlserver':
                connection_string = f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
            
            self.engine = create_engine(connection_string)
            
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            self.connection_info = config
            logger.info(f"Successfully connected to {db_type} database: {database}")
            return True
            
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False
    
    def get_database_metadata(self) -> Dict[str, Any]:
        if not self.engine:
            raise Exception("Database not connected")
        
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            
            inspector = inspect(self.engine)
            
            tables_info = {}
            for table_name in inspector.get_table_names():
                columns = []
                for column in inspector.get_columns(table_name):
                    columns.append({
                        'name': column['name'],
                        'type': str(column['type']),
                        'nullable': column['nullable'],
                        'default': str(column['default']) if column['default'] else None
                    })
                
                foreign_keys = []
                for fk in inspector.get_foreign_keys(table_name):
                    foreign_keys.append({
                        'column': fk['constrained_columns'],
                        'referenced_table': fk['referred_table'],
                        'referenced_column': fk['referred_columns']
                    })
                
                tables_info[table_name] = {
                    'columns': columns,
                    'foreign_keys': foreign_keys,
                    'primary_key': inspector.get_pk_constraint(table_name)['constrained_columns']
                }
            
            db_metadata = {
                'database': self.connection_info.get('database', ''),
                'db_type': self.connection_info.get('db_type', ''),
                'tables': tables_info,
                'table_count': len(tables_info)
            }
            
            logger.info(f"Retrieved metadata for {len(tables_info)} tables")
            return db_metadata
            
        except Exception as e:
            logger.error(f"Failed to get database metadata: {str(e)}")
            raise Exception(f"Failed to get database metadata: {str(e)}")
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        if not self.engine:
            raise Exception("Database not connected")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = list(result.keys())
                    
                    data = []
                    for row in rows:
                        data.append(dict(zip(columns, row)))
                    
                    return {
                        'data': data,
                        'columns': columns,
                        'row_count': len(data)
                    }
                else:
                    conn.commit()
                    return {
                        'data': [],
                        'columns': [],
                        'row_count': result.rowcount,
                        'message': f"Query executed successfully. {result.rowcount} rows affected."
                    }
                    
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise Exception(f"Query execution failed: {str(e)}")
    
    def test_connection(self) -> bool:
        if not self.engine:
            return False
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def disconnect(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.connection_info = None
            logger.info("Database connection closed")