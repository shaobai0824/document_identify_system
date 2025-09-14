"""
WebSocket 連接管理
"""

import json
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# 連接管理
class ConnectionManager:
    def __init__(self):
        # document_id -> set of websockets
        self.document_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> document_id
        self.websocket_documents: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, document_id: str):
        await websocket.accept()
        
        if document_id not in self.document_connections:
            self.document_connections[document_id] = set()
        
        self.document_connections[document_id].add(websocket)
        self.websocket_documents[websocket] = document_id
        
        logger.info(f"WebSocket connected for document {document_id}")

    def disconnect(self, websocket: WebSocket):
        document_id = self.websocket_documents.get(websocket)
        if document_id:
            self.document_connections[document_id].discard(websocket)
            if not self.document_connections[document_id]:
                del self.document_connections[document_id]
            del self.websocket_documents[websocket]
            logger.info(f"WebSocket disconnected for document {document_id}")

    async def send_to_document(self, document_id: str, message: dict):
        """發送訊息給訂閱特定文件的所有連接"""
        if document_id in self.document_connections:
            disconnected = []
            for websocket in self.document_connections[document_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send message to websocket: {e}")
                    disconnected.append(websocket)
            
            # 清理斷開的連接
            for ws in disconnected:
                self.disconnect(ws)

    async def broadcast(self, message: dict):
        """廣播訊息給所有連接"""
        for document_connections in self.document_connections.values():
            for websocket in document_connections:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception:
                    pass  # 忽略發送失敗

manager = ConnectionManager()


@router.websocket("/ws/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: str):
    """WebSocket 端點，訂閱特定文件的狀態更新"""
    await manager.connect(websocket, document_id)
    
    try:
        # 發送歡迎訊息
        welcome_message = {
            "type": "connection_established",
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Subscribed to updates for document {document_id}"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # 保持連接活躍
        while True:
            try:
                # 接收客戶端訊息（心跳包）
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    pong_message = {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(pong_message))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/global")
async def global_websocket_endpoint(websocket: WebSocket):
    """全域 WebSocket 端點，接收所有系統事件"""
    await websocket.accept()
    
    try:
        # 發送歡迎訊息
        welcome_message = {
            "type": "global_connection_established",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Subscribed to global system events"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # 保持連接
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    pong_message = {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(pong_message))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Global WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        pass


# 用於其他服務調用的通知函數
async def notify_document_update(document_id: str, event_type: str, data: dict):
    """通知文件狀態更新"""
    message = {
        "type": event_type,
        "document_id": document_id,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_to_document(document_id, message)


async def notify_system_event(event_type: str, data: dict):
    """通知系統事件"""
    message = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(message)


@router.get("/ws/stats")
async def get_websocket_stats():
    """取得 WebSocket 連接統計"""
    try:
        stats = {
            "active_connections": sum(len(connections) for connections in manager.document_connections.values()),
            "documents_with_subscribers": len(manager.document_connections),
            "connections_by_document": {
                doc_id: len(connections) 
                for doc_id, connections in manager.document_connections.items()
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
