import datetime
from sqlalchemy.orm import Session
from src.clients.google_fit_client import GoogleFitClient
from src.models.health_metric import OAuthToken, HealthMetric

class GoogleFitService:
    def __init__(self, db: Session):
        self.db = db

    def sync_user_data(self, user_id: int):
       #Coordena a coleta de dados para um usuário específico
        token_data = self.db.query(OAuthToken).filter_by(user_id=user_id).first()
        
        if not token_data:
            return None

        client = GoogleFitClient(
            access_token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            expires_at=token_data.expires_at
        )

        # 1. Tenta atualizar token se necessário
        new_creds = client.refresh_user_token()
        if new_creds:
            token_data.access_token = new_creds.token
            token_data.expires_at = new_creds.expiry
            self.db.commit()

        # 2. Define intervalo (Hoje, da meia-noite até agora)
        now = datetime.datetime.now()
        start_of_day = datetime.datetime.combine(now.date(), datetime.time.min)
        
        start_ms = int(start_of_day.timestamp() * 1000)
        end_ms = int(now.timestamp() * 1000)

        # 3. Busca métricas
        steps = client.get_daily_steps(start_ms, end_ms)

        # 4. Salva ou atualiza no banco
        metric = self.db.query(HealthMetric).filter_by(
            user_id=user_id, 
            date=now.date()
        ).first()

        if not metric:
            metric = HealthMetric(user_id=user_id, date=now.date())
            self.db.add(metric)

        metric.steps = steps
        self.db.commit()
        
        return metric