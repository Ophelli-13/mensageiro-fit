FROM python:3.11-slim

# Instala dependências do sistema para o mysqlclient
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Define o PYTHONPATH para o container achar a pasta src
ENV PYTHONPATH=/app

CMD ["python", "main.py"]