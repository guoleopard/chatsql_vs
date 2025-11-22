import json
import logging
from typing import Dict, Any, List, Optional
import os
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = "chroma_db"):
        self.persist_directory = persist_directory
        self.metadata_store = {}
        self._ensure_directory()
        self._load_metadata()
    
    def _ensure_directory(self):
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory)
    
    def _load_metadata(self):
        metadata_file = os.path.join(self.persist_directory, "metadata.json")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata_store = json.load(f)
                logger.info(f"Loaded {len(self.metadata_store)} metadata entries")
            except Exception as e:
                logger.error(f"Failed to load metadata: {str(e)}")
                self.metadata_store = {}
    
    def store_metadata(self, metadata: Dict[str, Any]) -> bool:
        try:
            database = metadata.get('database', 'unknown')
            db_type = metadata.get('db_type', 'unknown')
            tables = metadata.get('tables', {})
            
            metadata_entries = []
            
            for table_name, table_info in tables.items():
                table_description = self._create_table_description(table_name, table_info)
                
                entry = {
                    'id': f"{database}_{table_name}",
                    'type': 'table',
                    'database': database,
                    'db_type': db_type,
                    'table_name': table_name,
                    'description': table_description,
                    'timestamp': datetime.now().isoformat()
                }
                metadata_entries.append(entry)
                
                for column in table_info.get('columns', []):
                    column_description = self._create_column_description(table_name, column)
                    
                    column_entry = {
                        'id': f"{database}_{table_name}_{column['name']}",
                        'type': 'column',
                        'database': database,
                        'db_type': db_type,
                        'table_name': table_name,
                        'column_name': column['name'],
                        'description': column_description,
                        'timestamp': datetime.now().isoformat()
                    }
                    metadata_entries.append(column_entry)
            
            for entry in metadata_entries:
                self.metadata_store[entry['id']] = entry
            
            self._save_metadata()
            
            logger.info(f"Stored metadata for {len(tables)} tables with {len(metadata_entries)} total entries")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store metadata: {str(e)}")
            raise Exception(f"Failed to store metadata: {str(e)}")
    
    def _save_metadata(self):
        try:
            metadata_file = os.path.join(self.persist_directory, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata_store, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {str(e)}")
    
    def get_relevant_metadata(self, query: str, n_results: int = 10) -> Dict[str, Any]:
        try:
            query_lower = query.lower()
            relevant_tables = set()
            relevant_columns = {}
            
            for entry_id, entry in self.metadata_store.items():
                description = entry.get('description', '').lower()
                table_name = entry.get('table_name', '')
                column_name = entry.get('column_name', '')
                
                if (query_lower in description or 
                    any(word in description for word in query_lower.split()) or
                    (table_name and table_name.lower() in query_lower) or
                    (column_name and column_name.lower() in query_lower)):
                    
                    if table_name:
                        relevant_tables.add(table_name)
                        
                        if column_name:
                            if table_name not in relevant_columns:
                                relevant_columns[table_name] = []
                            relevant_columns[table_name].append(column_name)
            
            return {
                'relevant_tables': list(relevant_tables),
                'relevant_columns': relevant_columns,
                'query': query,
                'result_count': len(relevant_tables)
            }
            
        except Exception as e:
            logger.error(f"Failed to get relevant metadata: {str(e)}")
            return {
                'relevant_tables': [],
                'relevant_columns': {},
                'query': query,
                'result_count': 0
            }
    
    def _create_table_description(self, table_name: str, table_info: Dict[str, Any]) -> str:
        columns = table_info.get('columns', [])
        foreign_keys = table_info.get('foreign_keys', [])
        primary_key = table_info.get('primary_key', [])
        
        description = f"Table: {table_name}\n"
        description += f"Primary Key: {', '.join(primary_key) if primary_key else 'None'}\n"
        
        if columns:
            description += "Columns:\n"
            for column in columns:
                col_name = column.get('name', '')
                col_type = column.get('type', '')
                nullable = "NULL" if column.get('nullable', True) else "NOT NULL"
                description += f"  - {col_name} ({col_type}) {nullable}\n"
        
        if foreign_keys:
            description += "Foreign Keys:\n"
            for fk in foreign_keys:
                from_col = ', '.join(fk.get('column', []))
                to_table = fk.get('referenced_table', '')
                to_col = ', '.join(fk.get('referenced_column', []))
                description += f"  - {from_col} -> {to_table}({to_col})\n"
        
        return description.strip()
    
    def _create_column_description(self, table_name: str, column: Dict[str, Any]) -> str:
        col_name = column.get('name', '')
        col_type = column.get('type', '')
        nullable = "nullable" if column.get('nullable', True) else "not nullable"
        default = f" default {column.get('default')}" if column.get('default') else ""
        
        description = f"Column: {col_name} in table {table_name}\n"
        description += f"Type: {col_type}, {nullable}{default}\n"
        description += f"This column belongs to table {table_name}"
        
        return description
    
    def cleanup(self):
        try:
            self.metadata_store.clear()
            metadata_file = os.path.join(self.persist_directory, "metadata.json")
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
            logger.info("Vector store cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup vector store: {str(e)}")
            raise Exception(f"Failed to cleanup vector store: {str(e)}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            count = len(self.metadata_store)
            return {
                'total_documents': count,
                'collection_name': 'database_metadata',
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                'total_documents': 0,
                'collection_name': 'database_metadata',
                'persist_directory': self.persist_directory,
                'error': str(e)
            }