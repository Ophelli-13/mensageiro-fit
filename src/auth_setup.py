import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config.settings import settings
from src.database.connection import engine, Base, SessionLocal
from src.models.health_metric import User, OAuthToken, HealthMetric 

# Configuração de logs para acompanhar o processo no terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-setup")

# Escopos necessários para acessar dados do Google Fit e perfil
SCOPES = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.heart_rate.read',
    'https://www.googleapis.com/auth/fitness.sleep.read',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email'
]

def run_auth_flow():
    # 1. Garante que as tabelas existam no MariaDB do CasaOS
    logger.info("🛠️ Verificando/Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)

    # Configuração baseada nas credenciais que você baixou do Google Cloud
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # 2. Inicia o fluxo de autenticação local
    # access_type='offline' permite obter o Refresh Token
    # prompt='consent' garante que a tela de autorização apareça sempre no setup
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')

    logger.info("✅ Autenticação realizada com sucesso no Google!")

    # 3. Persistência dos dados no banco MariaDB
    db = SessionLocal()
    try:
        # Puxa o e-mail definido no seu arquivo .env
        meu_email = settings.USER_EMAIL 
        
        # Verifica se o usuário já existe, senão cria
        user = db.query(User).filter_by(email=meu_email).first()
        if not user:
            logger.info(f"Criando novo usuário no banco: {meu_email}")
            user = User(email=meu_email, google_id="google_authenticated_user")
            db.add(user)
            db.flush() # Gera o ID necessário para o relacionamento do Token

        # Busca ou cria o registro de token para este usuário
        token_entry = db.query(OAuthToken).filter_by(user_id=user.id).first()
        if not token_entry:
            token_entry = OAuthToken(user_id=user.id)
            db.add(token_entry)

        # Atualiza os dados do token (incluindo o vital Refresh Token)
        token_entry.access_token = creds.token
        token_entry.refresh_token = creds.refresh_token 
        token_entry.expires_at = creds.expiry

        db.commit()
        logger.info(f"🚀 SUCESSO! Refresh Token guardado para o e-mail do .env: {meu_email}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao salvar no banco: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Lembre-se de rodar: set PYTHONPATH=. antes de executar
    run_auth_flow()