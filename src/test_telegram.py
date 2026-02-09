import httpx
import asyncio
from src.config.settings import settings

async def send_test_message():
    token = settings.TELEGRAM_BOT_TOKEN
    
    print("--- Teste de Conexão Telegram ---")
    chat_id = input("Digite o seu Chat ID (obtido no @userinfobot): ")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🚀 *HOUSTON, TEMOS CONTATO!*\n\nSe você está lendo isso, o seu bot do Telegram está configurado corretamente e pronto para enviar seus dados de saúde.",
        "parse_mode": "Markdown"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                print("\n✅ SUCESSO! Verifique seu Telegram agora.")
            else:
                print(f"\n❌ ERRO {response.status_code}: {response.text}")
        except Exception as e:
            print(f"\n❌ Falha na requisição: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_message())