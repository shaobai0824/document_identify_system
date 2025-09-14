"""
人工覆核相關 API 路由
"""

import logging
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Query
from pydantic import BaseModel

from ...infrastructure.services.review_queue_service import ReviewQueueService

logger = logging.getLogger(__name__)
router = APIRouter()


class ReviewDecisionRequest(BaseModel):
    """覆核決定請求"""
    decision: str  # approve, reject, request_reprocess
    reviewer_id: str
    notes: Optional[str] = None
    corrected_data: Optional[dict] = None


@router.get("/queue")
async def get_review_queue(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    priority: Optional[str] = Query(None, regex="^(high|medium|low)$")
):
    """
    取得人工覆核佇列
    
    返回待覆核的文件列表，支援分頁和優先級過濾
    """
    try:
        service = ReviewQueueService()
        result = service.get_pending_reviews(
            limit=limit,
            offset=offset,
            priority_filter=priority
        )
        return result
        
    except Exception as e:
        logger.error(f"Failed to get review queue: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/items/{verification_id}")
async def get_review_item(verification_id: str):
    """
    取得覆核項目詳細資訊
    
    包含文件資訊、OCR 結果、驗證結果和建議動作
    """
    try:
        service = ReviewQueueService()
        result = service.get_review_details(verification_id)
        return result
        
    except ValueError as e:
        logger.warning(f"Review item not found: {verification_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get review item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/items/{verification_id}/decision")
async def submit_review_decision(
    verification_id: str,
    request: ReviewDecisionRequest
):
    """
    提交覆核決定
    
    支援核准、拒絕或要求重新處理
    """
    try:
        # 驗證決定類型
        if request.decision not in ["approve", "reject", "request_reprocess"]:
            raise HTTPException(status_code=400, detail="Invalid decision type")
        
        service = ReviewQueueService()
        success = service.submit_review_decision(
            verification_id=verification_id,
            decision=request.decision,
            reviewer_id=request.reviewer_id,
            notes=request.notes,
            corrected_data=request.corrected_data
        )
        
        if success:
            return {
                "verification_id": verification_id,
                "decision": request.decision,
                "status": "submitted",
                "message": f"Review decision '{request.decision}' has been recorded"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to submit decision")
        
    except ValueError as e:
        logger.warning(f"Invalid review decision: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit review decision: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics")
async def get_review_statistics(
    days: int = Query(30, ge=1, le=365)
):
    """
    取得覆核統計資訊
    
    包含處理量、完成率、平均處理時間等指標
    """
    try:
        service = ReviewQueueService()
        stats = service.get_review_statistics(days=days)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get review statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/batch-assign")
async def batch_assign_reviews(
    reviewer_id: str = Form(...),
    count: int = Form(10, ge=1, le=50),
    priority: Optional[str] = Form(None, regex="^(high|medium|low)$")
):
    """
    批次分派覆核任務
    
    將指定數量的待覆核項目分派給審核者
    """
    try:
        service = ReviewQueueService()
        assigned_items = service.batch_assign_reviews(
            reviewer_id=reviewer_id,
            count=count,
            priority_filter=priority
        )
        
        return {
            "assigned_count": len(assigned_items),
            "reviewer_id": reviewer_id,
            "assigned_items": assigned_items,
            "status": "assigned",
            "message": f"{len(assigned_items)} review items assigned to {reviewer_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to batch assign reviews: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/reviewers/{reviewer_id}/workload")
async def get_reviewer_workload(reviewer_id: str):
    """
    取得審核者工作負載
    
    顯示分派給特定審核者的待處理項目
    """
    try:
        service = ReviewQueueService()
        workload = service.get_reviewer_workload(reviewer_id)
        return workload
        
    except Exception as e:
        logger.error(f"Failed to get reviewer workload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
