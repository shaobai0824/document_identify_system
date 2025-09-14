# Celery Beat 啟動腳本 (Windows PowerShell)

Write-Host "啟動 Celery Beat 排程器..." -ForegroundColor Green

# 設定環境變數
$env:PYTHONPATH = $PWD

# 啟動 Celery Beat
celery -A verifier_app.infrastructure.tasks.celery_app beat --loglevel=info
