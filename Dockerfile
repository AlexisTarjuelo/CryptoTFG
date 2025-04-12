FROM python:3.11-bullseye

ENV DEBIAN_FRONTEND=noninteractive

# Instala dependencias necesarias y agrega el repositorio de Microsoft
RUN apt-get update && apt-get install -y \
    curl gnupg apt-transport-https \
    gcc g++ \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Establece directorio de trabajo
WORKDIR /app

# Copia archivos
COPY . .

# Para que Python encuentre tu app
ENV PYTHONPATH=/app

# Instala dependencias Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Puerto expuesto por Flask
EXPOSE 8000

# Comando de arranque
CMD ["python", "run.py"]
