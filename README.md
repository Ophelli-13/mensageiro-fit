# 🥗 Mensageiro Fit

Sistema automatizado que busca dados de saúde do **Google Fit API**, armazena em um banco **MariaDB** e envia relatórios diários via **Telegram Bot**.

## 🚀 Tecnologias
* Python 3.11
* SQLAlchemy (ORM)
* Google Fit REST API
* Docker & Docker Compose
* APScheduler (Agendamento de tarefas)

## ⚙️ Como configurar
1. Clone o repositório.
2. Crie um arquivo `.env` baseado nas variáveis do `src/config/settings.py`.
3. Configure suas credenciais no [Google Cloud Console](https://console.cloud.google.com/).
4. Execute via Docker: `docker-compose up -d`.