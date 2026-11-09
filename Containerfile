
# 使用 Python 3.13 的輕量 Linux 映像檔
FROM docker.io/library/python:3.13-slim

# 容器內的專案工作目錄
WORKDIR /app

# Python 執行環境設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝專案需要的套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製 CouponHub 程式碼
COPY app.py admin_app.py ./
COPY src/ ./src/
COPY tests/ ./tests/

# 建立資料庫與紀錄資料夾
RUN mkdir -p /app/data /app/logs

# Streamlit 容器內使用 8501
EXPOSE 8501

# 啟動 CouponHub 消費者前台
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
