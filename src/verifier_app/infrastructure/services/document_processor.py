"""
文件處理服務
"""

import hashlib
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from ...core.config import settings
from ...domains.documents.entities import (OcrBlock, SubmittedDocument,
                                           ValidationResult)
from ..database.base import get_sync_session
from ..database.models import (Document, DocumentStatus, VerificationRecord,
                               VerificationStatus)
from .dynamic_table_service import DynamicTableService
from .ocr_service import OCRService
from .storage_service import StorageService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """文件處理服務"""
    
    def __init__(self):
        """初始化文件處理器"""
        self.ocr_service = OCRService()
        self.storage_service = StorageService()
        self.dynamic_table_service = DynamicTableService()
        self.settings = settings
        
    async def process_uploaded_file(self, 
                                   file_content: bytes, 
                                   filename: str,
                                   template_id: Optional[str] = None) -> Dict[str, Any]:
        """處理上傳的檔案"""
        try:
            # 1. 基本驗證
            if len(file_content) > self.settings.max_file_size_mb * 1024 * 1024:
                raise ValueError(f"File size exceeds limit: {self.settings.max_file_size_mb}MB")
            
            file_extension = Path(filename).suffix.lower().lstrip('.')
            if file_extension not in self.settings.supported_file_types:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # 2. 計算檔案雜湊
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # 3. 檢查重複檔案
            db = get_sync_session()
            existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
            if existing_doc:
                logger.info(f"Duplicate file detected: {file_hash}")
                return {
                    "document_id": str(existing_doc.id),
                    "status": "duplicate",
                    "message": "File already processed"
                }
            
            # 4. 儲存檔案到臨時位置
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                tmp_file.write(file_content)
                temp_path = tmp_file.name
            
            try:
                # 5. 上傳到儲存系統
                document_id = uuid4()
                storage_path = self.storage_service.generate_storage_path(filename, str(document_id))
                storage_url = await self.storage_service.upload_file(temp_path, storage_path)
                
                # 6. 建立文件記錄（包含 storage_path）
                document = Document(
                    id=document_id,
                    filename=f"{document_id}{Path(filename).suffix}",
                    original_filename=filename,
                    content_type=self._get_content_type(file_extension),
                    file_size=len(file_content),
                    file_hash=file_hash,
                    storage_path=storage_path,
                    status=DocumentStatus.PROCESSING,
                    storage_provider="local"  # 預設使用本地儲存
                )
                
                db.add(document)
                db.commit()
                
                # 7. 執行 OCR
                ocr_result = await self.ocr_service.extract_text_with_metadata(temp_path)
                
                # 更新 OCR 結果
                document.ocr_text = ocr_result["text"]
                document.ocr_confidence = ocr_result["confidence"]
                document.ocr_metadata = ocr_result["metadata"]
                document.status = DocumentStatus.OCR_COMPLETED
                document.processed_at = datetime.utcnow()
                db.commit()
                
                # 8. 如果有模板 ID，執行驗證
                verification_result = None
                if template_id:
                    verification_result = await self._verify_document(document, template_id, db)
                
                logger.info(f"Document processed successfully: {document_id}")
                
                return {
                    "document_id": str(document_id),
                    "status": "success",
                    "ocr_result": {
                        "text": ocr_result["text"],
                        "confidence": ocr_result["confidence"],
                        "regions_count": len(ocr_result["regions"])
                    },
                    "verification_result": verification_result,
                    "storage_url": storage_url
                }
                
            finally:
                # 清理臨時檔案
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            
            # 更新文件狀態為失敗
            if 'document' in locals():
                document.status = DocumentStatus.FAILED
                db.commit()
            
            raise
        finally:
            if 'db' in locals():
                db.close()
    
    async def _verify_document(self, 
                              document: Document, 
                              template_id: str, 
                              db: Session) -> Dict[str, Any]:
        """驗證文件"""
        try:
            # 取得模板定義
            from ..database.models import Template
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                raise ValueError(f"Template not found: {template_id}")
            
            expected_fields = {field["name"]: field for field in template.field_definitions}
            
            # 建立驗證記錄
            verification = VerificationRecord(
                document_id=document.id,
                template_id=template_id,
                status=VerificationStatus.PENDING
            )
            
            db.add(verification)
            db.commit()
            
            # 1. 使用 LLM 進行內容審核
            llm_validation_result = await self._llm_content_review(document, template, db)
            
            # 2. 根據模板欄位進行比對驗證
            field_validation_result = await self._validate_template_fields(document, template, db)
            
            # 3. 合併驗證結果
            overall_confidence = document.ocr_confidence or 0.0
            is_valid = llm_validation_result.get("is_valid", False) and field_validation_result.get("is_valid", False)
            
            # 4. 如果驗證成功，建立資料表並存入資料
            if is_valid:
                await self._handle_successful_verification(
                    template_id, template, document, 
                    field_validation_result.get("extracted_data", {}),
                    overall_confidence, db
                )
            
            # 更新驗證記錄
            verification.status = VerificationStatus.COMPLETED if is_valid else VerificationStatus.FAILED
            verification.confidence_score = overall_confidence
            verification.validation_details = {
                "llm_review": llm_validation_result,
                "field_validation": field_validation_result
            }
            
            db.commit()
            
            return {
                "is_valid": is_valid,
                "confidence": overall_confidence,
                "extracted_data": field_validation_result.get("extracted_data", {}),
                "field_results": field_validation_result.get("field_results", {}),
                "llm_review": llm_validation_result,
                "missing_fields": field_validation_result.get("missing_fields", []),
                "low_confidence_fields": field_validation_result.get("low_confidence_fields", []),
                "data_stored": is_valid  # 標示資料是否已存入
            }
            
        except Exception as e:
            logger.error(f"Document verification failed: {e}")
            # 更新驗證記錄為失敗
            if 'verification' in locals():
                verification.status = VerificationStatus.FAILED
                verification.error_message = str(e)
                db.commit()
            raise
    
    async def _llm_content_review(self, document: Document, template, db: Session) -> Dict[str, Any]:
        """使用 LLM 進行內容審核"""
        try:
            from .llm_service import LLMService
            llm_service = LLMService()
            
            # 獲取 OCR 文字
            ocr_text = document.ocr_text or "無 OCR 文字"
            
            # 建立模板規則
            template_rules = {
                "template_name": template.name,
                "expected_fields": [field["name"] for field in template.field_definitions],
                "required_fields": [field["name"] for field in template.field_definitions if field.get("required", False)]
            }
            
            # 使用 LLM 進行內容審核
            validation_result = await llm_service.validate_document_content(ocr_text, template_rules)
            
            logger.info(f"LLM content review completed for document {document.id}: {validation_result}")
            return validation_result
            
        except Exception as e:
            logger.warning(f"LLM content review failed: {e}")
            return {
                "success": False,
                "is_valid": True,  # 如果 LLM 失敗，預設為有效
                "error": str(e),
                "confidence": 0.5
            }
    
    async def _validate_template_fields(self, document: Document, template, db: Session) -> Dict[str, Any]:
        """根據模板欄位進行比對驗證"""
        try:
            # 模擬提取的資料（實際會來自 OCR 和 LLM 提取）
            mock_extracted_data = {
                "姓名": "王小明",
                "日期": "2023-10-26",
                "身分證號": "A123456789"
            }
            mock_per_field_confidence = {
                "姓名": 0.95,
                "日期": 0.80,
                "身分證號": 0.88
            }
            mock_bboxes = {
                "姓名": {"x1": 100, "y1": 50, "x2": 300, "y2": 80},
                "日期": {"x1": 400, "y1": 100, "x2": 600, "y2": 130},
                "身分證號": {"x1": 100, "y1": 200, "x2": 400, "y2": 230}
            }
            
            expected_fields = {field["name"]: field for field in template.field_definitions}
            missing_fields = []
            low_confidence_fields = []
            field_results = {}
            
            # 比對預期欄位與提取資料
            for field_name, field_def in expected_fields.items():
                if field_name not in mock_extracted_data:
                    missing_fields.append({
                        "field_name": field_name,
                        "bbox": field_def["bbox"],
                        "reason": "not_found"
                    })
                else:
                    confidence = mock_per_field_confidence.get(field_name, 0.0)
                    if confidence < (template.confidence_threshold or 0.8):
                        low_confidence_fields.append({
                            "field_name": field_name,
                            "bbox": field_def["bbox"],
                            "reason": "low_confidence",
                            "confidence": confidence
                        })
                    field_results[field_name] = {
                        "confidence": confidence, 
                        "bbox": mock_bboxes.get(field_name),
                        "value": mock_extracted_data[field_name]
                    }
            
            # 判斷整體狀態
            is_valid = len(missing_fields) == 0 and len(low_confidence_fields) == 0
            
            return {
                "is_valid": is_valid,
                "extracted_data": mock_extracted_data,
                "field_results": field_results,
                "missing_fields": missing_fields,
                "low_confidence_fields": low_confidence_fields
            }
            
        except Exception as e:
            logger.error(f"Template field validation failed: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "extracted_data": {},
                "field_results": {},
                "missing_fields": [],
                "low_confidence_fields": []
            }
    
    async def _handle_successful_verification(self, template_id: str, template, document: Document, 
                                             extracted_data: Dict[str, Any], confidence_score: float, db: Session):
        """處理成功驗證的文件，建立資料表並存入資料"""
        try:
            logger.info(f"Handling successful verification for document {document.id} with template {template_id}")
            
            # 1. 建立或確認資料表存在
            table_created = await self.dynamic_table_service.create_table_for_template(
                template_id, template.name, template.field_definitions
            )
            
            if not table_created:
                logger.error(f"Failed to create table for template {template_id}")
                return
            
            # 2. 存入提取的資料
            data_stored = await self.dynamic_table_service.insert_extracted_data(
                template_id=template_id,
                document_id=str(document.id),
                extracted_data=extracted_data,
                verification_status='completed',
                confidence_score=confidence_score
            )
            
            if data_stored:
                logger.info(f"Successfully stored data for document {document.id} in template table")
                
                # 3. 更新文件狀態為已驗證
                document.status = DocumentStatus.VERIFIED
                db.commit()
                
                # 4. 記錄成功資訊
                logger.info(f"Document {document.id} verification completed and data stored successfully")
            else:
                logger.error(f"Failed to store data for document {document.id}")
                
        except Exception as e:
            logger.error(f"Error handling successful verification: {e}")
    
    def _get_content_type(self, file_extension: str) -> str:
        """根據副檔名取得 MIME 類型"""
        content_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'tiff': 'image/tiff',
            'bmp': 'image/bmp'
        }
        
        return content_types.get(file_extension, 'application/octet-stream')
    
    async def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """取得文件處理狀態"""
        try:
            db = get_sync_session()
            
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # 取得驗證記錄
            verification = db.query(VerificationRecord).filter(
                VerificationRecord.document_id == document.id
            ).first()
            
            result = {
                "document_id": str(document.id),
                "filename": document.original_filename,
                "status": document.status.value,
                "processing_progress": document.processing_progress,
                "created_at": document.created_at.isoformat(),
                "processed_at": document.processed_at.isoformat() if document.processed_at else None,
                "ocr_result": {
                    "text": document.ocr_text,
                    "confidence": document.ocr_confidence,
                    "metadata": document.ocr_metadata
                } if document.ocr_text else None,
                "pages": document.ocr_metadata.get("pages") if document.ocr_metadata else None,
                "verification_result": {
                    "verification_id": str(verification.id),
                    "status": verification.status.value,
                    "confidence": verification.overall_confidence,
                    "requires_manual_review": verification.requires_manual_review,
                    "extracted_data": verification.extracted_data
                } if verification else None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get document status: {e}")
            raise
        finally:
            if 'db' in locals():
                db.close()
