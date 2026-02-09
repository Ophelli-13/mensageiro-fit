import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from src.config.settings import settings

logger = logging.getLogger("mensageiro-fit")

class GoogleFitClient:
    def __init__(self, access_token: str, refresh_token: str = None, expires_at=None):
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            expiry=expires_at
        )
        # Inicializa o serviço da API Fitness
        self.service = build('fitness', 'v1', credentials=self.creds)

    def refresh_user_token(self):
       #Atualiza o token de acesso se ele estiver expirado
        if self.creds and self.creds.expired and self.creds.refresh_token:
            logger.info("Token expirado, tentando atualizar...")
            self.creds.refresh(Request())
            return self.creds
        return None

    def get_daily_steps(self, start_time_ms: int, end_time_ms: int):
        #Busca o total de passos no intervalo de tempo
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
            "bucketByTime": {"durationMillis": end_time_ms - start_time_ms},
            "startTimeMillis": start_time_ms,
            "endTimeMillis": end_time_ms
        }
        
        response = self.service.users().dataset().aggregate(userId='me', body=body).execute()
        
        steps = 0
        for bucket in response.get('bucket', []):
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for value in point.get('value', []):
                        steps += value.get('intVal', 0)
        return steps