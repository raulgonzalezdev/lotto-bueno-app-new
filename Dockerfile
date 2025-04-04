FROM phidata/pgvector:16 as db

ENV POSTGRES_DB=lottobueno
ENV POSTGRES_USER=lottobueno
ENV POSTGRES_PASSWORD=lottobueno

# Copiar el archivo de backup y los scripts de inicialización al contenedor
#COPY lottobueno_backup.dump /docker-entrypoint-initdb.d/
#COPY init-db.sh /docker-entrypoint-initdb.d/
#COPY wait-for-it.sh /docker-entrypoint-initdb.d/
#COPY init.sql /docker-entrypoint-initdb.d/

#RUN chmod +x /docker-entrypoint-initdb.d/init-db.sh
#RUN chmod +x /docker-entrypoint-initdb.d/wait-for-it.sh

# Etapa 2: Configuración de la aplicación
FROM python:3.10-slim as app

WORKDIR /app

COPY . /app
# Crear el archivo .env directamente en el contenedor
RUN echo "POSTGRES_DB=lottobueno\nPOSTGRES_USER=lottobueno\nPOSTGRES_PASSWORD=lottobueno\nDATABASE_URL=postgresql://lottobueno:lottobueno@postgres:5432/lottobueno\nREDIS_URL=redis://localhost:6380/0" > /app/.env

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]