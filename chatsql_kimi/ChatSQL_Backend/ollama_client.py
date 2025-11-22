import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.default_model = "llama2"
        self.default_temperature = 0.7
        self.default_max_tokens = 512
    
    async def nl_to_sql(self, natural_language: str, metadata: Dict[str, Any], ollama_config: Dict[str, Any]) -> Optional[str]:
        try:
            model = ollama_config.get('model', self.default_model)
            temperature = ollama_config.get('temperature', self.default_temperature)
            max_tokens = ollama_config.get('max_tokens', self.default_max_tokens)
            model_url = ollama_config.get('model_url', 'http://localhost:11434/api/generate')
            
            prompt = self._build_prompt(natural_language, metadata)
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            logger.info(f"Sending request to Ollama: {model_url}")
            response = requests.post(model_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            sql_query = result.get('response', '').strip()
            
            sql_query = self._clean_sql_query(sql_query)
            
            logger.info(f"Generated SQL query: {sql_query}")
            return sql_query
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {str(e)}")
            raise Exception(f"Ollama API请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response: {str(e)}")
            raise Exception(f"解析Ollama响应失败: {str(e)}")
        except Exception as e:
            logger.error(f"NL to SQL conversion failed: {str(e)}")
            raise Exception(f"自然语言转SQL失败: {str(e)}")
    
    def _build_prompt(self, natural_language: str, metadata: Dict[str, Any]) -> str:
        db_type = metadata.get('db_type', 'MySQL')
        tables = metadata.get('tables', {})
        
        schema_description = self._format_schema_description(tables)
        
        prompt = f"""You are a SQL query generator. Convert the following natural language request into a valid SQL query based on the provided database schema.

Database Type: {db_type}

Database Schema:
{schema_description}

Natural Language Request: {natural_language}

Instructions:
1. Generate only the SQL query, no explanations
2. Use proper SQL syntax for {db_type}
3. Return only the SQL query, nothing else
4. Make sure to use correct table and column names from the schema
5. If the request is unclear, make reasonable assumptions based on the schema

SQL Query:"""
        
        return prompt
    
    def _format_schema_description(self, tables: Dict[str, Any]) -> str:
        description = []
        
        for table_name, table_info in tables.items():
            description.append(f"Table: {table_name}")
            
            columns = table_info.get('columns', [])
            for column in columns:
                col_name = column.get('name', '')
                col_type = column.get('type', '')
                nullable = "NULL" if column.get('nullable', True) else "NOT NULL"
                description.append(f"  - {col_name} ({col_type}) {nullable}")
            
            foreign_keys = table_info.get('foreign_keys', [])
            for fk in foreign_keys:
                from_col = ', '.join(fk.get('column', []))
                to_table = fk.get('referenced_table', '')
                to_col = ', '.join(fk.get('referenced_column', []))
                description.append(f"  - FK: {from_col} -> {to_table}({to_col})")
            
            description.append("")
        
        return '\n'.join(description)
    
    def _clean_sql_query(self, sql_query: str) -> str:
        sql_query = sql_query.strip()
        
        if sql_query.startswith('```sql'):
            sql_query = sql_query[6:]
        if sql_query.startswith('```'):
            sql_query = sql_query[3:]
        if sql_query.endswith('```'):
            sql_query = sql_query[:-3]
        
        sql_query = sql_query.strip()
        
        lines = sql_query.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('--'):
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines)
    
    async def generate_explanation(self, sql_query: str, natural_language: str, ollama_config: Dict[str, Any]) -> str:
        try:
            model = ollama_config.get('model', self.default_model)
            temperature = ollama_config.get('temperature', self.default_temperature)
            max_tokens = ollama_config.get('max_tokens', self.default_max_tokens)
            model_url = ollama_config.get('model_url', 'http://localhost:11434/api/generate')
            
            prompt = f"""Explain the following SQL query in simple terms:

SQL Query: {sql_query}

Original Request: {natural_language}

Provide a brief explanation of what this SQL query does and how it relates to the original request."""
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = requests.post(model_url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            explanation = result.get('response', '').strip()
            
            return explanation
            
        except Exception as e:
            logger.error(f"Failed to generate explanation: {str(e)}")
            return f"无法生成解释: {str(e)}"