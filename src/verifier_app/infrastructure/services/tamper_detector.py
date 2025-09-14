from typing import Any, Dict, List

from pydantic import BaseModel


class TamperFinding(BaseModel):
    type: str  # content_modified, page_reordered, watermark_removed, metadata_altered
    severity: str  # low, medium, high, critical
    description: str
    evidence: Dict[str, Any]
    confidence: float

class TamperCheckResponse(BaseModel):
    document_id: str
    is_tampered: bool
    findings: List[TamperFinding]
    integrity_score: float  # 0.0-1.0
    processing_time_ms: int

class TamperDetector:
    async def analyze_document(self, document_id: str) -> TamperCheckResponse:
        # 實際篡改檢測邏輯
        print(f"模擬篡改檢測文件：{document_id}")
        findings = [
            TamperFinding(
                type="metadata_altered",
                severity="medium",
                description="Document creation timestamp appears to be modified",
                evidence={
                    "original_timestamp": "2025-01-01T10:00:00Z",
                    "current_timestamp": "2025-01-07T15:30:00Z",
                    "modification_detected": True
                },
                confidence=0.85
            )
        ]
        integrity_score = 0.75
        return TamperCheckResponse(
            document_id=document_id,
            is_tampered=len(findings) > 0,
            findings=findings,
            integrity_score=integrity_score,
            processing_time_ms=1200
        )
