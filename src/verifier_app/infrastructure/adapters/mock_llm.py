"""
模擬 LLM 適配器，用於測試目的
"""

import logging
from typing import Any, Dict, List, Optional

from ...domains.documents.entities import OcrBlock
from ..ports.llm import LLMPort, LLMResult

logger = logging.getLogger(__name__)


class MockLLMAdapter(LLMPort):
    """模擬 LLM 適配器，用於測試"""
    
    def __init__(self):
        """初始化模擬 LLM 適配器"""
        logger.info("Mock LLM adapter initialized for testing")
    
    async def generate_response(self, prompt: str, **kwargs) -> LLMResult:
        """模擬生成回應"""
        logger.info(f"Mock LLM processing prompt: {prompt[:100]}...")
        
        # 模擬回應
        mock_response = "這是一個模擬的 LLM 回應，用於測試目的。"
        
        return LLMResult(
            response=mock_response,
            tokens_used=50,
            model="mock-llm",
            metadata={"test": True}
        )
    
    async def extract_structured_data(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """模擬結構化資料提取"""
        logger.info(f"Mock LLM extracting structured data from: {text[:100]}...")
        
        # 模擬提取的結構化資料
        mock_extracted_data = {
            "姓名": "王小明",
            "身分證號": "A123456789",
            "日期": "2023-10-26",
            "地址": "台北市信義區信義路五段7號"
        }
        
        return {
            "success": True,
            "extracted_data": mock_extracted_data,
            "confidence": 0.85,
            "tokens_used": 30
        }
    
    async def validate_document_content(self, ocr_text: str, template_rules: Dict[str, Any]) -> Dict[str, Any]:
        """模擬文件內容驗證"""
        logger.info(f"Mock LLM validating document content: {ocr_text[:100]}...")
        
        # 模擬驗證結果
        mock_validation_result = {
            "is_valid": True,
            "confidence": 0.88,
            "issues": [],
            "extracted_fields": {
                "姓名": "王小明",
                "身分證號": "A123456789",
                "日期": "2023-10-26"
            },
            "suggestions": [
                "文件格式正確",
                "所有必填欄位都已填寫",
                "資料格式符合規範"
            ]
        }
        
        return {
            "success": True,
            **mock_validation_result,
            "tokens_used": 40
        }
    
    async def suggest_fields(self, ocr_text: str, prompt: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """模擬欄位建議"""
        logger.info(f"Mock LLM suggesting fields from: {ocr_text[:100]}...")
        
        # 模擬建議的欄位
        mock_suggested_fields = [
            {
                "name": "姓名",
                "bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 80},
                "confidence": 0.95,
                "type": "text",
                "required": True
            },
            {
                "name": "身分證號",
                "bbox": {"x1": 100, "y1": 200, "x2": 400, "y2": 230},
                "confidence": 0.88,
                "type": "text",
                "required": True
            },
            {
                "name": "日期",
                "bbox": {"x1": 400, "y1": 100, "x2": 600, "y2": 130},
                "confidence": 0.90,
                "type": "date",
                "required": False
            }
        ]
        
        return mock_suggested_fields
