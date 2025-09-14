# Celery Worker 啟動腳本 (Windows PowerShell)

Write-Host "啟動 Celery Worker..." -ForegroundColor Green

# 設定環境變數
$env:PYTHONPATH = $PWD

# 啟動 Celery Worker
celery -A verifier_app.infrastructure.tasks.celery_app worker --loglevel=info --pool=solo
