"""
模擬 OCR 適配器，用於測試目的
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from ...domains.documents.entities import OcrBlock
from ...domains.templates.entities import BoundingBox
from ..ports.ocr import OcrPort

logger = logging.getLogger(__name__)


@dataclass
class MockOCRResult:
    """模擬 OCR 結果資料類別"""
    text: str
    confidence: float
    regions: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class MockOCRAdapter(OcrPort):
    """模擬 OCR 適配器，用於測試"""
    
    def __init__(self):
        """初始化模擬 OCR 適配器"""
        logger.info("Mock OCR adapter initialized for testing")
    
    async def extract_text(self, file_path: str, language: str = "chi_tra+eng") -> List[OcrBlock]:
        """模擬文字提取"""
        logger.info(f"Mock OCR processing file: {file_path}")
        
        # 模擬提取的文字內容
        mock_text_regions = [
            {
                "text": "Document Verification Test",
                "confidence": 0.95,
                "bbox": (50, 100, 350, 130),
                "level": 3
            },
            {
                "text": "Name: John Doe",
                "confidence": 0.92,
                "bbox": (50, 180, 200, 210),
                "level": 3
            },
            {
                "text": "ID: A123456789",
                "confidence": 0.88,
                "bbox": (50, 260, 250, 290),
                "level": 3
            },
            {
                "text": "Date: 2024-01-01",
                "confidence": 0.90,
                "bbox": (50, 340, 220, 370),
                "level": 3
            }
        ]
        
        # 轉換為 OcrBlock 對象
        ocr_blocks = []
        for region in mock_text_regions:
            bbox = BoundingBox(
                x1=region["bbox"][0],
                y1=region["bbox"][1],
                x2=region["bbox"][2],
                y2=region["bbox"][3]
            )
            
            ocr_block = OcrBlock(
                page=1,
                bbox=bbox,
                text=region["text"],
                confidence=region["confidence"]
            )
            ocr_blocks.append(ocr_block)
        
        return ocr_blocks
    
    async def get_supported_formats(self) -> List[str]:
        """取得支援的檔案格式"""
        return ["jpg", "jpeg", "png", "tiff", "bmp", "pdf"]
    
    async def extract_text_with_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取文字並返回完整結果（包含元資料）"""
        logger.info(f"Mock OCR extracting text with metadata from: {file_path}")
        
        # 模擬完整的 OCR 結果
        mock_regions = [
            {
                "text": "Document Verification Test",
                "confidence": 0.95,
                "bbox": (50, 100, 350, 130),
                "level": 3
            },
            {
                "text": "Name: John Doe",
                "confidence": 0.92,
                "bbox": (50, 180, 200, 210),
                "level": 3
            },
            {
                "text": "ID: A123456789",
                "confidence": 0.88,
                "bbox": (50, 260, 250, 290),
                "level": 3
            },
            {
                "text": "Date: 2024-01-01",
                "confidence": 0.90,
                "bbox": (50, 340, 220, 370),
                "level": 3
            }
        ]
        
        full_text = "\n".join([region["text"] for region in mock_regions])
        avg_confidence = sum([region["confidence"] for region in mock_regions]) / len(mock_regions)
        
        return {
            "text": full_text,
            "confidence": avg_confidence,
            "regions": mock_regions,
            "metadata": {
                "engine": "mock_ocr",
                "language": "eng+chi_tra",
                "source_type": "test_image",
                "processing_time_ms": 100
            }
        }
