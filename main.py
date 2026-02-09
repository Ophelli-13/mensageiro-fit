import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.health_service import HealthService
from src.config.settings import settings
import httpx

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mensageiro-fit")

async def send_telegram_message(text):
    """Envia a mensagem final para o Telegram usando o ID do banco."""
    from src.database.connection import SessionLocal
    from src.models.health_metric import User

    db = SessionLocal()
    user = db.query(User).filter_by(email=settings.USER_EMAIL).first()
    db.close()

    if not user or not user.telegram_chat_id:
        logger.error("❌ Usuário ou Chat ID não encontrado no banco.")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def job_daily_report():
    """Tarefa que busca os dados e envia o relatório."""
    logger.info(f"🔄 Iniciando busca de dados: {datetime.now()}")
    service = HealthService()
    try:
        report_text = await service.generate_daily_report()
        await send_telegram_message(report_text)
        logger.info("✅ Relatório enviado com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro no job: {e}")

async def main():
    logger.info("🚀 Servidor Mensageiro Fit Iniciado!")
    
    # 1. Executa uma vez AGORA para testar
    await job_daily_report()

    # 2. Configura o agendamento para rodar todo dia às 21:00
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_daily_report, 'cron', hour=21, minute=0)
    scheduler.start()

    # Mantém o programa rodando
    try:
        while True:
            await asyncio.sleep(1000)
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    asyncio.run(main())