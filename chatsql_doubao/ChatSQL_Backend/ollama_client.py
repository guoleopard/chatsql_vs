import httpx
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_sql(self, question: str, metadata: Dict[str, Any], model_config: Dict[str, Any]) -> str:
        try:
            model_name = model_config.get('modelName', 'llama3')
            temperature = model_config.get('temperature', 0.7)
            max_tokens = model_config.get('maxTokens', 1000)
            
            # 构建提示词
            prompt = self._build_sql_generation_prompt(question, metadata)
            
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "num_predict": max_tokens
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                sql = self._extract_sql(result.get('response', ''))
                logger.info(f"成功生成SQL: {sql}")
                return sql
            else:
                raise Exception(f"Ollama API返回错误: {response.status_code}")
                
        except Exception as e:
            logger.error(f"生成SQL失败: {str(e)}")
            raise Exception(f"生成SQL失败: {str(e)}")
    
    def _build_sql_generation_prompt(self, question: str, metadata: Dict[str, Any]) -> str:
        db_type = metadata.get('db_type', 'mysql')
        tables = metadata.get('tables', [])
        
        # 构建数据库结构描述
        schema_description = ""
        for table in tables:
            table_name = table.get('name', '')
            table_comment = table.get('comment', '')
            columns = table.get('columns', [])
            
            schema_description += f"\n表: {table_name}"
            if table_comment:
                schema_description += f" ({table_comment})"
            schema_description += "\n"
            
            for column in columns:
                col_name = column.get('name', '')
                col_type = column.get('type', '')
                col_comment = column.get('comment', '')
                nullable = "可空" if column.get('nullable', True) else "非空"
                
                schema_description += f"  - {col_name}: {col_type} ({nullable})"
                if col_comment:
                    schema_description += f" - {col_comment}"
                schema_description += "\n"
        
        # 构建完整的提示词
        prompt = f"""你是一个SQL专家，请根据以下数据库结构和用户问题生成正确的SQL查询语句。

数据库类型: {db_type}

数据库结构:
{schema_description}

用户问题: {question}

请生成{db_type}数据库的SQL查询语句，只返回SQL语句，不要包含任何解释或其他文本。

SQL语句:"""
        
        return prompt
    
    def _extract_sql(self, response: str) -> str:
        """从响应中提取SQL语句"""
        # 移除前后空白字符
        sql = response.strip()
        
        # 如果响应包含多个SQL语句，只取第一个
        if ';' in sql and not sql.endswith(';'):
            sql = sql.split(';')[0] + ';'
        
        # 确保SQL语句以分号结尾
        if not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    async def test_connection(self) -> bool:
        """测试Ollama连接"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama连接测试失败: {str(e)}")
            return False
    
    async def get_models(self) -> List[str]:
        """获取可用的模型列表"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                return [model.get('name', '') for model in models]
            else:
                return []
        except Exception as e:
            logger.error(f"获取模型列表失败: {str(e)}")
            return []
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()