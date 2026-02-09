import httpx
from datetime import datetime, timedelta, time
from src.database.connection import SessionLocal
from src.models.health_metric import User, OAuthToken, HealthMetric
from src.config.settings import settings
import logging

logger = logging.getLogger("mensageiro-fit")

class HealthService:
    def __init__(self):
        self.base_url = "https://www.googleapis.com/fitness/v1/users/me"

    async def get_valid_token(self, db, user_id):
        """Garante um token de acesso válido, renovando-o se necessário."""
        token_info = db.query(OAuthToken).filter_by(user_id=user_id).first()
        
        # VERIFICAÇÃO: Se não existe token nenhum no banco para este usuário
        if not token_info:
            logger.error(f"❌ Nenhum token OAuth encontrado para o usuário {user_id}")
            return None
        
        # Se expirar em menos de 5 minutos, renova
        if token_info.expires_at <= datetime.utcnow() + timedelta(minutes=5):
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "refresh_token": token_info.refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                data = resp.json()
                if "access_token" in data:
                    token_info.access_token = data["access_token"]
                    token_info.expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])
                    db.commit()
                else:
                    logger.error(f"❌ Erro ao renovar token Google: {data}")
                    return None
        
        return token_info.access_token

    async def fetch_steps(self, token):
        """Busca o total de passos do dia atual."""
        if not token:
            return 0

        today = datetime.combine(datetime.today(), time.min)
        now = datetime.now()
        
        payload = {
            "aggregateBy": [{"dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"}],
            "bucketByTime": {"durationMillis": int((now - today).total_seconds() * 1000)},
            "startTimeMillis": int(today.timestamp() * 1000),
            "endTimeMillis": int(now.timestamp() * 1000),
        }

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(f"{self.base_url}/dataset:aggregate", json=payload, headers=headers)
            data = resp.json()
            
            try:
                steps = data['bucket'][0]['dataset'][0]['point'][0]['value'][0]['intVal']
                return steps
            except (KeyError, IndexError):
                return 0

    async def generate_daily_report(self):
        """Orquestra a busca de dados e salva no banco."""
        db = SessionLocal()
        try:
            # 1. Busca o usuário
            user = db.query(User).filter_by(email=settings.USER_EMAIL).first()
            
            # VERIFICAÇÃO: Se o banco estiver vazio ou usuário não existir
            if not user:
                return "⚠️ Usuário não encontrado no banco. Por favor, registre-se primeiro."

            # 2. Busca o token
            token = await self.get_valid_token(db, user.id)
            if not token:
                return "⚠️ Falha na conexão com o Google. Token não encontrado ou expirado."

            # 3. Busca os passos
            steps = await self.fetch_steps(token)

            # 4. Salva a métrica no banco
            metric = HealthMetric(user_id=user.id, date=datetime.today().date(), steps=steps)
            db.add(metric)
            db.commit()

            return f"📊 *Resumo de Saúde do Dia*\n\n👣 Passos: {steps}\n🔥 Continue se movendo!"
        
        except Exception as e:
            logger.error(f"🔥 Erro interno no HealthService: {e}")
            return "❌ Ocorreu um erro ao gerar seu relatório de saúde."
        finally:
            db.close()