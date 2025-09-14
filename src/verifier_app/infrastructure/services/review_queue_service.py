"""
人工覆核佇列服務
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ...core.config import settings
from ..database.base import get_sync_session
from ..database.models import (Document, DocumentStatus, ReviewStatus,
                               VerificationRecord, VerificationStatus)

logger = logging.getLogger(__name__)


class ReviewQueueService:
    """人工覆核佇列服務"""
    
    def __init__(self):
        """初始化覆核佇列服務"""
        self.settings = settings
    
    def get_pending_reviews(self, 
                          limit: int = 50, 
                          offset: int = 0,
                          priority_filter: Optional[str] = None) -> Dict[str, Any]:
        """取得待覆核項目列表"""
        try:
            db = get_sync_session()
            
            # 基本查詢條件
            query = db.query(VerificationRecord).join(Document).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.status == VerificationStatus.MANUAL_REVIEW
            )
            
            # 優先級過濾
            if priority_filter:
                if priority_filter == "high":
                    # 高優先級：低信心度或多個問題
                    query = query.filter(
                        or_(
                            VerificationRecord.overall_confidence < 0.5,
                            Document.status == DocumentStatus.FAILED
                        )
                    )
                elif priority_filter == "low":
                    # 低優先級：相對高信心度
                    query = query.filter(
                        VerificationRecord.overall_confidence >= 0.7
                    )
            
            # 按建立時間排序（最舊的優先）
            query = query.order_by(VerificationRecord.created_at.asc())
            
            # 分頁
            total_count = query.count()
            items = query.offset(offset).limit(limit).all()
            
            # 轉換為回應格式
            review_items = []
            for verification in items:
                document = verification.document
                
                review_items.append({
                    "verification_id": str(verification.id),
                    "document_id": str(document.id),
                    "template_id": str(verification.template_id),
                    "filename": document.original_filename,
                    "created_at": verification.created_at.isoformat(),
                    "confidence": verification.overall_confidence,
                    "status": verification.status.value,
                    "priority": self._calculate_priority(verification),
                    "estimated_review_time": self._estimate_review_time(verification),
                    "issues_summary": self._get_issues_summary(verification)
                })
            
            db.close()
            
            return {
                "items": review_items,
                "total_count": total_count,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < total_count,
                    "has_previous": offset > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get pending reviews: {e}")
            raise
    
    def get_review_details(self, verification_id: str) -> Dict[str, Any]:
        """取得覆核項目詳細資訊"""
        try:
            db = get_sync_session()
            
            verification = db.query(VerificationRecord).filter(
                VerificationRecord.id == verification_id
            ).first()
            
            if not verification:
                raise ValueError(f"Verification record not found: {verification_id}")
            
            document = verification.document
            
            # 取得 OCR 文字和區域
            ocr_regions = []
            if document.ocr_metadata and isinstance(document.ocr_metadata, dict):
                regions_data = document.ocr_metadata.get("regions", [])
                for region in regions_data:
                    ocr_regions.append({
                        "text": region.get("text", ""),
                        "confidence": region.get("confidence", 0.0),
                        "bbox": region.get("bbox", []),
                        "level": region.get("level", 0)
                    })
            
            # 分析問題
            issues = self._analyze_verification_issues(verification)
            
            # 建議動作
            suggested_actions = self._get_suggested_actions(verification)
            
            result = {
                "verification_id": str(verification.id),
                "document_id": str(document.id),
                "template_id": str(verification.template_id),
                "document_info": {
                    "filename": document.original_filename,
                    "file_size": document.file_size,
                    "content_type": document.content_type,
                    "created_at": document.created_at.isoformat(),
                    "storage_path": document.storage_path
                },
                "ocr_result": {
                    "text": document.ocr_text,
                    "confidence": document.ocr_confidence,
                    "regions": ocr_regions
                },
                "verification_result": {
                    "status": verification.status.value,
                    "overall_confidence": verification.overall_confidence,
                    "field_results": verification.field_results,
                    "extracted_data": verification.extracted_data,
                    "error_message": verification.error_message,
                    "warnings": verification.warnings
                },
                "review_info": {
                    "priority": self._calculate_priority(verification),
                    "estimated_time": self._estimate_review_time(verification),
                    "issues": issues,
                    "suggested_actions": suggested_actions,
                    "review_notes": verification.manual_review_notes,
                    "reviewed_by": verification.reviewed_by,
                    "reviewed_at": verification.reviewed_at.isoformat() if verification.reviewed_at else None
                }
            }
            
            db.close()
            return result
            
        except Exception as e:
            logger.error(f"Failed to get review details: {e}")
            raise
    
    def submit_review_decision(self, 
                             verification_id: str, 
                             decision: str,
                             reviewer_id: str,
                             notes: Optional[str] = None,
                             corrected_data: Optional[Dict[str, Any]] = None) -> bool:
        """提交覆核決定"""
        try:
            db = get_sync_session()
            
            verification = db.query(VerificationRecord).filter(
                VerificationRecord.id == verification_id
            ).first()
            
            if not verification:
                raise ValueError(f"Verification record not found: {verification_id}")
            
            # 更新覆核結果
            if decision == "approve":
                verification.status = VerificationStatus.PASS
                verification.document.status = DocumentStatus.VERIFIED
            elif decision == "reject":
                verification.status = VerificationStatus.FAIL
                verification.document.status = DocumentStatus.FAILED
            elif decision == "request_reprocess":
                # 重新處理
                verification.status = VerificationStatus.PENDING
                verification.document.status = DocumentStatus.PROCESSING
                verification.requires_manual_review = False
            else:
                raise ValueError(f"Invalid decision: {decision}")
            
            # 記錄覆核資訊
            verification.reviewed_by = reviewer_id
            verification.reviewed_at = datetime.utcnow()
            verification.manual_review_notes = notes
            verification.requires_manual_review = False
            
            # 如果有修正資料，更新提取的資料
            if corrected_data:
                verification.extracted_data.update(corrected_data)
            
            db.commit()
            db.close()
            
            logger.info(f"Review decision submitted: {verification_id} -> {decision} by {reviewer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit review decision: {e}")
            db.rollback()
            raise
    
    def get_review_statistics(self, days: int = 30) -> Dict[str, Any]:
        """取得覆核統計資訊"""
        try:
            db = get_sync_session()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 總體統計
            total_reviews = db.query(VerificationRecord).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.created_at >= cutoff_date
            ).count()
            
            pending_reviews = db.query(VerificationRecord).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.status == VerificationStatus.MANUAL_REVIEW
            ).count()
            
            completed_reviews = db.query(VerificationRecord).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.reviewed_at >= cutoff_date,
                VerificationRecord.reviewed_at.isnot(None)
            ).count()
            
            # 按決定類型統計
            approved_count = db.query(VerificationRecord).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.status == VerificationStatus.PASS,
                VerificationRecord.reviewed_at >= cutoff_date
            ).count()
            
            rejected_count = db.query(VerificationRecord).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.status == VerificationStatus.FAIL,
                VerificationRecord.reviewed_at >= cutoff_date
            ).count()
            
            # 平均處理時間
            avg_processing_time = db.query(
                db.func.avg(VerificationRecord.processing_time_ms)
            ).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.reviewed_at >= cutoff_date,
                VerificationRecord.processing_time_ms.isnot(None)
            ).scalar()
            
            # 按優先級統計
            high_priority = db.query(VerificationRecord).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.status == VerificationStatus.MANUAL_REVIEW,
                VerificationRecord.overall_confidence < 0.5
            ).count()
            
            stats = {
                "period_days": days,
                "total_reviews": total_reviews,
                "pending_reviews": pending_reviews,
                "completed_reviews": completed_reviews,
                "completion_rate": (completed_reviews / total_reviews) if total_reviews > 0 else 0,
                "decisions": {
                    "approved": approved_count,
                    "rejected": rejected_count,
                    "approval_rate": (approved_count / completed_reviews) if completed_reviews > 0 else 0
                },
                "performance": {
                    "avg_processing_time_ms": avg_processing_time,
                    "high_priority_pending": high_priority
                }
            }
            
            db.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get review statistics: {e}")
            return {}
    
    def _calculate_priority(self, verification: VerificationRecord) -> str:
        """計算覆核優先級"""
        confidence = verification.overall_confidence or 0.0
        
        if confidence < 0.3:
            return "high"
        elif confidence < 0.7:
            return "medium"
        else:
            return "low"
    
    def _estimate_review_time(self, verification: VerificationRecord) -> int:
        """估計覆核時間（分鐘）"""
        base_time = 5  # 基本時間 5 分鐘
        
        # 根據信心度調整
        confidence = verification.overall_confidence or 0.0
        if confidence < 0.3:
            base_time += 10
        elif confidence < 0.5:
            base_time += 5
        
        # 根據欄位數量調整
        field_count = len(verification.field_results) if verification.field_results else 0
        base_time += field_count * 1
        
        return base_time
    
    def _get_issues_summary(self, verification: VerificationRecord) -> List[str]:
        """取得問題摘要"""
        issues = []
        
        confidence = verification.overall_confidence or 0.0
        if confidence < 0.5:
            issues.append("Low overall confidence")
        
        if verification.error_message:
            issues.append("Processing error occurred")
        
        if verification.warnings:
            issues.append(f"{len(verification.warnings)} warnings")
        
        # 檢查欄位結果
        if verification.field_results:
            failed_fields = [
                field for field, result in verification.field_results.items()
                if not result
            ]
            if failed_fields:
                issues.append(f"{len(failed_fields)} fields failed validation")
        
        return issues
    
    def _analyze_verification_issues(self, verification: VerificationRecord) -> List[Dict[str, Any]]:
        """分析驗證問題"""
        issues = []
        
        # 信心度問題
        confidence = verification.overall_confidence or 0.0
        if confidence < 0.5:
            issues.append({
                "type": "low_confidence",
                "severity": "high" if confidence < 0.3 else "medium",
                "description": f"Overall confidence is low ({confidence:.2%})",
                "suggestion": "Verify OCR accuracy and check for image quality issues"
            })
        
        # 處理錯誤
        if verification.error_message:
            issues.append({
                "type": "processing_error",
                "severity": "high",
                "description": verification.error_message,
                "suggestion": "Check error details and consider reprocessing"
            })
        
        # 欄位驗證問題
        if verification.field_results:
            for field, result in verification.field_results.items():
                if not result:
                    issues.append({
                        "type": "field_validation_failed",
                        "severity": "medium",
                        "description": f"Field '{field}' failed validation",
                        "suggestion": f"Manually verify the '{field}' field value"
                    })
        
        return issues
    
    def _get_suggested_actions(self, verification: VerificationRecord) -> List[str]:
        """取得建議動作"""
        actions = []
        
        confidence = verification.overall_confidence or 0.0
        
        if confidence < 0.3:
            actions.append("Consider rejecting due to very low confidence")
            actions.append("Check if document image quality is adequate")
        elif confidence < 0.5:
            actions.append("Carefully review extracted data")
            actions.append("Consider requesting reprocessing with different settings")
        else:
            actions.append("Review and approve if data looks correct")
        
        if verification.error_message:
            actions.append("Investigate processing error")
            actions.append("Consider reprocessing with different template")
        
        return actions
    
    def batch_assign_reviews(self, reviewer_id: str, count: int, priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """批次分派覆核任務"""
        try:
            db = get_sync_session()
            
            query = db.query(VerificationRecord).filter(
                VerificationRecord.requires_manual_review == True,
                VerificationRecord.review_status == ReviewStatus.PENDING
            )
            
            if priority_filter == "high":
                query = query.filter(VerificationRecord.overall_confidence < 0.5)
            elif priority_filter == "low":
                query = query.filter(VerificationRecord.overall_confidence >= 0.7)
            
            records_to_assign = query.order_by(VerificationRecord.created_at.asc()).limit(count).all()
            
            assigned_items = []
            for record in records_to_assign:
                record.assigned_to = reviewer_id
                record.assigned_at = datetime.utcnow()
                record.review_status = ReviewStatus.ASSIGNED
                assigned_items.append({"verification_id": str(record.id), "document_id": str(record.document_id)})
            
            db.commit()
            db.close()
            
            logger.info(f"Assigned {len(assigned_items)} review items to {reviewer_id}")
            return assigned_items
            
        except Exception as e:
            logger.error(f"Failed to batch assign reviews: {e}")
            db.rollback()
            raise
    
    def get_reviewer_workload(self, reviewer_id: str) -> Dict[str, Any]:
        """取得審核者工作負載"""
        try:
            db = get_sync_session()
            
            pending_count = db.query(VerificationRecord).filter(
                VerificationRecord.assigned_to == reviewer_id,
                VerificationRecord.review_status == ReviewStatus.ASSIGNED
            ).count()
            
            in_progress_count = db.query(VerificationRecord).filter(
                VerificationRecord.assigned_to == reviewer_id,
                VerificationRecord.review_status == ReviewStatus.IN_PROGRESS
            ).count()
            
            completed_today = db.query(VerificationRecord).filter(
                VerificationRecord.assigned_to == reviewer_id,
                VerificationRecord.review_status == ReviewStatus.COMPLETED,
                VerificationRecord.reviewed_at >= datetime.utcnow() - timedelta(days=1)
            ).count()
            
            avg_processing_time_ms = db.query(
                db.func.avg(VerificationRecord.processing_time_ms)
            ).filter(
                VerificationRecord.assigned_to == reviewer_id,
                VerificationRecord.review_status == ReviewStatus.COMPLETED,
                VerificationRecord.processing_time_ms.isnot(None)
            ).scalar()
            
            workload_status = "light"
            if pending_count + in_progress_count > 10:
                workload_status = "moderate"
            if pending_count + in_progress_count > 25:
                workload_status = "heavy"
            
            db.close()
            
            return {
                "reviewer_id": reviewer_id,
                "pending_count": pending_count,
                "in_progress_count": in_progress_count,
                "completed_today": completed_today,
                "avg_processing_time_min": (avg_processing_time_ms / 60000) if avg_processing_time_ms else 0,
                "workload_status": workload_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get reviewer workload: {e}")
            raise
