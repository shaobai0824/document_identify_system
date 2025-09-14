"""
OCR 引擎適配器實作
"""

import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter

from ..ports.ocr import OcrPort

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR 結果資料類別"""
    text: str
    confidence: float
    regions: List[Dict[str, Any]]  # 文字區域資訊
    metadata: Dict[str, Any]       # 額外資訊（處理時間、引擎版本等）


@dataclass
class TextRegion:
    """文字區域資料類別"""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    level: int  # Tesseract 層級 (word, line, paragraph, block)


class BaseOCRAdapter(ABC):
    """OCR 適配器基礎類別"""
    
    @abstractmethod
    async def extract_text(self, image_path: str) -> OCRResult:
        """提取文字"""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """取得支援的檔案格式"""
        pass


class TesseractAdapter(BaseOCRAdapter, OcrPort):
    """Tesseract OCR 適配器"""
    
    def __init__(self, 
                 language: str = "eng+chi_tra",
                 psm: int = 6,
                 oem: int = 3,
                 config_options: Optional[Dict[str, Any]] = None):
        """
        初始化 Tesseract 適配器
        
        Args:
            language: OCR 語言 (eng+chi_tra 表示英文+繁體中文)
            psm: Page Segmentation Mode (0-13)
            oem: OCR Engine Mode (0-3)
            config_options: 額外配置選項
        """
        self.language = language
        self.psm = psm
        self.oem = oem
        self.config_options = config_options or {}
        
        # 驗證 Tesseract 是否可用
        try:
            pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {pytesseract.get_tesseract_version()}")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            raise RuntimeError("Tesseract OCR engine not found")
    
    def get_supported_formats(self) -> List[str]:
        """取得支援的檔案格式"""
        return ["jpg", "jpeg", "png", "tiff", "bmp", "pdf"]
    
    async def extract_text(self, file_path: str) -> OCRResult:
        """提取文字"""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.pdf':
                return await self._process_pdf(file_path)
            else:
                return await self._process_image(file_path)
                
        except Exception as e:
            logger.error(f"OCR extraction failed for {file_path}: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                regions=[],
                metadata={"error": str(e), "engine": "tesseract"}
            )
    
    async def _process_pdf(self, pdf_path: Path) -> OCRResult:
        """處理 PDF 檔案"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 轉換 PDF 為圖片
            images = convert_from_path(str(pdf_path), dpi=300)
            
            all_text = []
            all_regions = []
            total_confidence = 0.0
            
            for i, image in enumerate(images):
                # 儲存臨時圖片
                temp_image_path = Path(temp_dir) / f"page_{i}.png"
                image.save(temp_image_path)
                
                # 處理圖片
                page_result = await self._process_image(temp_image_path)
                
                if page_result.text.strip():
                    all_text.append(f"=== Page {i+1} ===\n{page_result.text}")
                    all_regions.extend(page_result.regions)
                    total_confidence += page_result.confidence
            
            avg_confidence = total_confidence / len(images) if images else 0.0
            
            return OCRResult(
                text="\n\n".join(all_text),
                confidence=avg_confidence,
                regions=all_regions,
                metadata={
                    "engine": "tesseract",
                    "pages": len(images),
                    "source_type": "pdf"
                }
            )
    
    async def _process_image(self, image_path: Path) -> OCRResult:
        """處理圖片檔案"""
        # 前處理圖片
        processed_image = self._preprocess_image(str(image_path))
        
        # 建立 Tesseract 配置
        config = self._build_tesseract_config()
        
        # 提取文字和詳細資訊
        data = pytesseract.image_to_data(
            processed_image,
            lang=self.language,
            config=config,
            output_type=pytesseract.Output.DICT
        )
        
        # 提取純文字
        text = pytesseract.image_to_string(
            processed_image,
            lang=self.language,
            config=config
        )
        
        # 處理區域資訊
        regions = self._extract_regions(data)
        
        # 計算平均信心度
        confidences = [r.confidence for r in regions if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=text.strip(),
            confidence=avg_confidence / 100.0,  # Tesseract 返回 0-100，正規化為 0-1
            regions=[{
                "text": r.text,
                "confidence": r.confidence / 100.0,
                "bbox": r.bbox,
                "level": r.level
            } for r in regions],
            metadata={
                "engine": "tesseract",
                "language": self.language,
                "psm": self.psm,
                "oem": self.oem,
                "source_type": "image"
            }
        )
    
    def _preprocess_image(self, image_path: str) -> Image.Image:
        """圖片前處理以提升 OCR 準確度"""
        # 使用 PIL 載入圖片
        image = Image.open(image_path)
        
        # 轉換為 RGB（如果需要）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 使用 OpenCV 進行更進階的前處理
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 轉為灰階
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # 降噪
        denoised = cv2.medianBlur(gray, 3)
        
        # 自適應閾值化
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 形態學操作（可選）
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 轉回 PIL 格式
        return Image.fromarray(processed)
    
    def _build_tesseract_config(self) -> str:
        """建立 Tesseract 配置字串"""
        config_parts = [
            f"--psm {self.psm}",
            f"--oem {self.oem}"
        ]
        
        # 添加自訂配置選項
        for key, value in self.config_options.items():
            config_parts.append(f"-c {key}={value}")
        
        return " ".join(config_parts)
    
    def _extract_regions(self, data: Dict[str, List]) -> List[TextRegion]:
        """從 Tesseract 資料中提取文字區域"""
        regions = []
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            # 過濾空文字和低信心度結果
            if text and conf > 0:
                bbox = (
                    data['left'][i],
                    data['top'][i],
                    data['left'][i] + data['width'][i],
                    data['top'][i] + data['height'][i]
                )
                
                regions.append(TextRegion(
                    text=text,
                    confidence=conf,
                    bbox=bbox,
                    level=data['level'][i]
                ))
        
        return regions


