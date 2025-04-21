import requests
from datetime import datetime
from app import create_app
from app.models import db, NoticiaCripto  # Ajusta si tu modelo tiene otro nombre

def obtener_noticias_gdelt(query="bitcoin"):
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "format": "json",
        "maxrecords": 5,
        "sort": "datedesc"
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        print("📡 Enviando petición a GDELT...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        print(f"✅ {len(data.get('articles', []))} noticias recibidas")

        return data.get("articles", [])
    except Exception as e:
        print(f"❌ Error al consultar GDELT: {e}")
        return []

def guardar_noticias_en_bd(articulos, activo="BTC"):
    app = create_app()

    with app.app_context():
        guardadas = 0
        for a in articulos:
            titulo = a.get("title")
            url = a.get("url")
            imagen = a.get("socialimage", None)
            fecha = a.get("seendate")

            if not titulo or not url or not fecha:
                continue

            try:
                noticia = NoticiaCripto(
                    Activo=activo,
                    FechaPublicacion=datetime.strptime(fecha, "%Y%m%dT%H%M%SZ"),
                    URL=url,
                    Imagen=imagen,
                    Titulo=titulo
                )
                db.session.add(noticia)
                guardadas += 1
            except Exception as e:
                print(f"⚠️ Error insertando noticia: {e}")

        db.session.commit()
        print(f"✅ {guardadas} noticias guardadas en la base de datos.")

if __name__ == "__main__":
    noticias = obtener_noticias_gdelt("bitcoin")
    if noticias:
        guardar_noticias_en_bd(noticias, "BTC")
    else:
        print("⚠️ No hay noticias para guardar.")
