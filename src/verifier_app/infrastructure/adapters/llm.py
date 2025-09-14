"""
LLM 適配器實作
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import openai
from openai import OpenAI

from ...core.config import settings
from ..ports.llm import LLMPort

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """LLM 結果資料類別"""
    response: str
    confidence: float
    tokens_used: int
    metadata: Dict[str, Any]


class BaseLLMAdapter(ABC):
    """LLM 適配器基礎類別"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> LLMResult:
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


class OpenAIAdapter(BaseLLMAdapter, LLMPort):
    """OpenAI GPT 適配器"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """初始化 OpenAI 適配器"""
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"OpenAI adapter initialized with model: {model}")
    
    async def generate_response(self, prompt: str, **kwargs) -> LLMResult:
        """生成回應"""
        try:
            max_tokens = kwargs.get('max_tokens', 1000)
            temperature = kwargs.get('temperature', 0.3)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            result = LLMResult(
                response=response.choices[0].message.content,
                confidence=1.0,  # OpenAI 不提供信心度，預設為 1.0
                tokens_used=response.usage.total_tokens,
                metadata={
                    "model": self.model,
                    "finish_reason": response.choices[0].finish_reason,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    async def extract_structured_data(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """從文字中提取結構化資料"""
        try:
            # 建立提示
            prompt = self._build_extraction_prompt(text, schema)
            
            response = await self.generate_response(
                prompt,
                max_tokens=1500,
                temperature=0.1  # 低溫度以獲得更一致的結果
            )
            
            # 嘗試解析 JSON 回應
            import json
            try:
                extracted_data = json.loads(response.response)
                return {
                    "success": True,
                    "data": extracted_data,
                    "confidence": response.confidence,
                    "tokens_used": response.tokens_used
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON")
                return {
                    "success": False,
                    "data": {},
                    "error": "Invalid JSON response",
                    "raw_response": response.response
                }
                
        except Exception as e:
            logger.error(f"Structured data extraction failed: {e}")
            return {
                "success": False,
                "data": {},
                "error": str(e)
            }
    
    async def validate_document_content(self, ocr_text: str, template_rules: Dict[str, Any]) -> Dict[str, Any]:
        """驗證文件內容"""
        try:
            # 建立驗證提示
            prompt = self._build_validation_prompt(ocr_text, template_rules)
            
            response = await self.generate_response(
                prompt,
                max_tokens=1000,
                temperature=0.2
            )
            
            # 解析驗證結果
            import json
            try:
                validation_result = json.loads(response.response)
                return {
                    "success": True,
                    "is_valid": validation_result.get("is_valid", False),
                    "confidence": validation_result.get("confidence", 0.0),
                    "issues": validation_result.get("issues", []),
                    "extracted_fields": validation_result.get("extracted_fields", {}),
                    "tokens_used": response.tokens_used
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse validation response as JSON")
                return {
                    "success": False,
                    "is_valid": False,
                    "error": "Invalid JSON response",
                    "raw_response": response.response
                }
                
        except Exception as e:
            logger.error(f"Document validation failed: {e}")
            return {
                "success": False,
                "is_valid": False,
                "error": str(e)
            }
    
    async def suggest_fields(self, ocr_text: str, prompt: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """根據 OCR 文字和提示建議文件欄位 (OpenAI 實作)"""
        system_prompt = """
你是一個文件處理專家，能根據提供的文件文字內容，
識別出文件中重要的欄位及其在頁面上的大致位置 (bounding box)。
請以 JSON 陣列的格式返回欄位定義，每個物件包含 'name', 'bbox', 'required', 'suggested'。
Bounding box (bbox) 是一個包含 'x1', 'y1', 'x2', 'y2' 的字典，座標值介於 0 到 1000 之間，表示相對於圖片左上角的位置。
'required' 表示該欄位是否為此文件類型中通常必須存在的。
'suggested' 永遠設置為 True。
如果找不到任何欄位，返回一個空陣列。
範例：
[
    {
        "name": "姓名",
        "bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 80},
        "required": true,
        "suggested": true
    },
    {
        "name": "日期",
        "bbox": {"x1": 400, "y1": 100, "x2": 600, "y2": 130},
        "required": false,
        "suggested": true
    }
]
"""

        user_prompt = f"請根據以下文件文字內容，建議重要的欄位及其大致位置：\n\n{ocr_text}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            import json
            try:
                suggested_fields = json.loads(content)
                if not isinstance(suggested_fields, list):
                    logger.error(f"LLM 返回的 JSON 格式不正確，預期為列表: {content}")
                    return []
                return suggested_fields
            except json.JSONDecodeError:
                logger.error(f"無法解析 LLM 返回的 JSON: {content}")
                return []

        except Exception as e:
            logger.error(f"OpenAI field suggestion failed: {e}")
            raise
    
    def _build_extraction_prompt(self, text: str, schema: Dict[str, Any]) -> str:
        """建立資料提取提示"""
        fields_description = "\n".join([
            f"- {field}: {info.get('description', 'No description')}"
            for field, info in schema.get('fields', {}).items()
        ])
        
        return f"""
