# Imagem oficial do Playwright baseada em Ubuntu 22.04.
FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Configuração necessária para o Chromium executado pelo bot no container.
ENV PYTHONUNBUFFERED=1 \
    ENVIRONMENT=container \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TZ=America/Manaus

RUN playwright install chromium && playwright install-deps chromium
RUN mkdir -p logs data/output reports screenshots

# Copia o restante do código para o container.
COPY . .

CMD ["python", "bot.py"]
