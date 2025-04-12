# Usa una imagen base ligera de Python
FROM python:3.11-slim

# Evita prompts en instalaciones
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependencias necesarias del sistema (para pyodbc)
RUN apt-get update && apt-get install -y \
    gcc g++ \
    curl \
    gnupg \
    unixodbc \
    unixodbc-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . .

# Instala dependencias Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expón el puerto que usará Flask
EXPOSE 8000

# Comando de inicio (Railway detecta esto)
CMD ["python", "run.py"]