請從以下 OCR 文字中提取指定的欄位資訊，並以 JSON 格式回應：

OCR 文字：
{text}

需要提取的欄位：
{fields_description}

請以以下 JSON 格式回應：
{{
    "field1": "extracted_value1",
    "field2": "extracted_value2",
    ...
}}

如果某個欄位找不到或不確定，請設為 null。
只回應 JSON，不要包含其他文字。
"""
    
    def _build_validation_prompt(self, ocr_text: str, template_rules: Dict[str, Any]) -> str:
        """建立驗證提示"""
        rules_description = "\n".join([
            f"- {rule}: {description}"
            for rule, description in template_rules.get('validation_rules', {}).items()
        ])
        
        return f"""
請驗證以下 OCR 文字是否符合指定的文件規則：

OCR 文字：
{ocr_text}

驗證規則：
{rules_description}

請以以下 JSON 格式回應：
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["issue1", "issue2"],
    "extracted_fields": {{
        "field1": "value1",
        "field2": "value2"
    }}
}}

只回應 JSON，不要包含其他文字。
"""


class GeminiAdapter(BaseLLMAdapter, LLMPort):
    """Google Gemini 適配器（待實作）"""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        """初始化 Gemini 適配器"""
        self.api_key = api_key
        self.model = model
        # TODO: 初始化 Gemini 客戶端
        raise NotImplementedError("Gemini adapter not implemented yet")
    
    async def generate_response(self, prompt: str, **kwargs) -> LLMResult:
        # TODO: 實作 Gemini API 調用
        raise NotImplementedError("Gemini adapter not implemented yet")
    
    async def extract_structured_data(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: 實作結構化資料提取
        raise NotImplementedError("Gemini adapter not implemented yet")
    
    async def validate_document_content(self, ocr_text: str, template_rules: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: 實作文件驗證
        raise NotImplementedError("Gemini adapter not implemented yet")

    async def suggest_fields(self, ocr_text: str, prompt: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """根據 OCR 文字和提示建議文件欄位 (Gemini 實作)"""
        system_prompt = """
你是一個文件處理專家，能根據提供的文件文字內容，
識別出文件中重要的欄位及其在頁面上的大致位置 (bounding box)。
請以 JSON 陣列的格式返回欄位定義，每個物件包含 'name', 'bbox', 'required', 'suggested'。
Bounding box (bbox) 是一個包含 'x1', 'y1', 'x2', 'y2' 的字典，座標值介於 0 到 1000 之間，表示相對於圖片左上角的位置。
'required' 表示該欄位是否為此文件類型中通常必須存在的。
'suggested' 永遠設置為 True。
如果找不到任何欄位，返回一個空陣列。
範例：
[
    {
        "name": "姓名",
        "bbox": {"x1": 100, "y1": 50, "x2": 300, "y2": 80},
        "required": true,
        "suggested": true
    },
    {
        "name": "日期",
        "bbox": {"x1": 400, "y1": 100, "x2": 600, "y2": 130},
        "required": false,
        "suggested": true
    }
]
"""

        user_prompt = f"請根據以下文件文字內容，建議重要的欄位及其大致位置：\n\n{ocr_text}"

        try:
            response = self.model.generate_content(
                prompt=user_prompt,
                generation_config={
                    "max_output_tokens": 1500,
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            content = response.text
            
            import json
            try:
                suggested_fields = json.loads(content)
                if not isinstance(suggested_fields, list):
                    logger.error(f"LLM 返回的 JSON 格式不正確，預期為列表: {content}")
                    return []
                return suggested_fields
            except json.JSONDecodeError:
                logger.error(f"無法解析 LLM 返回的 JSON: {content}")
                return []

        except Exception as e:
            logger.error(f"Gemini field suggestion failed: {e}")
            raise


# LLM 適配器工廠
class LLMAdapterFactory:
    """LLM 適配器工廠"""
    
    _adapters = {
        "openai": OpenAIAdapter,
        "gemini": GeminiAdapter
    }
    
    @classmethod
    def create_adapter(cls, provider: str, **kwargs) -> BaseLLMAdapter:
        """建立 LLM 適配器"""
        if provider not in cls._adapters:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        return cls._adapters[provider](**kwargs)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """取得可用的 LLM 提供者"""
        return list(cls._adapters.keys())
