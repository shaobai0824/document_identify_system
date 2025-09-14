# 文件驗證系統 - 完整開發版本

這是一個基於 FastAPI、SQLAlchemy、Celery 和 Tesseract OCR 的文件驗證系統，支援文件上傳、OCR 處理、智能驗證、背景任務處理和人工覆核佇列。

## 🚀 功能特色

### 核心功能
- ✅ **文件上傳與處理**: 支援 PDF、JPG、PNG、TIFF 等格式
- ✅ **OCR 文字識別**: 使用 Tesseract 引擎，支援中英文識別
- ✅ **可插拔架構**: OCR、儲存、LLM 服務均採用適配器模式
- ✅ **資料庫層**: SQLAlchemy ORM + Alembic 遷移管理
- ✅ **背景任務**: Celery 異步處理，支援任務佇列和監控

### 進階功能
- ✅ **LLM 整合**: OpenAI GPT 智能文件驗證和資料提取
- ✅ **Webhook 系統**: 處理完成後自動通知外部系統
- ✅ **人工覆核**: 低信心度結果進入人工審核佇列
- ✅ **多儲存後端**: 本地、S3、MinIO 儲存支援
- ✅ **任務監控**: 實時任務狀態追蹤和統計

## 📋 系統需求

### 必需依賴
- Python 3.10+
- Redis (Celery 訊息佇列)
- Tesseract OCR 引擎
- PostgreSQL (生產環境) 或 SQLite (開發環境)

### 可選依賴
- OpenAI API Key (LLM 功能)
- AWS S3 或 MinIO (雲端儲存)

## 🛠️ 安裝與設定

### 1. 環境準備

```powershell
# 啟動虛擬環境
.\venv-py311\Scripts\Activate.ps1

# 安裝依賴
pip install -r requirements.txt

# 安裝 Tesseract OCR (Windows)
# 下載並安裝: https://github.com/UB-Mannheim/tesseract/wiki
# 確保 tesseract 在 PATH 中
```

### 2. 環境配置

複製並編輯環境變數檔案：

```powershell
cp env.example .env
```

編輯 `.env` 檔案：

```env
# 基本設定
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# 資料庫 (開發環境使用 SQLite)
DATABASE_URL=sqlite:///./verifier_dev.db

# Redis (背景任務)
REDIS_URL=redis://localhost:6379/0

# OCR 設定
OCR_PROVIDER=tesseract

# LLM 設定 (可選)
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key

# 儲存設定 (預設本地儲存)
# S3_BUCKET=your-bucket
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
```

### 3. 資料庫初始化

```powershell
# 執行資料庫遷移
alembic upgrade head
```

## 🚀 啟動系統

### 開發環境 - 單機模式

1. **啟動 Redis** (需要另外安裝)
   ```powershell
   # Windows: 使用 Docker 或 WSL2 啟動 Redis
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **啟動 API 服務器**
   ```powershell
   python -m verifier_app.main
   # 或使用 uvicorn
   uvicorn verifier_app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **啟動 Celery Worker** (新終端)
   ```powershell
   .\start_celery_worker.ps1
   ```

4. **啟動 Celery Beat** (可選，定期任務)
   ```powershell
   .\start_celery_beat.ps1
   ```

### 服務地址
- API 文檔: http://localhost:8000/docs
- API 服務: http://localhost:8000/api/v1
- 健康檢查: http://localhost:8000/api/v1/health

## 📚 API 使用指南

### 1. 同步文件處理

```bash
# 上傳並立即處理文件
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "template_id=optional-template-id"
```

### 2. 異步文件處理

```bash
# 提交背景任務
curl -X POST "http://localhost:8000/api/v1/process-async" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "template_id=template-id" \
  -F "priority=high"

# 查詢任務狀態
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

### 3. 查詢文件狀態

```bash
# 詳細狀態
curl "http://localhost:8000/api/v1/status/{document_id}"

# 簡單狀態
curl "http://localhost:8000/api/v1/documents/{document_id}"
```

### 4. 人工覆核

```bash
# 取得覆核佇列
curl "http://localhost:8000/api/v1/review/queue?limit=10&priority=high"

# 取得覆核項目詳情
curl "http://localhost:8000/api/v1/review/items/{verification_id}"

# 提交覆核決定
curl -X POST "http://localhost:8000/api/v1/review/items/{verification_id}/decision" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "approve",
    "reviewer_id": "reviewer@example.com",
    "notes": "Document verified successfully"
  }'
