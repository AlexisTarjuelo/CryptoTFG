import os
import base64
from decimal import Decimal
from functools import wraps

from flask import render_template, redirect, url_for, flash, session, request, Blueprint, current_app, make_response, \
    jsonify, g
from sqlalchemy import func
from app import db,csrf
from app.models import User, Asset, AssetPrice, Transaction, NoticiaCripto, PortfolioAsset, Holder, HolderCategory
from app.forms import LoginForm, RegisterForm, EditProfileForm
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
#BIOMETRICO

RP_ID = "cryptotfg.com"
ORIGIN = "https://cryptotfg.com"


auth_bp = Blueprint('auth', __name__, template_folder='templates')


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not g.user:
            flash("Debes iniciar sesión para acceder a esta página", "warning")
            return redirect(url_for('auth.login'))
        return view_func(*args, **kwargs)
    return wrapper

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(Email=form.email.data).first()
        if user and user.check_password(form.password.data):
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
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    sort_by = request.args.get('sort', 'marketcap')
    page = int(request.args.get('page', 1))
    per_page = 100

    subquery = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('max_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

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

    if sort_by == 'price':
        query = query.order_by(AssetPrice.PriceUSD.desc())
    elif sort_by == 'volume':
        query = query.order_by(AssetPrice.TotalVolume.desc())
    else:
        query = query.order_by(AssetPrice.MarketCap.desc())

    paginated = query.paginate(page=page, per_page=per_page)

    total_value = sum(float(p[5]) if p[5] else 0 for p in paginated.items)
    top_asset = max(paginated.items, key=lambda x: x[6] if x[6] else 0) if paginated.items else None
    change_24h = -932.21

    return render_template('dashboard.html',
        assets=paginated.items,
        total_value=total_value,
        top_asset=top_asset,
        change_24h=change_24h,
        page=page,
        total_pages=paginated.pages,
        sort_by=sort_by
    )


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

    return render_template('profile.html', form=form, user=user)

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

    latest_price = (
        db.session.query(
            AssetPrice.PriceUSD,
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume,
            AssetPrice.RecordedAt
        )
        .filter(AssetPrice.AssetID == asset.AssetID)
        .order_by(AssetPrice.RecordedAt.desc())
        .first()
    )

    price_history = (
        db.session.query(
            AssetPrice.RecordedAt,
            AssetPrice.PriceUSD
        )
        .filter(AssetPrice.AssetID == asset.AssetID)
        .order_by(AssetPrice.RecordedAt.asc())
        .all()
    )

    from decimal import Decimal
    max_supply = 21000000
    circulating_supply = 19500000
    total_supply = max_supply

    fdv = latest_price.MarketCap * (Decimal(max_supply) / Decimal(circulating_supply)) if latest_price and latest_price.MarketCap else None
    vol_mkt_cap = (latest_price.TotalVolume / latest_price.MarketCap * Decimal(100)) if latest_price and latest_price.TotalVolume and latest_price.MarketCap else None

    transactions = (
        Transaction.query
        .filter_by(AssetID=asset.AssetID)
        .order_by(Transaction.Timestamp.desc())
        .limit(10)
        .all()
    )

    # 📰 Noticias relacionadas con el activo (por Symbol)
    related_news = (
        NoticiaCripto.query
        .filter_by(Activo=asset.Symbol)
        .order_by(NoticiaCripto.FechaPublicacion.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "asset_detail.html",
        asset=asset,
        latest_price=latest_price,
        price_history=price_history,
        transactions=transactions,
        fdv=fdv,
        vol_mkt_cap=vol_mkt_cap,
        max_supply=max_supply,
        total_supply=total_supply,
        circulating_supply=circulating_supply,
        related_news=related_news
    )




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

        return jsonify({"success": True, "message": "✅ Autenticación biométrica exitosa"})

    except Exception as e:
        print("❌ Excepción en autenticación biométrica:", str(e))
        return jsonify({"success": False, "error": "Error al procesar autenticación"}), 500


@auth_bp.route('/versus')
def versus():
    return render_template('versus.html')

@auth_bp.route('/versus/assets')
def get_asset_list():
    assets = Asset.query.with_entities(Asset.Symbol, Asset.Name).all()
    return jsonify({
        "assets": [{"Symbol": s, "Name": n} for s, n in assets]
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
        .limit(180)  # Puedes ajustar este límite
        .all()
    )

    data = [
        [dt.strftime('%Y-%m-%d'), float(price)]
        for dt, price in history if price is not None
    ]

    return jsonify({
        "label": asset.Name,
        "symbol": asset.Symbol,
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

    total_value = sum(float(entry.PortfolioAsset.CurrentValueUSD or 0) for entry, _, _, _ in portfolio_entries)
    gain_loss = sum(
        ((float(entry.PortfolioAsset.CurrentValueUSD or 0) - float(entry.PortfolioAsset.PurchaseValueUSD or 0)) / float(entry.PortfolioAsset.PurchaseValueUSD or 1)) * 100
        for entry, _, _, _ in portfolio_entries
    )
    gain_loss_pct = round(gain_loss / len(portfolio_entries), 2) if portfolio_entries else 0

    return render_template('portfolio.html',
        portfolio=portfolio_entries,
        total_value=round(total_value, 2),
        gain_loss_pct=gain_loss_pct
    )

@auth_bp.route('/portfolio/add', methods=['POST'])
@login_required
def add_to_portfolio():
    data = request.get_json()
    user_id = session['user_id']

    asset = Asset.query.filter_by(Symbol=data['symbol']).first()
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    new_entry = PortfolioAsset(
        UserID=user_id,
        AssetID=asset.AssetID,
        Quantity=data['quantity'],
        PurchaseValueUSD=data['purchase_usd'],
        CurrentValueUSD=data['purchase_usd']  # puede actualizarse más adelante
    )
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({"success": True})

@auth_bp.route('/holders')
def holders_view():
    assets = Asset.query.order_by(Asset.Symbol).all()
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

