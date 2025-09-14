# 使用 Python 3.11-slim 作為基礎映像
FROM python:3.11-slim

# 設定環境變數，將 Python 輸出緩衝區設定為不緩衝
ENV PYTHONUNBUFFERED 1

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴，解決 libGL.so.1 錯誤
RUN apt-get update && apt-get install -y --no-install-recommends     libgl1     libglib2.0-0     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# 暴露應用程式運行的埠
EXPOSE 8000

# 定義啟動命令
CMD ["python", "-m", "uvicorn", "src.verifier_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
