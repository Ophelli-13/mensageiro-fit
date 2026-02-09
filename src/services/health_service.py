import httpx
import logging
from datetime import datetime, timedelta, time
from src.database.connection import SessionLocal
from src.models.health_metric import User, OAuthToken, HealthMetric
from src.config.settings import settings

logger = logging.getLogger("mensageiro-fit")

class HealthService:
    def __init__(self):
        self.base_url = "https://www.googleapis.com/fitness/v1/users/me"

    async def get_valid_token(self, db, user_id):
        """Garante um token de acesso válido, renovando-o se necessário."""
        token_info = db.query(OAuthToken).filter_by(user_id=user_id).first()
        
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

    async def fetch_heart_rate(self, token):
        """Busca a média da frequência cardíaca do dia."""
        today = datetime.combine(datetime.today(), time.min)
        now = datetime.now()
        
        payload = {
            "aggregateBy": [{"dataTypeName": "com.google.heart_rate.bpm"}],
            "bucketByTime": {"durationMillis": int((now - today).total_seconds() * 1000)},
            "startTimeMillis": int(today.timestamp() * 1000),
            "endTimeMillis": int(now.timestamp() * 1000),
        }

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(f"{self.base_url}/dataset:aggregate", json=payload, headers=headers)
            data = resp.json()
            try:
                # Pega a média (fpVal) do primeiro bucket
                return int(data['bucket'][0]['dataset'][0]['point'][0]['value'][0]['fpVal'])
            except (KeyError, IndexError):
                return 0

    async def fetch_sleep(self, token):
        """Busca a duração do sono nas últimas 24 horas via Sessões."""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        start_time = yesterday.isoformat() + "Z"
        end_time = now.isoformat() + "Z"

        url = f"{self.base_url}/sessions"
        params = {
            "startTime": start_time,
            "endTime": end_time,
            "activityType": 72  # ID 72 = Sleep
        }

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.get(url, headers=headers, params=params)
            sessions = resp.json().get('session', [])
            
            total_minutes = 0
            for s in sessions:
                start = int(s['startTimeMillis'])
                end = int(s['endTimeMillis'])
                total_minutes += (end - start) / 60000
            
            if total_minutes == 0:
                return "Dados não registrados"
                
            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)
            return f"{hours}h {minutes}min"

    async def generate_daily_report(self):
        """Orquestra a busca de todos os dados e formata o relatório."""
        db = SessionLocal()
        try:
            # 1. Verifica usuário
            user = db.query(User).filter_by(email=settings.USER_EMAIL).first()
            if not user:
                return "⚠️ Usuário não cadastrado no banco."

            # 2. Verifica Token
            token = await self.get_valid_token(db, user.id)
            if not token:
                return "⚠️ Falha ao obter acesso ao Google Fit."

            # 3. Coleta Métricas
            steps = await self.fetch_steps(token)
            heart = await self.fetch_heart_rate(token)
            sleep = await self.fetch_sleep(token)

            # 4. Opcional: Salva no banco (somente passos no modelo atual)
            # Se você quiser salvar batimentos e sono, precisará alterar o Model HealthMetric
            metric = HealthMetric(user_id=user.id, date=datetime.today().date(), steps=steps)
            db.add(metric)
            db.commit()

            # 5. Formata Mensagem Final
            return (
                f"📊 *Resumo de Saúde do Dia*\n\n"
                f"👣 *Passos:* {steps}\n"
                f"❤️ *Batimentos Médios:* {heart} BPM\n"
                f"😴 *Sono (24h):* {sleep}\n\n"
                f"🔥 *Continue focado em sua saúde!*"
            )
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")
            return "❌ Erro interno ao processar dados de saúde."
        finally:
            db.close()