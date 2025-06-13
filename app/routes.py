import io
import os
import base64
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from decimal import Decimal, DivisionByZero, InvalidOperation
from functools import wraps

import numpy as np
import pyotp
import qrcode
from flask import render_template, redirect, url_for, flash, session, request, Blueprint, current_app, make_response, \
    jsonify, g
from sklearn.linear_model import LinearRegression
from sqlalchemy import func
from app import db,csrf
from app.models import User, Asset, AssetPrice, Transaction, NoticiaCripto, PortfolioAsset, Holder, HolderCategory
from app.forms import LoginForm, RegisterForm, EditProfileForm, TwoFactorForm, Disable2FAForm, RequestResetForm, \
    ResetPasswordForm
#BIOMETRICO

from webauthn import (
    generate_registration_options, verify_registration_response,
    generate_authentication_options, verify_authentication_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.structs import (
    RegistrationCredential, AuthenticatorAttestationResponse,
    AuthenticationCredential, AuthenticatorAssertionResponse,
    UserVerificationRequirement, ResidentKeyRequirement,
    AuthenticatorAttachment, AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url
import json

from scripts.send_email import send_reset_email

#BIOMETRICO

RP_ID = "cryptotfg.com"
ORIGIN = "https://cryptotfg.com"


auth_bp = Blueprint('auth', __name__, template_folder='templates')

def run_fetch_and_update():
    try:
        subprocess.run(["python", "scripts/fetch_assets.py"], check=True)
        subprocess.run(["python", "scripts/update_prices.py"], check=True)
        print("✅ Scripts ejecutados correctamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando scripts: {str(e)}")



def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not g.user:
            flash("Debes iniciar sesión para acceder a esta página", "warning")
            return redirect(url_for('auth.login'))
        return view_func(*args, **kwargs)
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not g.user or g.user.Role != 'admin':
            flash("❌ No tienes permiso para acceder a esta sección", "danger")
            return redirect(url_for('auth.dashboard'))
        return view_func(*args, **kwargs)
    return wrapper



@csrf.exempt
@login_required
@auth_bp.route('/admin/update-assets', methods=['POST'])
def update_assets():
    def run_assets():
        try:
            subprocess.run([sys.executable, 'scripts/fetch_assets.py'], check=True)
        except Exception as e:
            print(f"❌ Error actualizando activos: {e}")

    threading.Thread(target=run_assets).start()
    return jsonify({'success': True})


@csrf.exempt
@login_required
@auth_bp.route('/admin/update-prices', methods=['POST'])
def update_prices():
    def run_prices():
        try:
            subprocess.run([sys.executable, 'scripts/update_prices.py'], check=True)
        except Exception as e:
            print(f"❌ Error actualizando precios: {e}")

    threading.Thread(target=run_prices).start()
    return jsonify({'success': True})

@csrf.exempt
@login_required
@auth_bp.route('/admin/user/update/<int:user_id>', methods=['POST'])
def update_user(user_id):
    try:
        data = request.get_json()

        user = User.query.get_or_404(user_id)

        user.FirstName = data.get('first_name', user.FirstName)
        user.LastName = data.get('last_name', user.LastName)
        user.Email = data.get('email', user.Email)
        user.Phone = data.get('phone', user.Phone)

        new_role = data.get('role', user.Role)
        if new_role in ['admin', 'user']:
            user.Role = new_role

        db.session.commit()

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = User.query.get(user_id) if user_id else None

@auth_bp.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@auth_bp.route('/admin/assets')
@admin_required
def admin_assets():
    assets = Asset.query.order_by(Asset.Name).all()
    return render_template('admin_assets.html', assets=assets)

@csrf.exempt
@auth_bp.route('/admin/user/admin-update/<int:user_id>', methods=['POST'])
@admin_required
def admin_update_user(user_id):
    data = request.get_json()
    user = User.query.get_or_404(user_id)

    user.FirstName = data.get("first_name", user.FirstName)
    user.LastName = data.get("last_name", user.LastName)
    user.Email = data.get("email", user.Email)
    user.Phone = data.get("phone", user.Phone)
    user.Role = data.get("role", user.Role)

    db.session.commit()
    return jsonify({"success": True})





@auth_bp.route('/admin/user/delete/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == session.get("user_id"):
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True})

@auth_bp.route('/admin/asset/update/<int:asset_id>', methods=['POST'])
@csrf.exempt  # 👈 ¡añade esto aquí!
@admin_required
@login_required
def update_asset(asset_id):
    if g.user.Role != 'admin':
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = request.get_json()
    asset = Asset.query.get_or_404(asset_id)

    asset.Name = data.get('name')
    asset.Symbol = data.get('symbol')
    asset.AssetAddress = data.get('address')
    asset.Decimals = data.get('decimals')
    asset.Source = data.get('source')

    db.session.commit()

    return jsonify({"success": True})



@auth_bp.route('/admin/asset/delete/<int:asset_id>', methods=['DELETE'])
@csrf.exempt  # 👈 ¡añade esto aquí!
@admin_required
@login_required
def delete_asset(asset_id):
    if g.user.Role != 'admin':
        return jsonify({"success": False, "error": "No autorizado"}), 403

    asset = Asset.query.get_or_404(asset_id)
    db.session.delete(asset)
    db.session.commit()

    return jsonify({"success": True})



@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(Email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if user.two_factor_enabled:
                session['pending_2fa'] = user.UserID
                return redirect(url_for('auth.verify_2fa'))
            else:
                session['user_id'] = user.UserID
                flash("✅ Inicio de sesión exitoso", "success")
                return redirect(url_for('auth.dashboard'))
        else:
            flash("❌ Credenciales incorrectas", "danger")
    return render_template("login.html", form=form, login_page=True)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(Email=form.email.data).first()
        if existing:
            flash("❌ Este correo ya está registrado", "danger")
            return redirect(url_for('auth.register'))

        new_user = User(
            FirstName=form.first_name.data,
            LastName=f"{form.last_name.data} {form.second_last_name.data}",
            Email=form.email.data,
            Phone=form.phone.data,
            IsAdult=form.is_adult.data,
            AcceptedTerms=form.accept_terms.data
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        flash("✅ Registro exitoso, ahora puedes iniciar sesión", "success")
        return redirect(url_for('auth.login'))
    return render_template("register.html", form=form, login_page=True)


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get("user_id")
    sort_by = request.args.get('sort', 'marketcap')
    page = int(request.args.get('page', 1))
    per_page = 100

    # Subconsulta para obtener el último precio por asset
    subquery = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('max_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

    # Consulta principal para mostrar los activos en tabla
    query = (
        db.session.query(
            Asset.AssetID,
            Asset.Name,
            Asset.Symbol,
            Asset.LogoURL,
            Asset.id_coin,
            AssetPrice.PriceUSD,
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(AssetPrice, Asset.AssetID == AssetPrice.AssetID)
        .join(subquery, (AssetPrice.AssetID == subquery.c.AssetID) & (AssetPrice.RecordedAt == subquery.c.max_date))
    )

    # Ordenamiento
    if sort_by == 'price':
        query = query.order_by(AssetPrice.PriceUSD.desc())
    elif sort_by == 'volume':
        query = query.order_by(AssetPrice.TotalVolume.desc())
    else:
        query = query.order_by(AssetPrice.MarketCap.desc())

    paginated = query.paginate(page=page, per_page=per_page)

    # 💰 Valor total del portafolio real
    portfolio_assets = PortfolioAsset.query.filter_by(UserID=user_id).all()
    total_value = sum(float(p.CurrentValueUSD or 0) for p in portfolio_assets)

    # 📉 Cambio real en 24h
    change_24h = 0
    for entry in portfolio_assets:
        latest = AssetPrice.query.filter_by(AssetID=entry.AssetID).order_by(AssetPrice.RecordedAt.desc()).first()
        day_ago = AssetPrice.query.filter(
            AssetPrice.AssetID == entry.AssetID,
            AssetPrice.RecordedAt <= datetime.utcnow() - timedelta(hours=24)
        ).order_by(AssetPrice.RecordedAt.desc()).first()

        if latest and day_ago and day_ago.PriceUSD:
            try:
                price_diff = Decimal(latest.PriceUSD) - Decimal(day_ago.PriceUSD)
                change_24h += price_diff * Decimal(entry.Quantity)
            except:
                continue

    change_24h = float(change_24h)

    # 🥇 Top Asset por MarketCap entre todos los activos
    top_asset = max(
        paginated.items,
        key=lambda x: float(x[6]) if x[6] else 0
    ) if paginated.items else None

    # 🔄 Preparar historiales de 7 días para cada Asset
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    asset_ids = [a[0] for a in paginated.items]  # a[0] = AssetID

    # Consulta los precios históricos de los últimos 7 días para esos activos
    price_data = (
        db.session.query(AssetPrice.AssetID, AssetPrice.RecordedAt, AssetPrice.PriceUSD)
        .filter(AssetPrice.AssetID.in_(asset_ids))
        .filter(AssetPrice.RecordedAt >= seven_days_ago)
        .order_by(AssetPrice.AssetID, AssetPrice.RecordedAt.asc())
        .all()
    )

    from collections import defaultdict
    sparkline_map = defaultdict(list)

    for aid, dt, price in price_data:
        if price is not None:
            sparkline_map[aid].append((dt.strftime('%Y-%m-%d'), float(price)))

    # Enriquecer cada item de la tabla con su sparkline y cambio %
    enriched_assets = []
    for a in paginated.items:
        asset_id = a[0]
        sparkline = sparkline_map.get(asset_id, [])
        if sparkline and len(sparkline) >= 2:
            price_start = sparkline[0][1]
            price_end = sparkline[-1][1]
            price_change_percent = ((price_end - price_start) / price_start) * 100 if price_start else 0
        else:
            price_change_percent = 0
        enriched_assets.append((*a, sparkline, price_change_percent))

    return render_template(
        'dashboard.html',
        assets=enriched_assets,
        total_value=round(total_value, 2),
        change_24h=round(change_24h, 2),
        top_asset=top_asset,
        page=page,
        total_pages=paginated.pages,
        sort_by=sort_by
    )


@auth_bp.route('/market/overview-data')
def market_overview_data():
    # Subconsulta: fecha más reciente por Asset
    latest_dates = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('latest_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

    # Consulta principal: último registro por Asset
    latest_prices = (
        db.session.query(
            AssetPrice.AssetID,
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(latest_dates,
              (AssetPrice.AssetID == latest_dates.c.AssetID) &
              (AssetPrice.RecordedAt == latest_dates.c.latest_date))
        .all()
    )

    # Sumar los valores actuales
    total_market_cap = sum(float(p.MarketCap or 0) for p in latest_prices)
    total_volume = sum(float(p.TotalVolume or 0) for p in latest_prices)

    return jsonify({
        "market_cap": total_market_cap,
        "volume": total_volume
    })

@auth_bp.route('/market/history')
def market_history():
    from sqlalchemy import cast, Date
    from collections import defaultdict
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    last_30_days = today - timedelta(days=30)

    # Subconsulta: última fecha por asset y día (solo últimos 30 días)
    latest_per_day = (
        db.session.query(
            AssetPrice.AssetID,
            cast(AssetPrice.RecordedAt, Date).label('day'),
            func.max(AssetPrice.RecordedAt).label('latest_time')
        )
        .filter(cast(AssetPrice.RecordedAt, Date) >= last_30_days)
        .group_by(AssetPrice.AssetID, cast(AssetPrice.RecordedAt, Date))
        .subquery()
    )

    # Obtener precios diarios más recientes por asset
    latest_prices = (
        db.session.query(
            cast(AssetPrice.RecordedAt, Date).label("day"),
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(
            latest_per_day,
            (AssetPrice.AssetID == latest_per_day.c.AssetID) &
            (cast(AssetPrice.RecordedAt, Date) == latest_per_day.c.day) &
            (AssetPrice.RecordedAt == latest_per_day.c.latest_time)
        )
        .filter(cast(AssetPrice.RecordedAt, Date) >= last_30_days)
        .order_by(cast(AssetPrice.RecordedAt, Date).asc())
        .all()
    )

    # Agrupar por día y sumar MarketCap y Volume
    daily = defaultdict(lambda: {"market_cap": 0, "volume": 0})
    for day, mcap, vol in latest_prices:
        if mcap:
            daily[day]["market_cap"] += float(mcap)
        if vol:
            daily[day]["volume"] += float(vol)

    sorted_days = sorted(daily.keys())
    return jsonify({
        "dates": [d.strftime("%Y-%m-%d") for d in sorted_days],
        "market_cap": [daily[d]["market_cap"] for d in sorted_days],
        "volume": [daily[d]["volume"] for d in sorted_days]
    })





@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("👋 Sesión cerrada", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    form = EditProfileForm()
    disable_2fa_form = Disable2FAForm()  # 👈 NUEVO

    # Cargar avatares
    avatar_dir = os.path.join(current_app.static_folder, 'images', 'avatars')
    avatar_files = [f for f in os.listdir(avatar_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    form.avatar.choices = [(f, f.split('.')[0].capitalize()) for f in avatar_files]

    if request.method == 'GET':
        form.first_name.data = user.FirstName
        form.phone.data = user.Phone
        form.avatar.data = user.Avatar

    if form.validate_on_submit():
        user.FirstName = form.first_name.data
        user.Phone = form.phone.data
        user.Avatar = form.avatar.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash("✅ Perfil actualizado", "success")
        return redirect(url_for('auth.dashboard'))

    return render_template('profile.html', form=form, user=user, disable_2fa_form=disable_2fa_form)

@auth_bp.route('/dashboard/export')
def export_dashboard_csv():
    # Subconsulta para último precio por Asset
    subquery = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('max_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

    # Consulta principal
    query = (
        db.session.query(
            Asset.Name,
            Asset.Symbol,
            AssetPrice.PriceUSD,
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(AssetPrice, Asset.AssetID == AssetPrice.AssetID)
        .join(subquery, (AssetPrice.AssetID == subquery.c.AssetID) & (AssetPrice.RecordedAt == subquery.c.max_date))
        .order_by(AssetPrice.MarketCap.desc())
    )

    # Generar contenido CSV
    csv_content = 'Name,Symbol,PriceUSD,MarketCap,TotalVolume\n'
    for name, symbol, price, marketcap, volume in query:
        price = price or 0
        marketcap = marketcap or 0
        volume = volume or 0
        csv_content += f'{name},{symbol},{price},{marketcap},{volume}\n'

    # Preparar respuesta
    response = make_response(csv_content)
    response.headers['Content-Disposition'] = 'attachment; filename=\"dashboard_export.csv\"'
    response.mimetype = 'text/csv'
    return response

@auth_bp.route('/asset/<string:id_coin>')
def asset_detail(id_coin):
    asset = Asset.query.filter_by(id_coin=id_coin).first_or_404()

    # Último precio
    latest_price = (
        db.session.query(AssetPrice)
        .filter_by(AssetID=asset.AssetID)
        .order_by(AssetPrice.RecordedAt.desc())
        .first()
    )

    # Historial de precios para gráfico
    price_history = [
        (p.RecordedAt.strftime('%Y-%m-%d'), float(p.PriceUSD))
        for p in db.session.query(AssetPrice.RecordedAt, AssetPrice.PriceUSD)
            .filter(AssetPrice.AssetID == asset.AssetID)
            .order_by(AssetPrice.RecordedAt.asc())
            .all()
    ]

    # ----- MODELO DE PREDICCIÓN POLINÓMICA -----
    prediction_labels = []
    prediction_data = []
    if len(price_history) >= 7:  # mínimo razonable para curva
        try:
            from sklearn.preprocessing import PolynomialFeatures

            X = np.arange(len(price_history)).reshape(-1, 1)
            y = np.array([p[1] for p in price_history])

            poly = PolynomialFeatures(degree=3)
            X_poly = poly.fit_transform(X)

            model = LinearRegression().fit(X_poly, y)

            future_X = np.arange(len(price_history), len(price_history) + 30).reshape(-1, 1)
            future_X_poly = poly.transform(future_X)
            future_y = model.predict(future_X_poly)

            prediction_data = future_y.tolist()
            prediction_labels = [
                (datetime.utcnow().date() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 31)
            ]
        except Exception as e:
            print(f"❌ Error al generar predicción polinómica: {e}")

    # Valores base
    max_supply = latest_price.MaxSupply if latest_price else None
    circulating_supply = latest_price.CirculatingSupply if latest_price else None
    total_supply = latest_price.TotalSupply if latest_price else None
    market_cap = latest_price.MarketCap if latest_price else None

    # Tratar max_supply = 0 como sin límite
    if max_supply == 0:
        max_supply = None

    # Cálculo FDV
    fdv = None
    fdv_infinite = False
    if market_cap and circulating_supply:
        if max_supply:
            try:
                fdv = market_cap * (Decimal(max_supply) / Decimal(circulating_supply))
            except (DivisionByZero, InvalidOperation):
                fdv = None
        else:
            fdv_infinite = True  # FDV = infinito

    # Volumen / Market Cap (%)
    vol_mkt_cap = (
        latest_price.TotalVolume / latest_price.MarketCap * Decimal(100)
        if latest_price and latest_price.TotalVolume and latest_price.MarketCap
        else None
    )

    # Transacciones recientes
    transactions = (
        Transaction.query
        .filter_by(AssetID=asset.AssetID)
        .order_by(Transaction.Timestamp.desc())
        .limit(10)
        .all()
    )

    # Noticias relacionadas
    related_news = (
        NoticiaCripto.query
        .filter_by(Activo=asset.Symbol)
        .order_by(NoticiaCripto.FechaPublicacion.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "asset_detail.html",
        asset=asset,
        latest_price=latest_price,
        price_history=price_history,
        prediction_labels=prediction_labels,
        prediction_data=prediction_data,
        transactions=transactions,
        fdv=fdv,
        fdv_infinite=fdv_infinite,
        vol_mkt_cap=vol_mkt_cap,
        max_supply=max_supply,
        total_supply=total_supply,
        circulating_supply=circulating_supply,
        related_news=related_news
    )


@login_required
@auth_bp.route('/about')
def about():
    return render_template('about.html')

@auth_bp.route('/search')
def search_asset():
    query = request.args.get('q', '').strip().lower()

    if not query:
        flash("Introduce un valor para buscar.", "warning")
        return redirect(url_for('auth.dashboard'))

    # Buscar por symbol o id_coin
    asset = Asset.query.filter(
        (Asset.Symbol.ilike(query)) | (Asset.id_coin.ilike(query))
    ).first()

    if asset:
        return redirect(url_for('auth.asset_detail', id_coin=asset.id_coin))

    flash("Activo no encontrado.", "danger")
    return redirect(url_for('auth.dashboard'))


@auth_bp.route('/search/suggestions')
def search_suggestions():
    query = request.args.get('q', '').strip().lower()

    if not query or len(query) < 2:
        return jsonify([])

    suggestions = Asset.query.filter(
        (Asset.Name.ilike(f"%{query}%")) |
        (Asset.Symbol.ilike(f"%{query}%")) |
        (Asset.id_coin.ilike(f"%{query}%"))
    ).limit(8).all()

    return jsonify([
        {
            "name": asset.Name,
            "symbol": asset.Symbol,
            "id_coin": asset.id_coin
        } for asset in suggestions
    ])



@auth_bp.route('/biometric/start-registration')
@login_required
def start_biometric_registration():
    if not g.user:
        return jsonify({"error": "No autenticado"}), 403

    user_id = str(g.user.UserID).encode()
    username = g.user.Email

    session['biometric_challenge'] = base64.b64encode(os.urandom(32)).decode()

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name="CryptoTFG",
        user_id=user_id,
        user_name=username,
        user_display_name=g.user.FirstName,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    session['biometric_challenge'] = base64.b64encode(options.challenge).decode()

    options_json = json.loads(options_to_json(options))
    options_json['challenge'] = bytes_to_base64url(options.challenge)
    options_json['user']['id'] = bytes_to_base64url(options.user.id)

    return jsonify(options_json)

@auth_bp.route('/biometric/finish-registration', methods=['POST'])
def finish_biometric_registration():
    if not g.user:
        return jsonify({"success": False, "error": "No autenticado"}), 403

    challenge_b64 = session.get('biometric_challenge')
    if not challenge_b64:
        return jsonify({'success': False, 'error': 'Sesión inválida'}), 400

    try:
        challenge = base64.b64decode(challenge_b64)
        data = request.get_json()

        credential = RegistrationCredential(
            id=data['id'],
            raw_id=base64url_to_bytes(data['rawId']),
            response=AuthenticatorAttestationResponse(
                client_data_json=base64url_to_bytes(data['response']['clientDataJSON']),
                attestation_object=base64url_to_bytes(data['response']['attestationObject']),
            ),
            type=data['type'],
            authenticator_attachment=None,
        )

        verification = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            require_user_verification=True
        )

        # 👇 Guarda en base de datos de forma correcta
        user = User.query.get(session["user_id"])
        user.BiometricCredentialID = bytes_to_base64url(verification.credential_id)
        user.BiometricPublicKey = bytes_to_base64url(verification.credential_public_key)  # ✅ Clave completa
        user.SignCount = verification.sign_count

        db.session.commit()

        return jsonify({"success": True, "message": "✅ Biometría registrada correctamente"})

    except Exception as e:
        print("❌ Error biométrico:", str(e))
        return jsonify({"success": False, "error": "Error al procesar la respuesta biométrica"}), 400


@auth_bp.route('/biometric/start-authentication', methods=['POST'])
def start_authentication():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(Email=email).first()
    if not user or not user.BiometricCredentialID:
        return jsonify({"success": False, "error": "❌ Usuario no encontrado o sin biometría registrada"}), 404

    options = generate_authentication_options(
        rp_id=RP_ID,
        user_verification=UserVerificationRequirement.REQUIRED,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(user.BiometricCredentialID))
        ]
    )

    session.permanent = True  # 👈 Importante si usas cookies de sesión
    session["user_id"] = user.UserID
    session["auth_challenge"] = base64.b64encode(options.challenge).decode()

    response = {
        "challenge": bytes_to_base64url(options.challenge),
        "rpId": options.rp_id,
        "timeout": options.timeout,
        "userVerification": options.user_verification,
        "allowCredentials": [
            {
                "type": "public-key",
                "id": user.BiometricCredentialID,
                "transports": []
            }
        ]
    }

    return jsonify(response)


@auth_bp.route('/biometric/finish-authentication', methods=['POST'])
def finish_authentication():
    challenge_b64 = session.get("auth_challenge")
    user_id = session.get("user_id")

    if not challenge_b64 or not user_id:
        return jsonify({"success": False, "error": "Sesión inválida"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "Usuario no válido"}), 404

    try:
        data = request.get_json()

        # Decodificación segura de datos del frontend
        raw_id = base64url_to_bytes(data["rawId"])
        client_data_json = base64url_to_bytes(data["response"]["clientDataJSON"])
        authenticator_data = base64url_to_bytes(data["response"]["authenticatorData"])
        signature = base64url_to_bytes(data["response"]["signature"])
        user_handle = None

        if data["response"].get("userHandle"):
            user_handle = base64url_to_bytes(data["response"]["userHandle"])

        # Debug opcional
        print("📦 Autenticando usuario:", user.Email)
        print("📦 raw_id:", raw_id)
        print("📦 authenticator_data:", authenticator_data)
        print("📦 client_data_json:", client_data_json)
        print("📦 signature:", signature)
        print("📦 user_handle:", user_handle)

        credential = AuthenticationCredential(
            id=data["id"],
            raw_id=raw_id,
            response=AuthenticatorAssertionResponse(
                client_data_json=client_data_json,
                authenticator_data=authenticator_data,
                signature=signature,
                user_handle=user_handle
            ),
            type=data["type"]
        )

        # Validar que el credential_id coincide con el del usuario
        if raw_id != base64url_to_bytes(user.BiometricCredentialID):
            return jsonify({"success": False, "error": "❌ Credential ID no coincide con el registrado"}), 403

        public_key_bytes = base64url_to_bytes(user.BiometricPublicKey)

        # Verificación WebAuthn
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64.b64decode(challenge_b64),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=public_key_bytes,
            credential_current_sign_count=user.SignCount,
            require_user_verification=True
        )

        # Actualizar contador de firma
        user.SignCount = verification.new_sign_count
        db.session.commit()

        # ⚠️ Si tiene 2FA, redirigir a verificación
        if user.two_factor_enabled:
            session.pop("user_id", None)  # Limpiar login previo
            session["pending_2fa"] = user.UserID
            return jsonify({
                "success": True,
                "message": "✅ Biometría verificada. Redirigiendo a verificación 2FA",
                "redirect_to": "/2fa/verify"
            })

        # Si no tiene 2FA, login completo
        session["user_id"] = user.UserID
        return jsonify({
            "success": True,
            "message": "✅ Autenticación biométrica exitosa",
            "redirect_to": "/dashboard"
        })

    except Exception as e:
        print("❌ Excepción en autenticación biométrica:", str(e))
        return jsonify({"success": False, "error": "Error al procesar autenticación"}), 500



@auth_bp.route('/versus')
def versus():
    return render_template('versus.html')

@auth_bp.route('/versus/assets')
def get_asset_list():
    assets = Asset.query.with_entities(Asset.Symbol, Asset.Name, Asset.LogoURL).all()
    return jsonify({
        "assets": [{"Symbol": s, "Name": n, "LogoURL": l} for s, n, l in assets]
    })



@auth_bp.route('/versus/data')
def get_asset_data():
    symbol = request.args.get('symbol')

    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400

    asset = Asset.query.filter_by(Symbol=symbol).first()
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    history = (
        db.session.query(AssetPrice.RecordedAt, AssetPrice.PriceUSD)
        .filter_by(AssetID=asset.AssetID)
        .order_by(AssetPrice.RecordedAt.asc())
        .limit(180)
        .all()
    )

    data = [
        [dt.strftime('%Y-%m-%d'), float(price)]
        for dt, price in history if price is not None
    ]

    return jsonify({
        "label": asset.Name,
        "symbol": asset.Symbol,
        "logo_url": asset.LogoURL,  # <-- agregado
        "data": data
    })



@auth_bp.route('/portfolio')
@login_required
def portfolio():
    user = User.query.get(session['user_id'])

    portfolio_entries = (
        db.session.query(
            PortfolioAsset,
            Asset.Name,
            Asset.Symbol,
            Asset.LogoURL
        )
        .join(Asset, PortfolioAsset.AssetID == Asset.AssetID)
        .filter(PortfolioAsset.UserID == user.UserID)
        .all()
    )

    # Refrescar valores actuales
    for entry, _, _, _ in portfolio_entries:
        latest_price = (
            AssetPrice.query
            .filter_by(AssetID=entry.AssetID)
            .order_by(AssetPrice.RecordedAt.desc())
            .first()
        )
        if latest_price:
            entry.CurrentValueUSD = float(entry.Quantity) * float(latest_price.PriceUSD)
    db.session.commit()

    total_value = sum(float(entry.CurrentValueUSD or 0) for entry, _, _, _ in portfolio_entries)
    gain_loss = sum(
        ((float(entry.CurrentValueUSD or 0) - float(entry.PurchaseValueUSD or 0)) / float(
            entry.PurchaseValueUSD or 1)) * 100
        for entry, _, _, _ in portfolio_entries
    )

    gain_loss_pct = round(gain_loss / len(portfolio_entries), 2) if portfolio_entries else 0

    return render_template('portfolio.html',
        portfolio=portfolio_entries,
        total_value=round(total_value, 2),
        gain_loss_pct=gain_loss_pct
    )



@auth_bp.route('/portfolio/add', methods=['POST'])
@csrf.exempt  # Evita errores 400 por CSRF en llamadas con fetch
@login_required
def add_to_portfolio():
    print("🔔 Llamada a /portfolio/add")

    data = request.get_json()
    print("📦 Datos recibidos:", data)

    if not data or 'symbol' not in data or 'quantity' not in data or 'purchase_usd' not in data:
        return jsonify({"error": "❌ Datos incompletos"}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "No autenticado"}), 403

    # Convertir a Decimal para evitar errores al operar con Numeric
    try:
        quantity = Decimal(str(data['quantity']))
        purchase_usd = Decimal(str(data['purchase_usd']))
    except Exception as e:
        print("❌ Error al convertir a Decimal:", e)
        return jsonify({"error": "Formato inválido"}), 400

    asset = Asset.query.filter_by(Symbol=data['symbol']).first()
    if not asset:
        return jsonify({"error": "Activo no encontrado"}), 404

    # Precio actual
    latest_price = (
        db.session.query(AssetPrice)
        .filter_by(AssetID=asset.AssetID)
        .order_by(AssetPrice.RecordedAt.desc())
        .first()
    )
    current_price = Decimal(str(latest_price.PriceUSD)) if latest_price else Decimal("1")

    existing = PortfolioAsset.query.filter_by(UserID=user_id, AssetID=asset.AssetID).first()

    if existing:
        existing.Quantity += quantity
        existing.PurchaseValueUSD += purchase_usd
        existing.CurrentValueUSD = current_price * existing.Quantity
        print("📝 Actualizado portfolio existente")
    else:
        new_entry = PortfolioAsset(
            UserID=user_id,
            AssetID=asset.AssetID,
            Quantity=quantity,
            PurchaseValueUSD=purchase_usd,
            CurrentValueUSD=current_price * quantity
        )
        db.session.add(new_entry)
        print("📦 Nuevo asset agregado al portfolio")

    db.session.commit()
    return jsonify({"success": True})


@auth_bp.route('/portfolio/assets')
@login_required
def get_portfolio_assets():
    assets = (
        db.session.query(Asset.Symbol, Asset.Name)
        .order_by(Asset.Name)
        .all()
    )
    return jsonify([
        {"symbol": symbol, "name": name}
        for symbol, name in assets
    ])

@auth_bp.route('/portfolio/price/<symbol>')
@login_required
def get_latest_price(symbol):
    asset = Asset.query.filter_by(Symbol=symbol.upper()).first()
    if not asset:
        return jsonify({"error": "Activo no encontrado"}), 404

    latest_price = (
        AssetPrice.query
        .filter_by(AssetID=asset.AssetID)
        .order_by(AssetPrice.RecordedAt.desc())
        .first()
    )

    if not latest_price:
        return jsonify({"error": "No hay precio registrado"}), 404

    return jsonify({"price": float(latest_price.PriceUSD)})


@auth_bp.route('/portfolio/delete', methods=['POST'])
@csrf.exempt  # ← Añade esta línea
@login_required
def delete_from_portfolio():
    data = request.get_json()
    user_id = session['user_id']
    asset_symbol = data.get("symbol")

    asset = Asset.query.filter_by(Symbol=asset_symbol).first()
    if not asset:
        return jsonify({"error": "Activo no encontrado"}), 404

    deleted = PortfolioAsset.query.filter_by(UserID=user_id, AssetID=asset.AssetID).delete()
    db.session.commit()

    return jsonify({"success": deleted > 0})


@auth_bp.route('/holders')
def holders_view():
    # Subconsulta: IDs de activos con holders
    asset_ids_with_holders = (
        db.session.query(Holder.AssetID)
        .group_by(Holder.AssetID)
        .having(func.count(Holder.HolderID) > 0)
        .subquery()
    )

    # Consulta final: traer solo esos activos completos
    assets = (
        db.session.query(Asset)
        .join(asset_ids_with_holders, Asset.AssetID == asset_ids_with_holders.c.AssetID)
        .order_by(Asset.Symbol)
        .all()
    )

    categories = HolderCategory.query.order_by(HolderCategory.MinBalance).all()
    return render_template("holders.html", assets=assets, categories=categories)

@auth_bp.route('/holders/data')
def holders_data():
    holders = (
        db.session.query(Holder)
        .join(Asset, Holder.AssetID == Asset.AssetID)
        .outerjoin(HolderCategory, Holder.CategoryID == HolderCategory.CategoryID)
        .all()
    )

    holders_json = []
    for h in holders:
        holders_json.append({
            "address": h.Address,
            "balance": float(h.Balance),
            "asset": f"{h.asset.Name} ({h.asset.Symbol})",
            "symbol": h.asset.Symbol,  # este es clave para filtrar
            "category": h.category.Name if h.category else "Sin categoría"
        })

    return jsonify(holders_json)


# --- NUEVA RUTA EN FLASK (routes.py o donde tengas las views) ---
# Nueva ruta en auth_bp/routes.py o similar
from flask import request, jsonify
from sqlalchemy import func, desc
from app.models import Holder, Asset, HolderCategory

@auth_bp.route('/holders/summary')
def holders_summary():
    symbol = request.args.get("symbol")
    category = request.args.get("category")

    query = Holder.query.join(Asset).outerjoin(HolderCategory)

    if symbol:
        query = query.filter(Asset.Symbol.ilike(symbol))
    if category:
        query = query.filter(HolderCategory.Name.ilike(category))

    holders = query.all()

    total_holders = len(holders)
    total_balance = sum(h.Balance for h in holders)

    category_counts = {}
    for h in holders:
        cat = h.category.Name if h.category else "Sin categoría"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    most_common_category = max(category_counts, key=category_counts.get) if category_counts else "-"

    return jsonify({
        "total_holders": total_holders,
        "total_balance": total_balance,
        "most_common_category": most_common_category
    })

@auth_bp.route('/2fa/setup')
@login_required
def setup_2fa():
    user = User.query.get(session['user_id'])
    form = TwoFactorForm()

    if not user.two_factor_secret:
        user.generate_two_factor_secret()
        db.session.commit()

    otp_uri = user.get_otp_uri()
    qr_img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template("2fa_setup.html", qr_code=qr_b64, form=form)

@auth_bp.route('/2fa/confirm', methods=['POST'])
@login_required
def confirm_2fa():
    form = TwoFactorForm()
    user = User.query.get(session['user_id'])

    if form.validate_on_submit():
        code = form.otp_code.data
        totp = pyotp.TOTP(user.two_factor_secret)

        if totp.verify(code):
            user.two_factor_enabled = True
            db.session.commit()
            flash("✅ 2FA activado correctamente", "success")
            return redirect(url_for('auth.profile'))
        else:
            flash("❌ Código incorrecto. Intenta nuevamente.", "danger")
            return redirect(url_for('auth.setup_2fa'))

    # Si el form no es válido
    flash("❌ Error en el formulario.", "danger")
    return redirect(url_for('auth.setup_2fa'))

@auth_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    form = Disable2FAForm()
    user = User.query.get(session['user_id'])

    if form.validate_on_submit():
        user.two_factor_enabled = False
        user.two_factor_secret = None
        db.session.commit()
        flash("🔓 2FA desactivado con éxito", "info")
    else:
        flash("❌ Error al desactivar 2FA. Inténtalo de nuevo.", "danger")

    return redirect(url_for('auth.profile'))

@auth_bp.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa():
    if 'pending_2fa' not in session:
        flash("Sesión inválida", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['pending_2fa'])
    form = TwoFactorForm()

    if form.validate_on_submit():
        totp = pyotp.TOTP(user.two_factor_secret)
        if totp.verify(form.otp_code.data):
            session['user_id'] = user.UserID
            session.pop('pending_2fa', None)
            flash("✅ 2FA verificado correctamente", "success")
            return redirect(url_for('auth.dashboard'))
        else:
            flash("❌ Código incorrecto", "danger")

    return render_template("2fa_verify.html", form=form)

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(Email=form.email.data).first()
        if user:
            from scripts.send_email import send_reset_email
            send_reset_email(user)

        flash("📧 Se ha enviado un enlace de recuperación a tu correo si existe en el sistema.", "info")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html", form=form, login_page=True)



@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash("❌ Enlace inválido o expirado", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.two_factor_enabled = False  # ✅ Opcional: desactiva 2FA al recuperar
        user.two_factor_secret = None
        db.session.commit()
        flash("✅ Contraseña actualizada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", form=form, login_page=True)
