"""
動態資料表服務
用於根據模板欄位動態建立資料表
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String,
                        Table, Text, create_engine, text)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ...core.config import settings
from ..database.base import get_sync_session
from ..database.models import Template

logger = logging.getLogger(__name__)


class DynamicTableService:
    """動態資料表服務"""
    
    def __init__(self):
        """初始化動態資料表服務"""
        self.settings = settings
        self.engine = create_engine(settings.DATABASE_URL)
        self.metadata = MetaData()
        
    async def create_table_for_template(self, template_id: str, template_name: str, field_definitions: List[Dict[str, Any]]) -> bool:
        """為模板建立對應的資料表"""
        try:
            # 生成表名（使用模板ID的簡化版本）
            table_name = f"template_{template_id.replace('-', '_')}"
            
            # 檢查表是否已存在
            if await self._table_exists(table_name):
                logger.info(f"Table {table_name} already exists for template {template_id}")
                return True
            
            # 建立表結構
            columns = [
                Column('id', String(36), primary_key=True),  # UUID
                Column('document_id', String(36), nullable=False),  # 關聯的文件ID
                Column('template_id', String(36), nullable=False),  # 模板ID
                Column('created_at', DateTime, default=datetime.utcnow),
                Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
                Column('verification_status', String(20), default='pending'),
                Column('confidence_score', Float, default=0.0),
                Column('raw_data', Text),  # 原始提取資料的JSON
            ]
            
            # 為每個欄位建立對應的資料庫欄位
            for field_def in field_definitions:
                field_name = field_def.get('name', '')
                if field_name:
                    # 清理欄位名稱，移除特殊字符
                    clean_field_name = self._clean_field_name(field_name)
                    columns.append(Column(clean_field_name, Text, nullable=True))
            
            # 建立表
            table = Table(table_name, self.metadata, *columns)
            table.create(self.engine)
            
            logger.info(f"Created table {table_name} for template {template_id}")
            
            # 記錄表建立資訊到模板
            await self._update_template_table_info(template_id, table_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table for template {template_id}: {e}")
            return False
    
    async def _table_exists(self, table_name: str) -> bool:
        """檢查表是否存在"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{table_name}'
                """))
                return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False
    
    async def _update_template_table_info(self, template_id: str, table_name: str):
        """更新模板的表資訊"""
        try:
            db = get_sync_session()
            template = db.query(Template).filter(Template.id == template_id).first()
            if template:
                # 更新模板的額外資訊
                if not template.validation_rules:
                    template.validation_rules = {}
                
                template.validation_rules['data_table'] = {
                    'table_name': table_name,
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'active'
                }
                
                db.commit()
                logger.info(f"Updated template {template_id} with table info")
            db.close()
        except Exception as e:
            logger.error(f"Failed to update template table info: {e}")
    
    def _clean_field_name(self, field_name: str) -> str:
        """清理欄位名稱，移除特殊字符"""
        import re

        # 移除或替換特殊字符
        clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', field_name)
        # 確保以字母開頭
        if clean_name and not clean_name[0].isalpha():
            clean_name = f"field_{clean_name}"
        return clean_name.lower()
    
    async def insert_extracted_data(self, template_id: str, document_id: str, extracted_data: Dict[str, Any], 
                                  verification_status: str = 'completed', confidence_score: float = 0.0) -> bool:
        """將提取的資料插入到對應的資料表中"""
        try:
            # 獲取表名
            table_name = await self._get_template_table_name(template_id)
            if not table_name:
                logger.error(f"No table found for template {template_id}")
                return False
            
            # 準備插入資料
            insert_data = {
                'id': document_id,  # 使用document_id作為主鍵
                'document_id': document_id,
                'template_id': template_id,
                'verification_status': verification_status,
                'confidence_score': confidence_score,
                'raw_data': json.dumps(extracted_data, ensure_ascii=False),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # 添加提取的欄位資料
            for field_name, field_value in extracted_data.items():
                clean_field_name = self._clean_field_name(field_name)
                insert_data[clean_field_name] = str(field_value) if field_value is not None else None
            
            # 執行插入
            with self.engine.connect() as conn:
                # 使用動態SQL插入
                columns = list(insert_data.keys())
                values = list(insert_data.values())
                
                placeholders = ', '.join(['?' for _ in values])
                column_names = ', '.join(columns)
                
                sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                conn.execute(text(sql), values)
                conn.commit()
            
            logger.info(f"Successfully inserted data for document {document_id} into table {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert data for template {template_id}: {e}")
            return False
    
    async def _get_template_table_name(self, template_id: str) -> Optional[str]:
        """獲取模板對應的表名"""
        try:
            db = get_sync_session()
            template = db.query(Template).filter(Template.id == template_id).first()
            if template and template.validation_rules and 'data_table' in template.validation_rules:
                table_name = template.validation_rules['data_table']['table_name']
                db.close()
                return table_name
            db.close()
            return None
        except Exception as e:
            logger.error(f"Failed to get table name for template {template_id}: {e}")
            return None
    
    async def get_template_data(self, template_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """獲取模板的所有驗證資料"""
        try:
            table_name = await self._get_template_table_name(template_id)
            if not table_name:
                return []
            
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT {limit}"))
                rows = result.fetchall()
                
                # 轉換為字典列表
                data = []
                for row in rows:
                    row_dict = dict(row._mapping)
                    # 解析raw_data
                    if row_dict.get('raw_data'):
                        try:
                            row_dict['raw_data'] = json.loads(row_dict['raw_data'])
                        except:
                            pass
                    data.append(row_dict)
                
                return data
                
        except Exception as e:
            logger.error(f"Failed to get template data: {e}")
            return []
    
    async def get_document_data(self, template_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        """獲取特定文件的驗證資料"""
        try:
            table_name = await self._get_template_table_name(template_id)
            if not table_name:
                return None
            
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} WHERE document_id = :doc_id"), 
                                    {"doc_id": document_id})
                row = result.fetchone()
                
                if row:
                    row_dict = dict(row._mapping)
                    # 解析raw_data
                    if row_dict.get('raw_data'):
                        try:
                            row_dict['raw_data'] = json.loads(row_dict['raw_data'])
                        except:
                            pass
                    return row_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get document data: {e}")
            return None
