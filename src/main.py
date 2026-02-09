import logging
import sys
from src.config.settings import settings
from src.database.connection import engine, Base
# Import vital para o SQLAlchemy mapear as tabelas
from src.models.health_metric import User, OAuthToken, HealthMetric 

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mensageiro-fit")

def init_db():
    try:
        logger.info("Verificando conexão com o MariaDB do CasaOS...")
        # Cria as tabelas se não existirem
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tabelas sincronizadas com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar no banco: {e}")

if __name__ == "__main__":
    logger.info("🚀 Mensageiro Fit Iniciado!")
    init_db()