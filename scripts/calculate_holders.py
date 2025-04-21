from app import create_app
from app.models import db, Transaction, Holder, HolderCategory
from sqlalchemy import func
from collections import defaultdict

def calcular_saldos_por_activo():
    app = create_app()

    with app.app_context():
        print("🔍 Calculando balances de holders...")

        # Obtenemos todos los IDs únicos de activos
        activos = db.session.query(Transaction.AssetID).distinct().all()
        activos = [a[0] for a in activos]

        total_guardados = 0
        db.session.query(Holder).delete()  # Limpiar tabla antes de insertar nuevos datos

        for asset_id in activos:
            print(f"🪙 Procesando activo ID: {asset_id}")
            balances = defaultdict(lambda: 0)

            transacciones = Transaction.query.filter_by(AssetID=asset_id).order_by(Transaction.Timestamp).all()

            for tx in transacciones:
                if tx.FromAddress != "0x0000000000000000000000000000000000000000":
                    balances[tx.FromAddress] -= float(tx.Amount)

                if tx.ToAddress != "0x0000000000000000000000000000000000000000":
                    balances[tx.ToAddress] += float(tx.Amount)

            holders_validos = [
                (address, balance) for address, balance in balances.items() if balance > 0
            ]

            categorias = HolderCategory.query.all()

            for address, balance in holders_validos:
                categoria_id = None
                for cat in categorias:
                    if balance >= float(cat.MinBalance) and (cat.MaxBalance is None or balance <= float(cat.MaxBalance)):
                        categoria_id = cat.CategoryID
                        break

                holder = Holder(
                    AssetID=asset_id,
                    Address=address,
                    Balance=balance,
                    CategoryID=categoria_id
                )
                db.session.add(holder)
                total_guardados += 1

        db.session.commit()
        print(f"✅ Se guardaron {total_guardados} holders en total.")

if __name__ == "__main__":
    calcular_saldos_por_activo()
