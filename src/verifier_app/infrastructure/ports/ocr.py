"""
OCR 服務介面
"""

from abc import ABC, abstractmethod
from typing import List

from ...domains.documents.entities import OcrBlock


class OcrPort(ABC):
    """OCR 服務介面"""
    
    @abstractmethod
    async def extract_text(self, file_path: str, language: str = "chi_tra+eng") -> List[OcrBlock]:
        """從影像中擷取文字與座標
        
        Args:
            file_path: 檔案路徑
            language: OCR 語言包
            
        Returns:
            OCR 區塊清單
        """
        pass
    
    @abstractmethod
    async def get_supported_formats(self) -> List[str]:
        """取得支援的檔案格式"""
        pass
