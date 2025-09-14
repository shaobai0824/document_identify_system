"""
Webhook 服務實作
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from ...core.config import settings
from ..database.base import get_sync_session
from ..database.models import Document, VerificationRecord, WebhookDelivery

logger = logging.getLogger(__name__)


class WebhookService:
    """Webhook 服務"""
    
    def __init__(self):
        """初始化 Webhook 服務"""
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def send_document_processed(self, document_id: str, webhook_url: str) -> bool:
        """發送文件處理完成 Webhook"""
        try:
            db = get_sync_session()
            
            # 取得文件資訊
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document not found for webhook: {document_id}")
                return False
            
            # 取得驗證結果
            verification = db.query(VerificationRecord).filter(
                VerificationRecord.document_id == document.id
            ).first()
            
            # 建立 Webhook 載荷
            payload = {
                "event": "document.processed",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "document_id": str(document.id),
                    "filename": document.original_filename,
                    "status": document.status.value,
                    "processing_time_ms": None,
                    "ocr_result": {
                        "text_length": len(document.ocr_text) if document.ocr_text else 0,
                        "confidence": document.ocr_confidence
                    } if document.ocr_text else None,
                    "verification_result": {
                        "verification_id": str(verification.id),
                        "status": verification.status.value,
                        "confidence": verification.overall_confidence,
                        "requires_manual_review": verification.requires_manual_review
                    } if verification else None
                }
            }
            
            # 發送 Webhook
            success = await self._deliver_webhook(webhook_url, payload, document_id, "document.processed")
            
            db.close()
            return success
            
        except Exception as e:
            logger.error(f"Failed to send document processed webhook: {e}")
            return False
    
    async def send_verification_completed(self, verification_id: str, webhook_url: str) -> bool:
        """發送驗證完成 Webhook"""
        try:
            db = get_sync_session()
            
            verification = db.query(VerificationRecord).filter(
                VerificationRecord.id == verification_id
            ).first()
            
            if not verification:
                logger.error(f"Verification record not found: {verification_id}")
                return False
            
            payload = {
                "event": "verification.completed",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "verification_id": str(verification.id),
                    "document_id": str(verification.document_id),
                    "template_id": str(verification.template_id),
                    "status": verification.status.value,
                    "confidence": verification.overall_confidence,
                    "requires_manual_review": verification.requires_manual_review,
                    "extracted_data": verification.extracted_data,
                    "field_results": verification.field_results
                }
            }
            
            success = await self._deliver_webhook(webhook_url, payload, verification_id, "verification.completed")
            
            db.close()
            return success
            
        except Exception as e:
            logger.error(f"Failed to send verification completed webhook: {e}")
            return False
    
    async def send_manual_review_required(self, document_id: str, webhook_url: str) -> bool:
        """發送需要人工審核 Webhook"""
        try:
            payload = {
                "event": "manual_review.required",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "document_id": document_id,
                    "message": "Document requires manual review",
                    "review_url": f"{self.settings.app_base_url}/review/{document_id}"
                }
            }
            
            return await self._deliver_webhook(webhook_url, payload, document_id, "manual_review.required")
            
        except Exception as e:
            logger.error(f"Failed to send manual review required webhook: {e}")
            return False
    
    async def _deliver_webhook(self, url: str, payload: Dict[str, Any], resource_id: str, event_type: str) -> bool:
        """發送 Webhook 並記錄結果"""
        delivery_id = None
        
        try:
            # 建立發送記錄
            db = get_sync_session()
            
            delivery = WebhookDelivery(
                webhook_url=url,
                event_type=event_type,
                payload=payload,
                resource_id=resource_id,
                status="pending"
            )
            
            db.add(delivery)
            db.commit()
            delivery_id = delivery.id
            
            # 準備標頭
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"{self.settings.app_name}/{self.settings.version}",
                "X-Webhook-Event": event_type,
                "X-Webhook-Delivery": str(delivery_id)
            }
            
            # 發送請求
            response = await self.client.post(
                url,
                json=payload,
                headers=headers
            )
            
            # 更新發送記錄
            delivery.status = "delivered" if response.status_code < 400 else "failed"
            delivery.response_status = response.status_code
            delivery.response_headers = dict(response.headers)
            delivery.response_body = response.text[:1000]  # 限制回應長度
            delivery.delivered_at = datetime.utcnow()
            
            db.commit()
            db.close()
            
            if response.status_code < 400:
                logger.info(f"Webhook delivered successfully: {url} (status: {response.status_code})")
                return True
            else:
                logger.warning(f"Webhook delivery failed: {url} (status: {response.status_code})")
                return False
                
        except Exception as e:
            logger.error(f"Webhook delivery error: {e}")
            
            # 更新失敗記錄
            if delivery_id:
                try:
                    db = get_sync_session()
                    delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
                    if delivery:
                        delivery.status = "failed"
                        delivery.error_message = str(e)
                        delivery.delivered_at = datetime.utcnow()
                        db.commit()
                    db.close()
                except Exception:
                    pass
            
            return False
    
    async def retry_failed_webhooks(self, max_retries: int = 3) -> Dict[str, int]:
        """重試失敗的 Webhook"""
        try:
            db = get_sync_session()
            
            # 查找失敗的 Webhook
            failed_deliveries = db.query(WebhookDelivery).filter(
                WebhookDelivery.status == "failed",
                WebhookDelivery.retry_count < max_retries
            ).limit(100).all()
            
            retry_count = 0
            success_count = 0
            
            for delivery in failed_deliveries:
                try:
                    # 重新發送
                    success = await self._deliver_webhook(
                        delivery.webhook_url,
                        delivery.payload,
                        delivery.resource_id,
                        delivery.event_type
                    )
                    
                    delivery.retry_count += 1
                    
                    if success:
                        success_count += 1
                    
                    retry_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to retry webhook {delivery.id}: {e}")
                    delivery.retry_count += 1
            
            db.commit()
            db.close()
            
            logger.info(f"Webhook retry completed: {retry_count} attempted, {success_count} succeeded")
            
            return {
                "attempted": retry_count,
                "succeeded": success_count,
                "failed": retry_count - success_count
            }
            
        except Exception as e:
            logger.error(f"Webhook retry process failed: {e}")
            return {"attempted": 0, "succeeded": 0, "failed": 0}
    
    async def get_webhook_statistics(self) -> Dict[str, Any]:
        """取得 Webhook 統計資訊"""
        try:
            db = get_sync_session()
            
            # 統計各狀態的數量
            stats = {}
            
            status_counts = db.query(
                WebhookDelivery.status, 
                db.func.count(WebhookDelivery.id)
            ).group_by(WebhookDelivery.status).all()
            
            stats["by_status"] = {status: count for status, count in status_counts}
            
            # 統計事件類型
            event_counts = db.query(
                WebhookDelivery.event_type,
                db.func.count(WebhookDelivery.id)
            ).group_by(WebhookDelivery.event_type).all()
            
            stats["by_event_type"] = {event_type: count for event_type, count in event_counts}
            
            # 總數
            total_deliveries = db.query(WebhookDelivery).count()
            stats["total_deliveries"] = total_deliveries
            
            # 成功率
            successful_deliveries = db.query(WebhookDelivery).filter(
                WebhookDelivery.status == "delivered"
            ).count()
            
            stats["success_rate"] = (successful_deliveries / total_deliveries) if total_deliveries > 0 else 0
            
            db.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get webhook statistics: {e}")
            return {}
    
    async def cleanup(self):
        """清理資源"""
        await self.client.aclose()
