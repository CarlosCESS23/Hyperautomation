#Selecionando o versão do python
FROM python:3.12-slim

#Definindo ambiente de trabaalho
WORKDIR /app
#Copiando os conteúdos, como o requirements.txt
COPY api_ml/requirements.txt /app/api_ml/requirements.txt

# Instalando as bibliotecas
RUN pip install --no-cache-dir \
    -r /app/api_ml/requirements.txt

# Copiando os conteúdos desse diretorio
COPY . /app
# Abrindo na porta 8000
EXPOSE 8000

# Executandoa os comandos
CMD ["uvicorn", "api_ml.main:app", "--host", "0.0.0.0", "--port", "8000"]