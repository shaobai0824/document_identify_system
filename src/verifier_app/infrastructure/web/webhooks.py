"""
Webhook 管理路由
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

router = APIRouter()
logger = logging.getLogger(__name__)


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: List[str] = Field(..., min_items=1)
    secret: Optional[str] = None
    description: Optional[str] = None
    active: bool = True


class WebhookUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class Webhook(BaseModel):
    id: str
    url: str
    events: List[str]
    secret_preview: str  # 只顯示前幾個字符
    description: Optional[str]
    active: bool
    created_at: str
    updated_at: Optional[str]
    last_delivery_at: Optional[str]
    delivery_count: int
    failure_count: int


class WebhookDelivery(BaseModel):
    id: str
    webhook_id: str
    event_type: str
    status: str  # pending, delivered, failed, retrying
    http_status: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    attempt_count: int
    created_at: str
    delivered_at: Optional[str]
    next_retry_at: Optional[str]


# 模擬儲存
webhooks_db = {}
deliveries_db = {}


@router.post("/webhooks", response_model=Webhook, status_code=201)
async def create_webhook(webhook_data: WebhookCreate):
    """建立 Webhook"""
    try:
        # 驗證事件類型
        valid_events = [
            "document.queued", "document.processing", "document.passed", 
            "document.failed", "document.review_required", "review.decided",
            "template.created", "template.updated", "template.deleted"
        ]
        
        for event in webhook_data.events:
            if event not in valid_events:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid event type: {event}. Valid events: {', '.join(valid_events)}"
                )
        
        # 生成 Webhook
        webhook_id = str(uuid4())
        secret = webhook_data.secret or generate_webhook_secret()
        
        webhook = {
            "id": webhook_id,
            "url": str(webhook_data.url),
            "events": webhook_data.events,
            "secret": secret,
            "description": webhook_data.description,
            "active": webhook_data.active,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": None,
            "last_delivery_at": None,
            "delivery_count": 0,
            "failure_count": 0
        }
        
        webhooks_db[webhook_id] = webhook
        
        # 回應時隱藏完整密鑰
        response_webhook = Webhook(
            **webhook,
            secret_preview=secret[:8] + "..." if len(secret) > 8 else secret
        )
        
        logger.info(f"Created webhook {webhook_id} for {webhook_data.url}")
        return response_webhook
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/webhooks", response_model=List[Webhook])
async def list_webhooks(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0
):
    """列出 Webhooks"""
    try:
        webhooks = list(webhooks_db.values())
        
        if active_only:
            webhooks = [w for w in webhooks if w["active"]]
        
        # 分頁
        total = len(webhooks)
        webhooks = webhooks[offset:offset + limit]
        
        # 隱藏密鑰
        response_webhooks = []
        for webhook in webhooks:
            secret = webhook["secret"]
            response_webhook = Webhook(
                **webhook,
                secret_preview=secret[:8] + "..." if len(secret) > 8 else secret
            )
            response_webhooks.append(response_webhook)
        
        return response_webhooks
        
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/webhooks/{webhook_id}", response_model=Webhook)
async def get_webhook(webhook_id: str):
    """取得 Webhook 詳情"""
    try:
        webhook = webhooks_db.get(webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        secret = webhook["secret"]
        response_webhook = Webhook(
            **webhook,
            secret_preview=secret[:8] + "..." if len(secret) > 8 else secret
        )
        
        return response_webhook
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/webhooks/{webhook_id}", response_model=Webhook)
async def update_webhook(webhook_id: str, webhook_data: WebhookUpdate):
    """更新 Webhook"""
    try:
        webhook = webhooks_db.get(webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # 更新欄位
        if webhook_data.url is not None:
            webhook["url"] = str(webhook_data.url)
        if webhook_data.events is not None:
            webhook["events"] = webhook_data.events
        if webhook_data.secret is not None:
            webhook["secret"] = webhook_data.secret
        if webhook_data.description is not None:
            webhook["description"] = webhook_data.description
        if webhook_data.active is not None:
            webhook["active"] = webhook_data.active
        
        webhook["updated_at"] = datetime.utcnow().isoformat()
        
        secret = webhook["secret"]
        response_webhook = Webhook(
            **webhook,
            secret_preview=secret[:8] + "..." if len(secret) > 8 else secret
        )
        
        logger.info(f"Updated webhook {webhook_id}")
        return response_webhook
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: str):
    """刪除 Webhook"""
    try:
        if webhook_id not in webhooks_db:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        del webhooks_db[webhook_id]
        
        logger.info(f"Deleted webhook {webhook_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """測試 Webhook 連接"""
    try:
        webhook = webhooks_db.get(webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # TODO: 實作實際的 Webhook 測試
        # webhook_dispatcher = WebhookDispatcher()
        # result = await webhook_dispatcher.test_webhook(webhook)
        
        # 模擬測試結果
        test_event = {
            "id": str(uuid4()),
            "type": "webhook.test",
            "created_at": datetime.utcnow().isoformat(),
            "data": {"message": "This is a test webhook"}
        }
        
        logger.info(f"Testing webhook {webhook_id}")
        
        return {
            "webhook_id": webhook_id,
            "test_event": test_event,
            "status": "sent",
            "message": "Test webhook sent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/webhooks/{webhook_id}/deliveries", response_model=List[WebhookDelivery])
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
):
    """取得 Webhook 投遞記錄"""
    try:
        webhook = webhooks_db.get(webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # 過濾該 webhook 的投遞記錄
        deliveries = [d for d in deliveries_db.values() if d["webhook_id"] == webhook_id]
        
        if status:
            deliveries = [d for d in deliveries if d["status"] == status]
        
        # 按時間排序（最新的在前）
        deliveries.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 分頁
        deliveries = deliveries[offset:offset + limit]
        
        return [WebhookDelivery(**d) for d in deliveries]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deliveries for webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhooks/rotate-secret")
async def rotate_webhook_secret(webhook_id: str):
    """輪替 Webhook 密鑰"""
    try:
        webhook = webhooks_db.get(webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # 生成新密鑰
        new_secret = generate_webhook_secret()
        old_secret_preview = webhook["secret"][:8] + "..."
        
        webhook["secret"] = new_secret
        webhook["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Rotated secret for webhook {webhook_id}")
        
        return {
            "webhook_id": webhook_id,
            "old_secret_preview": old_secret_preview,
            "new_secret_preview": new_secret[:8] + "...",
            "rotated_at": webhook["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rotate secret for webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def generate_webhook_secret() -> str:
    """生成 Webhook 密鑰"""
    import secrets
    return secrets.token_urlsafe(32)


def generate_webhook_signature(payload: str, secret: str) -> str:
    """生成 Webhook 簽名"""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


async def dispatch_webhook_event(event_type: str, data: dict):
    """分發 Webhook 事件（供其他服務調用）"""
    try:
        # 找到訂閱此事件的 webhooks
        relevant_webhooks = [
            w for w in webhooks_db.values() 
            if w["active"] and event_type in w["events"]
        ]
        
        if not relevant_webhooks:
            return
        
        event = {
            "id": str(uuid4()),
            "type": event_type,
            "created_at": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # 為每個 webhook 建立投遞記錄
        for webhook in relevant_webhooks:
            delivery_id = str(uuid4())
            delivery = {
                "id": delivery_id,
                "webhook_id": webhook["id"],
                "event_type": event_type,
                "status": "pending",
                "http_status": None,
                "response_body": None,
                "error_message": None,
                "attempt_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "delivered_at": None,
                "next_retry_at": None
            }
            
            deliveries_db[delivery_id] = delivery
            
            # TODO: 實作實際的 HTTP 投遞邏輯
            # webhook_dispatcher.deliver_async(webhook, event, delivery_id)
        
        logger.info(f"Dispatched webhook event {event_type} to {len(relevant_webhooks)} webhooks")
        
    except Exception as e:
        logger.error(f"Failed to dispatch webhook event {event_type}: {e}")
