# 文件驗證系統

基於 FastAPI 的文件驗證與 OCR 處理系統，支援範本管理、自動驗證與人工覆核流程。

## 系統需求

- Python 3.10+
- PostgreSQL 12+
- Redis 6+
- Tesseract OCR

## 快速開始

### 1. 環境準備

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安裝相依套件
# 選項 A: 完整版本（需要 PostgreSQL）
pip install -r requirements.txt

# 選項 B: 開發版本（僅核心功能，無外部依賴）
pip install -r requirements-dev.txt
```

### Windows 特別說明

#### Python 版本建議
- **推薦**: Python 3.10 或 3.11
- **當前**: Python 3.13 可能有套件相容性問題

#### 快速設定（推薦）
```bash
# 一鍵設定環境
PowerShell -ExecutionPolicy Bypass -File setup-env.ps1
```

#### 手動設定
如果遇到套件安裝問題：

1. **Python 3.10/3.11 相容版本**（推薦）:
   ```bash
   pip install -r requirements-py310.txt
   python dev-start.py
   ```

2. **最小依賴版本**（快速測試）:
   ```bash
   pip install -r requirements-minimal.txt
   python dev-start.py
   ```

3. **安裝 Python 3.10**:
   ```bash
   # 使用 PowerShell 腳本
   PowerShell -ExecutionPolicy Bypass -File install-python-3.10.ps1
   
   # 或使用 Chocolatey
   choco install python --version=3.10.11
   ```

### 2. 環境變數設定

建立 `.env` 檔案：

```env
# 基本設定
DEBUG=true
SECRET_KEY=your-secret-key-here

# 資料庫
DATABASE_URL=postgresql://user:password@localhost/verifier_db

# Redis
REDIS_URL=redis://localhost:6379/0

# 物件儲存（可選用 MinIO 或 AWS S3）
S3_BUCKET=verifier-documents
S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# OCR 設定
OCR_PROVIDER=tesseract

# LLM 設定（可選）
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
```

### 3. 資料庫初始化

```bash
# 建立資料庫（需先安裝 PostgreSQL）
createdb verifier_db

# 執行資料庫遷移（待實作）
# alembic upgrade head
```

### 4. 安裝 Tesseract OCR

#### Windows
1. 下載 [Tesseract Windows installer](https://github.com/UB-Mannheim/tesseract/wiki)
2. 安裝並將路徑加入 PATH 環境變數
3. 下載中文語言包：`tessdata/chi_tra.traineddata`

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-chi-tra
```

#### macOS
```bash
brew install tesseract
brew install tesseract-lang
```

### 5. 啟動服務

#### 快速啟動（推薦）
```bash
# 使用內建啟動腳本（自動處理路徑與環境變數）
python dev-start.py
```

#### 開發模式
```bash
# 啟動 API 服務
cd src
python -m verifier_app.main

# 或使用 uvicorn
uvicorn verifier_app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 生產模式
```bash
uvicorn verifier_app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 啟動背景任務處理器（待實作）
```bash
celery -A verifier_app.infrastructure.tasks worker --loglevel=info
```

### 6. 驗證安裝

訪問以下端點確認服務正常：

- API 文檔：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/v1/health
- OpenAPI 規格：http://localhost:8000/openapi.json

## 專案結構

```
src/verifier_app/
├── main.py                 # FastAPI 應用程式入口
├── core/                   # 核心配置與共用邏輯
│   └── config.py
├── domains/                # 領域層（DDD）
│   ├── templates/          # 範本管理領域
│   └── documents/          # 文件處理領域
├── application/            # 應用層
│   ├── templates/          # 範本管理用例
│   └── documents/          # 文件處理用例
└── infrastructure/         # 基礎設施層
    ├── web/                # Web API 路由
    ├── ports/              # 可插拔介面
    ├── adapters/           # 外部服務適配器（待實作）
    └── persistence/        # 資料持久化（待實作）
```

## 開發指引

### 程式碼品質

```bash
# 格式化程式碼
black src/

# 程式碼檢查
flake8 src/

# 型別檢查
mypy src/
```

### 測試

```bash
# 執行測試
pytest

# 測試涵蓋率
pytest --cov=src/verifier_app
```

## 下一步開發

目前已完成：
- ✅ 基本專案結構（Clean Architecture）
- ✅ FastAPI 應用程式骨架
- ✅ 健康檢查端點
- ✅ 範本與處理路由雛形
- ✅ 領域模型定義
- ✅ 可插拔介面（OCR/LLM Ports）

待實作功能：
- [ ] 資料庫 ORM 模型與 Repository
- [ ] OCR 適配器（Tesseract/Google Vision）
- [ ] LLM 適配器（OpenAI/Gemini）
- [ ] 物件儲存適配器（S3/MinIO）
- [ ] 背景任務處理（Celery）
- [ ] 使用者認證與授權
- [ ] 人工覆核佇列
- [ ] Webhook 事件通知
- [ ] 範本版本化
- [ ] 完整的錯誤處理與日誌

## 相關文件

- [產品需求文件](dev_docs/PRD-文件驗證系統.md)
- [API 設計規範](dev_docs/API-文件驗證系統_設計規範.md)
- [架構設計文件](dev_docs/ARCH-文件驗證系統_架構與設計.md)
- [模組規格與測試](dev_docs/MODULES-文件驗證系統_規格與測試.md)
- [OpenAPI 規格](dev_docs/openapi.yaml)
