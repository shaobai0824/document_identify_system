"""
OCR 服務實作
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from ...core.config import settings
from ...domains.documents.entities import OcrBlock
from ...domains.templates.entities import BoundingBox
from ..adapters.ocr import OCRAdapterFactory, OCRResult
from ..ports.ocr import OcrPort

logger = logging.getLogger(__name__)


class OCRService(OcrPort):
    """OCR 服務實作"""
    
    def __init__(self):
        """初始化 OCR 服務"""
        self.settings = settings
        
        # 根據配置建立適配器
        if settings.ocr_provider == "tesseract":
            try:
                self.adapter = OCRAdapterFactory.create_adapter(
                    "tesseract",
                    language="eng+chi_tra",  # 英文 + 繁體中文
                    psm=6,  # 單一統一文字區塊
                    oem=3,  # 預設 OCR 引擎模式
                    config_options={
                        "tessedit_char_whitelist": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz一二三四五六七八九十壹貳參肆伍陸柒捌玖拾",
                        "preserve_interword_spaces": "1"
                    }
                )
            except RuntimeError as e:
                logger.warning(f"Tesseract not available: {e}, falling back to mock OCR for testing")
                from ..adapters.mock_ocr import MockOCRAdapter
                self.adapter = MockOCRAdapter()
        elif settings.ocr_provider == "google_vision":
            self.adapter = OCRAdapterFactory.create_adapter(
                "google_vision",
                credentials_path=settings.google_vision_credentials_path
            )
        else:
            raise ValueError(f"Unsupported OCR provider: {settings.ocr_provider}")
        
        logger.info(f"OCR service initialized with provider: {settings.ocr_provider}")
    
    async def extract_text(self, file_path: str, language: str = "chi_tra+eng") -> List[OcrBlock]:
        """從影像中擷取文字與座標"""
        try:
            # 使用適配器執行 OCR
            result: OCRResult = await self.adapter.extract_text(file_path)
            
            # 轉換為領域實體
            ocr_blocks = []
            
            for region in result.regions:
                # 建立邊界框
                bbox_data = region["bbox"]
                bbox = BoundingBox(
                    x1=bbox_data[0],
                    y1=bbox_data[1], 
                    x2=bbox_data[2],
                    y2=bbox_data[3]
                )
                
                # 建立 OCR 區塊
                ocr_block = OcrBlock(
                    page=1,  # 預設為第一頁，PDF 處理時需要調整
                    bbox=bbox,
                    text=region["text"],
                    confidence=region["confidence"]
                )
                
                ocr_blocks.append(ocr_block)
            
            logger.info(f"OCR completed for {file_path}: {len(ocr_blocks)} blocks extracted")
            return ocr_blocks
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {file_path}: {e}")
            raise
    
    async def get_supported_formats(self) -> List[str]:
        """取得支援的檔案格式"""
        return self.adapter.get_supported_formats()
    
    async def extract_text_with_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取文字並返回完整結果（包含元資料）"""
        try:
            # 檢查適配器是否有 extract_text_with_metadata 方法
            if hasattr(self.adapter, 'extract_text_with_metadata'):
                return await self.adapter.extract_text_with_metadata(file_path)
            else:
                # 使用標準的 extract_text 方法並轉換格式
                ocr_blocks = await self.adapter.extract_text(file_path)
                
                # 將 OcrBlock 列表轉換為標準格式
                regions = []
                full_text_parts = []
                
                for block in ocr_blocks:
                    regions.append({
                        "text": block.text,
                        "confidence": block.confidence,
                        "bbox": (block.bbox.x1, block.bbox.y1, block.bbox.x2, block.bbox.y2),
                        "level": 3  # 預設層級
                    })
                    full_text_parts.append(block.text)
                
                full_text = "\n".join(full_text_parts)
                avg_confidence = sum([block.confidence for block in ocr_blocks]) / len(ocr_blocks) if ocr_blocks else 0.0
                
                return {
                    "text": full_text,
                    "confidence": avg_confidence,
                    "regions": regions,
                    "metadata": {
                        "engine": "ocr_service",
                        "blocks_count": len(ocr_blocks)
                    }
                }
            
        except Exception as e:
            logger.error(f"OCR extraction with metadata failed for {file_path}: {e}")
            raise
