import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.health_service import HealthService
from src.config.settings import settings
from src.database.connection import SessionLocal
from src.models.health_metric import User
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mensageiro-fit")

async def send_telegram_message(chat_id, text):
    """Envia mensagem para um chat_id específico."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def register_user_chat_id(chat_id):
    """Salva o chat_id do Telegram no banco para o e-mail configurado."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=settings.USER_EMAIL).first()
        if user:
            user.telegram_chat_id = str(chat_id)
            db.commit()
            logger.info(f"✅ Chat ID {chat_id} vinculado ao usuário {settings.USER_EMAIL}")
            return True
        logger.warning(f"⚠️ Usuário {settings.USER_EMAIL} não encontrado no banco para vincular ID.")
        return False
    finally:
        db.close()

async def handle_updates():
    """Loop que 'ouve' o Telegram para capturar o /start."""
    last_update_id = 0
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
    logger.info("📡 Escutador de mensagens (Polling) iniciado...")
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params={"offset": last_update_id + 1, "timeout": 20})
                updates = resp.json().get("result", [])
                for update in updates:
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    if msg.get("text") == "/start":
                        chat_id = msg["chat"]["id"]
                        if await register_user_chat_id(chat_id):
                            await send_telegram_message(chat_id, "✅ *Conectado!* Seu ID foi registrado e você receberá os relatórios aqui.")
                        else:
                            await send_telegram_message(chat_id, "❌ Erro: Seu e-mail não foi pré-cadastrado no sistema.")
        except Exception as e:
            logger.error(f"Erro no polling: {e}")
        await asyncio.sleep(2)

async def job_daily_report():
    """Tarefa de relatório."""
    logger.info(f"🔄 Iniciando busca de dados: {datetime.now()}")
    service = HealthService()
    try:
        report_text = await service.generate_daily_report()
        # Busca o chat_id atualizado no banco
        db = SessionLocal()
        user = db.query(User).filter_by(email=settings.USER_EMAIL).first()
        db.close()
        
        if user and user.telegram_chat_id:
            await send_telegram_message(user.telegram_chat_id, report_text)
            logger.info("✅ Relatório enviado!")
    except Exception as e:
        logger.error(f"❌ Erro no job: {e}")

async def main():
    logger.info("🚀 Servidor Mensageiro Fit Iniciado!")
    # Inicia o escutador em segundo plano
    asyncio.create_task(handle_updates())
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_daily_report, 'cron', hour=21, minute=0)
    scheduler.start()

    while True:
        await asyncio.sleep(1000)

if __name__ == "__main__":
    asyncio.run(main())