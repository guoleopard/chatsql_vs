import json
import logging
from typing import Dict, List, Any, Optional
import os

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.metadata_store = []
        self._initialize_store()
    
    def _initialize_store(self):
        """初始化存储"""
        try:
            # 创建持久化目录
            os.makedirs(self.persist_directory, exist_ok=True)
            logger.info("向量存储初始化成功")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {str(e)}")
            raise Exception(f"向量存储初始化失败: {str(e)}")
    
    async def store_metadata(self, metadata: Dict[str, Any]):
        """存储数据库元数据"""
        try:
            tables = metadata.get('tables', [])
            self.metadata_store = []
            
            for i, table in enumerate(tables):
                table_name = table.get('name', '')
                table_comment = table.get('comment', '')
                columns = table.get('columns', [])
                
                # 构建文档内容
                content = f"表名: {table_name}\n"
                if table_comment:
                    content += f"表描述: {table_comment}\n"
                
                content += "字段信息:\n"
                for column in columns:
                    col_name = column.get('name', '')
                    col_type = column.get('type', '')
                    col_comment = column.get('comment', '')
                    nullable = "可空" if column.get('nullable', True) else "非空"
                    
                    content += f"- {col_name} ({col_type}, {nullable})"
                    if col_comment:
                        content += f" - {col_comment}"
                    content += "\n"
                
                self.metadata_store.append({
                    "id": f"table_{i}",
                    "table_name": table_name,
                    "table_comment": table_comment,
                    "content": content,
                    "columns": columns
                })
            
            logger.info(f"成功存储 {len(self.metadata_store)} 个表的元数据")
            
        except Exception as e:
            logger.error(f"存储元数据失败: {str(e)}")
            raise Exception(f"存储元数据失败: {str(e)}")
    
    async def search_relevant_metadata(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """搜索相关的数据库元数据"""
        try:
            # 简单的关键词匹配
            relevant_tables = []
            query_lower = query.lower()
            
            for table_data in self.metadata_store:
                content_lower = table_data["content"].lower()
                table_name_lower = table_data["table_name"].lower()
                
                # 计算相关性分数
                score = 0
                if table_name_lower in query_lower:
                    score += 10
                
                # 检查查询中的关键词是否出现在内容中
                keywords = query_lower.split()
                for keyword in keywords:
                    if len(keyword) > 2:  # 忽略太短的词
                        if keyword in content_lower:
                            score += 1
                
                if score > 0:
                    relevant_tables.append({
                        "table_name": table_data["table_name"],
                        "table_comment": table_data["table_comment"],
                        "content": table_data["content"],
                        "score": score
                    })
            
            # 按分数排序
            relevant_tables.sort(key=lambda x: x["score"], reverse=True)
            
            # 限制结果数量
            relevant_tables = relevant_tables[:n_results]
            
            logger.info(f"找到 {len(relevant_tables)} 个相关表")
            return {
                "relevant_tables": relevant_tables,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"搜索相关元数据失败: {str(e)}")
            return {
                "relevant_tables": [],
                "query": query
            }
    
    def clear_all(self):
        """清空所有数据"""
        try:
            self.metadata_store = []
            logger.info("向量存储已清空")
        except Exception as e:
            logger.error(f"清空向量存储失败: {str(e)}")
            raise Exception(f"清空向量存储失败: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            return {
                "total_documents": len(self.metadata_store),
                "collection_name": "database_metadata",
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "total_documents": 0,
                "error": str(e)
            }