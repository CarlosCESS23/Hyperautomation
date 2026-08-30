import json
import os
import urllib.request
from dotenv import load_dotenv

load_dotenv()

token = os.environ["TELEGRAM_BOT_TOKEN"]
url = f"https://api.telegram.org/bot{token}/getMe"

try:
    with urllib.request.urlopen(url, timeout=10) as resposta:
        dados = json.load(resposta)

    print(json.dumps(dados, indent=2, ensure_ascii=False))
except Exception as erro:
    print(f"Falha ao validar Telegram: {erro}")