```

## 🧪 測試

### 運行 MVP 測試

```powershell
python test_mvp.py
```

這會建立一個測試圖片，執行完整的處理流程，並驗證所有功能是否正常。

### 單元測試

```powershell
pytest tests/
```

## 📊 系統架構

```
文件驗證系統架構圖

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web API       │    │  Background     │    │   Storage       │
│   (FastAPI)     │    │  Tasks          │    │   (Local/S3)    │
│                 │    │  (Celery)       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ├───────────────────────┼───────────────────────┤
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OCR Engine    │    │   Database      │    │   Message       │
│   (Tesseract)   │    │   (SQLite/PG)   │    │   Queue (Redis) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Service   │    │   Webhook       │    │   Review Queue  │
│   (OpenAI)      │    │   Delivery      │    │   (Manual)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 組件說明

### 核心組件

1. **API 層** (`infrastructure/web/`)
   - `processing.py`: 文件處理端點
   - `templates.py`: 模板管理
   - `review.py`: 人工覆核
   - `health.py`: 健康檢查

2. **服務層** (`infrastructure/services/`)
   - `document_processor.py`: 文件處理邏輯
   - `ocr_service.py`: OCR 服務整合
   - `storage_service.py`: 儲存服務
   - `llm_service.py`: LLM 整合
   - `webhook_service.py`: Webhook 發送
   - `review_queue_service.py`: 覆核佇列

3. **適配器層** (`infrastructure/adapters/`)
   - `ocr.py`: OCR 引擎適配器
   - `storage.py`: 儲存後端適配器
   - `llm.py`: LLM 服務適配器

4. **任務層** (`infrastructure/tasks/`)
   - `celery_app.py`: Celery 配置
   - `document_tasks.py`: 背景任務定義
   - `task_manager.py`: 任務管理

5. **資料層** (`infrastructure/database/`)
   - `models.py`: SQLAlchemy 模型
   - `base.py`: 資料庫連線管理

### 領域模型 (`domains/`)
- `documents/entities.py`: 文件實體
- `templates/entities.py`: 模板實體

## 🔍 監控與維護

### 系統監控

```bash
# 查詢任務統計
curl "http://localhost:8000/api/v1/stats/tasks"

# 查詢活躍任務
curl "http://localhost:8000/api/v1/tasks"

# 查詢覆核統計
curl "http://localhost:8000/api/v1/review/statistics"
```

### 日誌檔案

- 應用程式日誌: 控制台輸出
- Celery Worker 日誌: 控制台輸出
- 資料庫查詢日誌: 開發模式下顯示

### 維護任務

系統會自動執行以下定期任務：
- 每日清理舊文件 (30 天後封存)
- 每小時檢查失敗任務並重試
- 定期重試失敗的 Webhook

## 🚧 生產環境部署

### 環境變數調整

```env
DEBUG=false
DATABASE_URL=postgresql://user:password@localhost/verifier_production
REDIS_URL=redis://redis-server:6379/0
SECRET_KEY=your-production-secret-key
```

### Docker 部署 (建議)

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db/verifier
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  worker:
    build: .
    command: celery -A verifier_app.infrastructure.tasks.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@db/verifier
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=verifier
      - POSTGRES_PASSWORD=password

  redis:
    image: redis:alpine
```

## 🤝 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案

## 🆘 常見問題

### Q: Tesseract 安裝問題
A: Windows 環境請從 [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) 下載安裝，並確保添加到 PATH

### Q: Redis 連線失敗
A: 確認 Redis 服務已啟動，Windows 建議使用 Docker: `docker run -d -p 6379:6379 redis:alpine`

### Q: 資料庫遷移失敗
A: 檢查資料庫連線設定，執行 `alembic current` 查看目前版本

### Q: OCR 識別準確度低
A: 檢查圖片品質，調整 OCR 引擎參數，或使用 LLM 增強功能

---

**開發完成！** 🎉

系統已具備完整的文件驗證功能，包含：
- ✅ 資料庫層：SQLAlchemy ORM 模型 + Alembic 遷移
- ✅ OCR 適配器：Tesseract 實作 + 可插拔介面  
- ✅ 最小端到端：上傳→OCR→驗證→結果（MVP）
- ✅ 背景任務：Celery 整合
- ✅ 擴充功能：LLM、Webhook、覆核佇列等

系統採用 Clean Architecture 原則，具備良好的可擴充性和可維護性！
