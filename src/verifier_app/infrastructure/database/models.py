"""
SQLAlchemy 資料庫模型定義
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (JSON, Boolean, Column, DateTime, Enum, Float,
                        ForeignKey, Index, Integer, LargeBinary, String, Text)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import CHAR, TypeDecorator

from .base import Base


class GUID(TypeDecorator):
    """
    跨資料庫相容的 UUID 類型
    在 PostgreSQL 使用 UUID，在 SQLite 使用 CHAR(36)
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class DocumentStatus(PyEnum):
    """文件處理狀態"""
    UPLOADED = "uploaded"          # 已上傳
    PROCESSING = "processing"      # 處理中
    OCR_COMPLETED = "ocr_completed"  # OCR 完成
    VERIFIED = "verified"          # 已驗證
    FAILED = "failed"              # 處理失敗
    ARCHIVED = "archived"          # 已封存


class VerificationStatus(PyEnum):
    """驗證結果狀態"""
    PENDING = "pending"            # 待驗證
    PASS = "pass"                  # 通過
    FAIL = "fail"                  # 未通過
    MANUAL_REVIEW = "manual_review"  # 需人工審核


class ReviewStatus(PyEnum):
    """覆核任務狀態"""
    PENDING = "pending"            # 待分配
    ASSIGNED = "assigned"          # 已分配
    IN_PROGRESS = "in_progress"    # 處理中
    COMPLETED = "completed"        # 已完成
    CANCELLED = "cancelled"        # 已取消


class TemplateType(PyEnum):
    """模板類型"""
    IDENTITY_CARD = "identity_card"      # 身分證
    PASSPORT = "passport"                # 護照
    DRIVER_LICENSE = "driver_license"    # 駕照
    UTILITY_BILL = "utility_bill"        # 水電費帳單
    BANK_STATEMENT = "bank_statement"    # 銀行對帳單
    CUSTOM = "custom"                    # 自訂模板


class Document(Base):
    """文件實體"""
    __tablename__ = "documents"
    
    # 主鍵
    id = Column(GUID(), primary_key=True, default=uuid4, index=True)
    
    # 基本資訊
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 雜湊
    
    # 儲存位置
    storage_path = Column(String(500), nullable=False)  # S3 或本地路徑
    storage_provider = Column(String(50), default="local")  # local | s3 | minio
    
    # 處理狀態
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, index=True)
    processing_progress = Column(Float, default=0.0)  # 0.0 - 1.0
    
    # OCR 結果
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)
    ocr_metadata = Column(JSON)  # OCR 引擎的額外資訊
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # 關聯
    verification_records = relationship("VerificationRecord", back_populates="document", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_document_status_created', 'status', 'created_at'),
        Index('idx_document_hash', 'file_hash'),
    )


class Template(Base):
    """驗證模板實體"""
    __tablename__ = "templates"
    
    # 主鍵
    id = Column(GUID(), primary_key=True, default=uuid4, index=True)
    
    # 基本資訊
    name = Column(String(200), nullable=False)
    description = Column(Text)
    template_type = Column(Enum(TemplateType), nullable=False, index=True)
    version = Column(String(20), default="1.0")
    
    # 模板配置
    field_definitions = Column(JSON, nullable=False)  # 欄位定義和驗證規則
    validation_rules = Column(JSON)  # 驗證規則配置
    ocr_regions = Column(JSON)  # OCR 區域定義
    
    # 狀態
    is_active = Column(Boolean, default=True, index=True)
    confidence_threshold = Column(Float, default=0.9)  # 信心度門檻
    
    # 統計資訊
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 關聯
    verification_records = relationship("VerificationRecord", back_populates="template")
    
    # 索引
    __table_args__ = (
        Index('idx_template_type_active', 'template_type', 'is_active'),
    )


class VerificationRecord(Base):
    """驗證記錄實體"""
    __tablename__ = "verification_records"
    
    # 主鍵
    id = Column(GUID(), primary_key=True, default=uuid4, index=True)
    
    # 關聯外鍵
    document_id = Column(GUID(), ForeignKey("documents.id"), nullable=False, index=True)
    template_id = Column(GUID(), ForeignKey("templates.id"), nullable=False, index=True)
    
    # 驗證結果
    status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING, index=True)
    overall_confidence = Column(Float)  # 整體信心度
    
    # 欄位驗證結果
    field_results = Column(JSON)  # 各欄位驗證結果詳情
    extracted_data = Column(JSON)  # 提取的資料
    
    # 處理資訊
    processing_time_ms = Column(Integer)  # 處理時間（毫秒）
    error_message = Column(Text)  # 錯誤訊息
    warnings = Column(JSON)  # 警告訊息列表
    
    # 人工審核
    requires_manual_review = Column(Boolean, default=False, index=True)
    manual_review_notes = Column(Text)
    reviewed_by = Column(String(100))  # 審核者
    reviewed_at = Column(DateTime(timezone=True))
    
    # 覆核任務狀態與分配
    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, index=True)
    assigned_to = Column(String(100), index=True)  # 被分配的審核者 ID
    assigned_at = Column(DateTime(timezone=True))  # 分配時間
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 關聯
    document = relationship("Document", back_populates="verification_records")
    template = relationship("Template", back_populates="verification_records")
    
    # 索引
    __table_args__ = (
        Index('idx_verification_document_template', 'document_id', 'template_id'),
        Index('idx_verification_status_created', 'status', 'created_at'),
        Index('idx_verification_manual_review', 'requires_manual_review'),
    )


class TaskRecord(Base):
    """背景任務記錄"""
    __tablename__ = "task_records"
    
    # 主鍵
    id = Column(GUID(), primary_key=True, default=uuid4, index=True)
    
    # 任務資訊
    task_id = Column(String(255), unique=True, nullable=False, index=True)  # Celery 任務 ID
    task_name = Column(String(200), nullable=False)  # 任務名稱
    task_type = Column(String(100), nullable=False, index=True)  # 任務類型
    
    # 關聯資源
    document_id = Column(GUID(), ForeignKey("documents.id"), index=True)
    
    # 狀態和結果
    status = Column(String(50), default="PENDING", index=True)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    result = Column(JSON)  # 任務結果
    error_info = Column(JSON)  # 錯誤資訊
    
    # 執行資訊
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    execution_time_ms = Column(Integer)
    retry_count = Column(Integer, default=0)
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_task_type_status', 'task_type', 'status'),
        Index('idx_task_document', 'document_id'),
    )


class WebhookDelivery(Base):
    """Webhook 發送記錄"""
    __tablename__ = "webhook_deliveries"
    
    # 主鍵
    id = Column(GUID(), primary_key=True, default=uuid4, index=True)
    
    # Webhook 資訊
    webhook_url = Column(String(500), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    resource_id = Column(String(255), index=True)  # 關聯的資源 ID
    
    # 發送狀態
    status = Column(String(50), default="pending", index=True)  # pending, delivered, failed
    retry_count = Column(Integer, default=0)
    
    # 回應資訊
    response_status = Column(Integer)
    response_headers = Column(JSON)
    response_body = Column(Text)
    error_message = Column(Text)
    
    # 時間戳記
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    delivered_at = Column(DateTime(timezone=True))
    
    # 索引
    __table_args__ = (
        Index('idx_webhook_status_created', 'status', 'created_at'),
        Index('idx_webhook_event_type', 'event_type'),
        Index('idx_webhook_resource', 'resource_id'),
    )
