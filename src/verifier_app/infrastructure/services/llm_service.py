"""
LLM 服務實作
"""

import logging
from typing import Any, Dict, List, Optional

import openai
from dotenv import load_dotenv

from ...core.config import settings
from ..adapters.llm import LLMAdapterFactory
from ..ports.llm import LLMPort

logger = logging.getLogger(__name__)


class LLMService(LLMPort):
    """LLM 服務實作"""
    
    def __init__(self):
        """初始化 LLM 服務"""
        self.settings = settings
        
        # 根據配置建立適配器
        if settings.llm_provider == "openai" and settings.openai_api_key:
            self.adapter = LLMAdapterFactory.create_adapter(
                "openai",
                api_key=settings.openai_api_key,
                model="gpt-3.5-turbo"
            )
        else:
            logger.warning("LLM service not configured, using mock adapter")
            from ..adapters.mock_llm import MockLLMAdapter
            self.adapter = MockLLMAdapter()
        
        logger.info(f"LLM service initialized with provider: {settings.llm_provider}")
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成回應"""
        if not self.adapter:
            raise RuntimeError("LLM service not configured")
        
        return await self.adapter.generate_response(prompt, **kwargs)
    
    async def extract_structured_data(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """從文字中提取結構化資料"""
        if not self.adapter:
            raise RuntimeError("LLM service not configured")
        return await self.adapter.extract_structured_data(text, schema)
    
    async def suggest_fields(self, ocr_text: str, prompt: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """根據 OCR 文字和提示建議文件欄位"""
        if not self.adapter:
            raise RuntimeError("LLM service not configured")
        return await self.adapter.suggest_fields(ocr_text, prompt)
    
    async def validate_document_content(self, ocr_text: str, template_rules: Dict[str, Any]) -> Dict[str, Any]:
        """驗證文件內容"""
        if not self.adapter:
            logger.warning("LLM service not available, skipping content validation")
            return {
                "success": False,
                "is_valid": False,
                "error": "LLM service not configured"
            }
        
        return await self.adapter.validate_document_content(ocr_text, template_rules)
    
    async def enhance_ocr_result(self, ocr_text: str, document_type: str) -> Dict[str, Any]:
        """增強 OCR 結果"""
        if not self.adapter:
            return {"enhanced_text": ocr_text, "improvements": []}
        
        try:
            prompt = f"""
請協助改善以下 OCR 文字的品質，這是一份 {document_type} 文件：

原始 OCR 文字：
{ocr_text}

請：
1. 修正明顯的 OCR 錯誤
2. 改善標點符號和格式
3. 保持原始資訊的完整性

請以 JSON 格式回應：
{{
    "enhanced_text": "改善後的文字",
    "improvements": ["改善項目1", "改善項目2"]
}}
"""
            
            result = await self.adapter.generate_response(prompt, temperature=0.2)
            
            import json
            try:
                enhancement = json.loads(result.response)
                return {
                    "success": True,
                    "enhanced_text": enhancement.get("enhanced_text", ocr_text),
                    "improvements": enhancement.get("improvements", []),
                    "tokens_used": result.tokens_used
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse OCR enhancement response")
                return {"enhanced_text": ocr_text, "improvements": []}
                
        except Exception as e:
            logger.error(f"OCR enhancement failed: {e}")
            return {"enhanced_text": ocr_text, "improvements": []}
    
    def is_available(self) -> bool:
        """檢查 LLM 服務是否可用"""
        return self.adapter is not None
