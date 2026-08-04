# Utilizando a imagem oficial do PLAYWRIGHT que será baseada em UBUNTU 22.04
FROM mcr.microsoft.com/playwright/python:v.1.40.0-jammy

# Definindo o diretório de trabalho
WORKDIR /app

#Copiando os requisitos do requirements.txt para otimizar o cache de build do docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiando os restante do código para container
COPY . .

#Desativando o buffer do Python para que os logs apareçam no terminal
ENV PYTHONUNBUFFERED=1

#Comando padrão que quando iniciar o docker, ele irá executar
CMD['python','bot.py']
