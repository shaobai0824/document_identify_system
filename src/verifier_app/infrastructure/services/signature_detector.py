from typing import Any, Dict, List

from pydantic import BaseModel


class SignatureLocation(BaseModel):
    page: int
    bbox: Dict[str, float]  # {x1, y1, x2, y2}
    similarity: float
    signature_type: str  # handwritten, digital, stamp

class SignatureDetectionResult(BaseModel):
    document_id: str
    present: bool
    locations: List[SignatureLocation]
    processing_time_ms: int

class SignatureDetector:
    async def check_document(self, document_id: str) -> SignatureDetectionResult:
        # 實際簽名檢測邏輯
        print(f"模擬簽名檢測文件：{document_id}")
        locations = [
            SignatureLocation(
                page=1,
                bbox={"x1": 400, "y1": 600, "x2": 550, "y2": 650},
                similarity=0.92,
                signature_type="handwritten"
            ),
            SignatureLocation(
                page=1,
                bbox={"x1": 100, "y1": 700, "x2": 200, "y2": 750},
                similarity=0.88,
                signature_type="stamp"
            )
        ]
        return SignatureDetectionResult(
            document_id=document_id,
            present=len(locations) > 0,
            locations=locations,
            processing_time_ms=850
        )
