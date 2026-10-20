FROM python:3.12-slim

WORKDIR /app

# 先装依赖（利用 Docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝代码
COPY app ./app
COPY static ./static
COPY demo.py .

# 数据目录（sqlite + 音频）挂载点
RUN mkdir -p /app/data /app/static/audio

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
