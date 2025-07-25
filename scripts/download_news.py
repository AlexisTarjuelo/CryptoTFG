import requests
from datetime import datetime
from app import create_app
from app.models import db, Asset, CryptoNews  # ⬅️ Nombre del modelo actualizado

def obtener_noticias_gdelt(query="bitcoin"):
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "format": "json",
        "maxrecords": 6,
        "sort": "datedesc"
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        print(f"❌ Error consultando noticias para '{query}': {e}")
        return []

def actualizar_noticias():
    app = create_app()
    with app.app_context():
        # 🧹 Borrar todas las noticias previas
        print("🧹 Eliminando noticias anteriores...")
        db.session.query(CryptoNews).delete()  # ⬅️ Modelo actualizado
        db.session.commit()

        hoy = datetime.utcnow().date()
        activos = Asset.query.filter(Asset.Symbol.isnot(None)).all()
        print(f"🔍 Obteniendo noticias para {len(activos)} activos...\n")

        total_guardadas = 0

        for asset in activos:
            symbol = asset.Symbol
            print(f"📡 Consultando noticias para: {symbol}")

            articulos = obtener_noticias_gdelt(symbol)
            guardadas = 0

            for a in articulos:
                titulo = a.get("title")
                url = a.get("url")
                imagen = a.get("socialimage")
                fecha_str = a.get("seendate")

                if not titulo or not url or not fecha_str:
                    continue

                try:
                    fecha = datetime.strptime(fecha_str, "%Y%m%dT%H%M%SZ")
                    if fecha.date() != hoy:
                        continue  # ⛔ Solo noticias de hoy

                    # 🛑 Evitar duplicados por URL
                    existe = CryptoNews.query.filter_by(Asset=symbol, URL=url).first()  # ⬅️ Campos actualizados
                    if existe:
                        continue

                    noticia = CryptoNews(
                        Asset=symbol,
                        PublicationDate=fecha,
                        URL=url,
                        Image=imagen,
                        Title=titulo
                    )
                    db.session.add(noticia)
                    guardadas += 1
                except Exception as e:
                    print(f"⚠️ Error guardando noticia de {symbol}: {e}")

            db.session.commit()
            print(f"✅ {guardadas} noticias guardadas para {symbol}.\n")
            total_guardadas += guardadas

        print(f"🎉 Total de noticias insertadas: {total_guardadas}")

if __name__ == "__main__":
    actualizar_noticias()
