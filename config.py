# app/config.py

class Config:
    SQLALCHEMY_DATABASE_URI = "mssql+pyodbc://sa:NuevaContraseñaSegura@localhost\\SQLEXPRESS/CRIPTOTFG?driver=ODBC+Driver+17+for+SQL+Server"
    SQLALCHEMY_TRACK_MODIFICATIONS = False