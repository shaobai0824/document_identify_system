"""
自動分類與條碼解析路由
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class ClassificationCandidate(BaseModel):
    template_id: str
    template_name: str
    confidence: float
    match_features: List[str]


class ClassificationResponse(BaseModel):
    candidates: List[ClassificationCandidate]
    recommended_template_id: Optional[str]
    processing_time_ms: int


class BarcodeResult(BaseModel):
    symbology: str  # QR, Code128, Code39, EAN13, etc.
    value: str
    bbox: BoundingBox
    confidence: float


class BarcodeResponse(BaseModel):
    barcodes: List[BarcodeResult]
    processing_time_ms: int


@router.post("/classification", response_model=ClassificationResponse)
async def classify_document(file: UploadFile = File(...)):
    """依影像進行範本分類"""
    try:
        # 驗證檔案
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "application/pdf"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.content_type}"
            )
        
        # 讀取檔案內容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # TODO: 實作實際的文件分類邏輯
        # classifier = DocumentClassifier()
        # result = await classifier.classify(file_content)
        
        # 模擬分類結果
        candidates = [
            ClassificationCandidate(
                template_id="tpl_001",
                template_name="身分證範本",
                confidence=0.92,
                match_features=["text_pattern", "layout_structure", "size_ratio"]
            ),
            ClassificationCandidate(
                template_id="tpl_002",
                template_name="護照範本",
                confidence=0.78,
                match_features=["text_pattern", "color_scheme"]
            ),
            ClassificationCandidate(
                template_id="tpl_003",
                template_name="駕照範本",
                confidence=0.65,
                match_features=["layout_structure"]
            )
        ]
        
        # 推薦信心度最高的範本
        recommended_template_id = candidates[0].template_id if candidates and candidates[0].confidence > 0.8 else None
        
        response = ClassificationResponse(
            candidates=candidates,
            recommended_template_id=recommended_template_id,
            processing_time_ms=450
        )
        
        logger.info(f"Classified document: {file.filename}, recommended: {recommended_template_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to classify document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/barcodes/decode", response_model=BarcodeResponse)
async def decode_barcodes(file: UploadFile = File(...)):
    """解析條碼和 QR 碼"""
    try:
        # 驗證檔案
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        allowed_types = ["image/png", "image/jpeg", "image/jpg"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type for barcode detection: {file.content_type}"
            )
        
        # 讀取檔案內容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # TODO: 實作實際的條碼解析邏輯
        # barcode_decoder = BarcodeDecoder()
        # result = await barcode_decoder.decode(file_content)
        
        # 模擬條碼解析結果
        barcodes = [
            BarcodeResult(
                symbology="QR",
                value="https://example.com/verify/abc123",
                bbox=BoundingBox(x1=50, y1=50, x2=150, y2=150),
                confidence=0.98
            ),
            BarcodeResult(
                symbology="Code128",
                value="A123456789",
                bbox=BoundingBox(x1=200, y1=300, x2=400, y2=350),
                confidence=0.95
            )
        ]
        
        response = BarcodeResponse(
            barcodes=barcodes,
            processing_time_ms=200
        )
        
        logger.info(f"Decoded {len(barcodes)} barcodes from {file.filename}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to decode barcodes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/classification/batch")
async def classify_documents_batch(files: List[UploadFile] = File(...)):
    """批次分類多個文件"""
    try:
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed per batch")
        
        results = []
        for file in files:
            try:
                # 重複使用單檔分類邏輯
                classification_result = await classify_document(file)
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "result": classification_result
                })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })
        
        logger.info(f"Batch classified {len(files)} documents")
        return {"results": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to classify documents batch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/classification/templates")
async def get_classification_templates():
    """取得可用於分類的範本列表"""
    try:
        # TODO: 從資料庫查詢啟用的範本
        templates = [
            {"id": "tpl_001", "name": "身分證範本", "category": "identity"},
            {"id": "tpl_002", "name": "護照範本", "category": "identity"},
            {"id": "tpl_003", "name": "駕照範本", "category": "license"},
            {"id": "tpl_004", "name": "銀行對帳單範本", "category": "financial"}
        ]
        
        return {"templates": templates}
        
    except Exception as e:
        logger.error(f"Failed to get classification templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
