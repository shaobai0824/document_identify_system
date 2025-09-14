"""
範本管理路由
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...application.templates.dtos import (BoundingBoxDto,
                                           FieldDefinitionCreateDto,
                                           FieldDefinitionDto,
                                           TemplateCreateDto, TemplateDto,
                                           TemplateListDto, TemplateUpdateDto)
from ...infrastructure.database.base import get_sync_session
from ...infrastructure.database.models import Template, TemplateType
from ...infrastructure.services.llm_service import LLMService
from ...infrastructure.services.storage_service import StorageService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/document-templates", response_model=TemplateListDto)
async def list_templates(
    limit: int = Query(25, le=100),
    starting_after: Optional[str] = None,
    template_type: Optional[str] = Query(None, description="過濾範本類型")
):
    """列出範本"""
    try:
        db = get_sync_session()
        query = db.query(Template).filter(Template.is_active == True)
        
        # 類型過濾
        if template_type:
            try:
                template_type_enum = TemplateType[template_type.upper()]
                query = query.filter(Template.template_type == template_type_enum)
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid template type: {template_type}")
            except AttributeError:
                # 如果 template_type 不是字串，跳過過濾
                pass
        
        # 分頁
        if starting_after:
            query = query.filter(Template.id > starting_after)
        
        templates = query.order_by(Template.created_at.desc()).limit(limit + 1).all()
        
        has_more = len(templates) > limit
        if has_more:
            templates = templates[:-1]
        
        # 轉換為 DTO
        template_dtos = []
        for template in templates:
            field_definitions = []
            if template.field_definitions and isinstance(template.field_definitions, list):
                for field_def in template.field_definitions:
                    if isinstance(field_def, dict) and "name" in field_def and "bbox" in field_def:
                        field_definitions.append(FieldDefinitionDto(
                            id=field_def.get("id", str(uuid4())),
                            name=field_def["name"],
                            bbox=BoundingBoxDto(**field_def["bbox"]),
                            required=field_def.get("required", False),
                            suggested=field_def.get("suggested", False)
                        ))
            
            # 生成 base_image_url
            base_image_url = None
            if template.ocr_regions and isinstance(template.ocr_regions, dict):
                base_image_path = template.ocr_regions.get("base_image_path")
                if base_image_path:
                    base_image_url = f"/api/v1/storage/{base_image_path}"
            
            template_dtos.append(TemplateDto(
                id=str(template.id),
                name=template.name,
                base_image_url=base_image_url,
                field_definitions=field_definitions,
                version=template.version or "1.0",
                status="active" if template.is_active else "inactive",
                created_at=template.created_at.isoformat(),
                updated_at=template.updated_at.isoformat() if template.updated_at else None
            ))
        
        db.close()
        
        return TemplateListDto(
            object="list",
            data=template_dtos,
            has_more=has_more,
            total_count=len(template_dtos)
        )
        
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/document-templates", response_model=TemplateDto, status_code=201)
async def create_template(template_data: TemplateCreateDto):
    """建立範本"""
    try:
        db = get_sync_session()
        
        # 檢查名稱是否重複
        existing = db.query(Template).filter(
            Template.name == template_data.name,
            Template.is_active == True
        ).first()
        
        if existing:
            raise HTTPException(status_code=409, detail="Template with this name already exists")
        
        # 建立新範本
        template = Template(
            id=uuid4(),
            name=template_data.name,
            template_type=TemplateType.CUSTOM,
            field_definitions=[],  # 初始為空，後續透過其他端點新增
            is_active=True
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        # 轉換為 DTO
        template_dto = TemplateDto(
            id=str(template.id),
            name=template.name,
            base_image_url=None,
            field_definitions=[],
            version=template.version or "1.0",
            status="active",
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None
        )
        
        db.close()
        logger.info(f"Created template: {template.id}")
        
        return template_dto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/document-templates/{template_id}", response_model=TemplateDto)
async def get_template(template_id: str):
    """取得範本"""
    try:
        db = get_sync_session()
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # 轉換欄位定義
        field_definitions = []
        if template.field_definitions:
            for field_def in template.field_definitions:
                field_definitions.append(FieldDefinitionDto(
                    id=field_def.get("id", str(uuid4())),
                    name=field_def["name"],
                    bbox=BoundingBoxDto(**field_def["bbox"]),
                    required=field_def.get("required", False),
                    suggested=field_def.get("suggested", False)
                ))
        
        # 生成 base_image_url
        base_image_url = None
        if template.ocr_regions and isinstance(template.ocr_regions, dict):
            base_image_path = template.ocr_regions.get("base_image_path")
            if base_image_path:
                base_image_url = f"/api/v1/storage/{base_image_path}"
        
        template_dto = TemplateDto(
            id=str(template.id),
            name=template.name,
            base_image_url=base_image_url,
            field_definitions=field_definitions,
            version=template.version or "1.0",
            status="active" if template.is_active else "inactive",
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None
        )
        
        db.close()
        return template_dto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/document-templates/{template_id}", response_model=TemplateDto)
async def update_template(template_id: str, template_data: TemplateUpdateDto):
    """更新範本"""
    try:
        db = get_sync_session()
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # 更新欄位
        if template_data.name is not None:
            # 檢查名稱是否重複
            existing = db.query(Template).filter(
                Template.name == template_data.name,
                Template.is_active == True,
                Template.id != template_id
            ).first()
            
            if existing:
                raise HTTPException(status_code=409, detail="Template with this name already exists")
            
            template.name = template_data.name
        
        # 更新欄位定義
        if template_data.field_definitions is not None:
            # 轉換為字典格式存儲
            field_definitions = []
            for field_def in template_data.field_definitions:
                field_definitions.append({
                    "id": field_def.id,
                    "name": field_def.name,
                    "bbox": {
                        "x1": field_def.bbox.x1,
                        "y1": field_def.bbox.y1,
                        "x2": field_def.bbox.x2,
                        "y2": field_def.bbox.y2
                    },
                    "required": field_def.required,
                    "suggested": field_def.suggested
                })
            template.field_definitions = field_definitions
        
        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        
        # 轉換欄位定義
        field_definitions = []
        if template.field_definitions:
            for field_def in template.field_definitions:
                field_definitions.append(FieldDefinitionDto(
                    id=field_def.get("id", str(uuid4())),
                    name=field_def["name"],
                    bbox=BoundingBoxDto(**field_def["bbox"]),
                    required=field_def.get("required", False),
                    suggested=field_def.get("suggested", False)
                ))
        
        # 生成 base_image_url
        base_image_url = None
        if template.ocr_regions and isinstance(template.ocr_regions, dict):
            base_image_path = template.ocr_regions.get("base_image_path")
            if base_image_path:
                base_image_url = f"/api/v1/storage/{base_image_path}"
        
        template_dto = TemplateDto(
            id=str(template.id),
            name=template.name,
            base_image_url=base_image_url,
            field_definitions=field_definitions,
            version=template.version or "1.0",
            status="active" if template.is_active else "inactive",
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None
        )
        
        db.close()
        logger.info(f"Updated template: {template.id}")
        
        return template_dto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/document-templates/{template_id}", status_code=204)
async def delete_template(template_id: str):
    """刪除範本（軟刪除）"""
    db = None
    try:
        db = get_sync_session()
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # 檢查是否已經被刪除
        if not template.is_active:
            raise HTTPException(status_code=404, detail="Template already deleted")
        
        # 軟刪除
        template.is_active = False
        template.updated_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Deleted template: {template.id}")
        
    except HTTPException:
        if db:
            db.rollback()
        raise
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Failed to delete template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if db:
            db.close()


@router.post("/document-templates/{template_id}/image", response_model=TemplateDto)
async def upload_template_image(template_id: str, file: UploadFile = File(...)):
    """上傳範本底圖"""
    try:
        db = get_sync_session()
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # 驗證檔案類型
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "application/pdf"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
            )
        
        # 上傳檔案
        storage_service = StorageService()
        file_content = await file.read()
        
        # 生成儲存路徑
        storage_path = storage_service.generate_storage_path(
            file.filename or "template_image",
            template_id,
            prefix="templates"
        )
        
        await storage_service.upload_file_content(file_content, storage_path)
        
        # 更新範本記錄（暫時儲存路徑）
        if not template.ocr_regions:
            template.ocr_regions = {}
        template.ocr_regions["base_image_path"] = storage_path
        template.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(template)
        
        # 轉換為 DTO
        field_definitions = []
        if template.field_definitions:
            for field_def in template.field_definitions:
                field_definitions.append(FieldDefinitionDto(
                    id=field_def.get("id", str(uuid4())),
                    name=field_def["name"],
                    bbox=BoundingBoxDto(**field_def["bbox"]),
                    required=field_def.get("required", False),
                    suggested=field_def.get("suggested", False)
                ))
        
        template_dto = TemplateDto(
            id=str(template.id),
            name=template.name,
            base_image_url=f"/api/v1/storage/{storage_path}",  # 返回可訪問的 URL
            field_definitions=field_definitions,
            version=template.version or "1.0",
            status="active" if template.is_active else "inactive",
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat() if template.updated_at else None
        )
        
        db.close()
        logger.info(f"Uploaded image for template: {template.id}")
        
        return template_dto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload template image for {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/document-templates/{template_id}/fields", response_model=FieldDefinitionDto, status_code=201)
async def add_field_definition(template_id: str, field_data: FieldDefinitionCreateDto):
    """新增欄位定義"""
    try:
        db = get_sync_session()
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # 驗證座標框
        bbox = field_data.bbox
        if bbox.x1 >= bbox.x2 or bbox.y1 >= bbox.y2:
            raise HTTPException(status_code=400, detail="Invalid bounding box coordinates")
        
        # 建立新欄位定義
        field_id = str(uuid4())
        new_field = {
            "id": field_id,
            "name": field_data.name,
            "bbox": {
                "x1": bbox.x1,
                "y1": bbox.y1,
                "x2": bbox.x2,
                "y2": bbox.y2
            },
            "required": field_data.required,
            "suggested": False
        }
        
        # 更新範本的欄位定義
        if not template.field_definitions:
            template.field_definitions = []
        
        # 檢查欄位名稱是否重複
        for existing_field in template.field_definitions:
            if existing_field["name"] == field_data.name:
                raise HTTPException(status_code=409, detail="Field with this name already exists")
        
        template.field_definitions.append(new_field)
        template.updated_at = datetime.utcnow()
        
        # 標記為已修改以觸發 JSON 欄位更新
        db.add(template)
        db.commit()
        
        field_dto = FieldDefinitionDto(
            id=field_id,
            name=field_data.name,
            bbox=bbox,
            required=field_data.required,
            suggested=False
        )
        
        db.close()
        logger.info(f"Added field '{field_data.name}' to template: {template.id}")
        
        return field_dto
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add field to template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/document-templates/{template_id}/ai/suggest-fields", response_model=List[FieldDefinitionDto])
async def suggest_fields_with_ai(template_id: str, prompt: Optional[dict] = None):
    """LLM 自動建議欄位"""
    try:
        db = get_sync_session()
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # 檢查是否有底圖
        if not template.ocr_regions or not template.ocr_regions.get("base_image_path"):
            raise HTTPException(
                status_code=412, 
                detail="Template must have a base image before AI field suggestion"
            )
        
        # 實作 LLM 欄位建議邏輯
        llm_service = LLMService()
        # 這裡需要獲取 OCR 文字，目前假設 template.ocr_regions 中包含處理過的文字
        # 實際應用中，可能需要從 storage_service 下載圖片，再調用 OCR 服務獲取文字
        # 為了 POC，暫時使用一個佔位符
        ocr_text = "Document text content will be here."
        
        # 調用 LLM 服務獲取建議欄位
        suggested_fields_raw = await llm_service.suggest_fields(ocr_text, prompt)
        
        # 確保返回的是列表，如果不是則返回空列表
        if not isinstance(suggested_fields_raw, list):
            logger.error(f"LLMService.suggest_fields 返回的格式不正確: {suggested_fields_raw}")
            suggested_fields_raw = []

        # 轉換為 DTO
        field_dtos = []
        for field in suggested_fields_raw:
            field_dtos.append(FieldDefinitionDto(
                id=field.get("id", str(uuid4())),
                name=field["name"],
                bbox=BoundingBoxDto(**field["bbox"]),
                required=field.get("required", False),
                suggested=field.get("suggested", True)
            ))
        
        db.close()
        logger.info(f"Generated AI field suggestions for template: {template.id}")
        
        return field_dtos
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate AI suggestions for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
