FROM python:3.11-slim

# Evita prompts
ENV DEBIAN_FRONTEND=noninteractive

# 🔧 Requisitos y dependencias para pyodbc + driver oficial de Microsoft
RUN apt-get update && apt-get install -y \
    curl gnupg apt-transport-https \
    gcc g++ \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y \
    msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . .

# Asegura que Python vea la raíz
ENV PYTHONPATH=/app

# Instala dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expón el puerto para Railway
EXPOSE 8000

# Comando de inicio
CMD ["python", "run.py"]