class GoogleVisionAdapter(BaseOCRAdapter, OcrPort):
    """Google Vision API 適配器（可選實作）"""
    
    def __init__(self, credentials_path: str):
        """初始化 Google Vision 適配器"""
        self.credentials_path = credentials_path
        # TODO: 實作 Google Vision API 整合
        raise NotImplementedError("Google Vision adapter not implemented yet")
    
    def get_supported_formats(self) -> List[str]:
        return ["jpg", "jpeg", "png", "tiff", "bmp", "pdf"]
    
    async def extract_text(self, image_path: str) -> OCRResult:
        # TODO: 實作 Google Vision API 調用
        raise NotImplementedError("Google Vision adapter not implemented yet")


class AzureOCRAdapter(BaseOCRAdapter, OcrPort):
    """Azure Computer Vision API 適配器（可選實作）"""
    
    def __init__(self, endpoint: str, subscription_key: str):
        """初始化 Azure OCR 適配器"""
        self.endpoint = endpoint
        self.subscription_key = subscription_key
        # TODO: 實作 Azure Computer Vision API 整合
        raise NotImplementedError("Azure OCR adapter not implemented yet")
    
    def get_supported_formats(self) -> List[str]:
        return ["jpg", "jpeg", "png", "tiff", "bmp", "pdf"]
    
    async def extract_text(self, image_path: str) -> OCRResult:
        # TODO: 實作 Azure Computer Vision API 調用
        raise NotImplementedError("Azure OCR adapter not implemented yet")


# OCR 適配器工廠
class OCRAdapterFactory:
    """OCR 適配器工廠"""
    
    _adapters = {
        "tesseract": TesseractAdapter,
        "google_vision": GoogleVisionAdapter,
        "azure": AzureOCRAdapter
    }
    
    @classmethod
    def create_adapter(cls, provider: str, **kwargs) -> BaseOCRAdapter:
        """建立 OCR 適配器"""
        if provider not in cls._adapters:
            raise ValueError(f"Unsupported OCR provider: {provider}")
        
        return cls._adapters[provider](**kwargs)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """取得可用的 OCR 提供者"""
        return list(cls._adapters.keys())
