#!/usr/bin/env python3
"""
Celery Worker 啟動腳本
"""

import os
import sys

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from verifier_app.infrastructure.tasks.celery_app import celery_app

if __name__ == "__main__":
    # 啟動 Celery Worker
    celery_app.start()
