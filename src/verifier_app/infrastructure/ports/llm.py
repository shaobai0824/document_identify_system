"""
LLM 服務介面定義
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMPort(ABC):
    """LLM 服務介面"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成回應"""
        pass
    
    @abstractmethod
    async def extract_structured_data(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """從文字中提取結構化資料"""
        pass
    
    @abstractmethod
    async def validate_document_content(self, ocr_text: str, template_rules: Dict[str, Any]) -> Dict[str, Any]:
        """驗證文件內容"""
        pass

    @abstractmethod
    async def suggest_fields(self, ocr_text: str, prompt: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """根據 OCR 文字和提示建議文件欄位"""
        pass
