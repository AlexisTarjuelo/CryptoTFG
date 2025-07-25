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
from app.models import User, Asset, AssetPrice, Transaction, CryptoNews, PortfolioAsset, Holder, HolderCategory
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

from functools import wraps
from flask import g, session, redirect, url_for, jsonify, request

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            if request.method in ['POST', 'DELETE', 'PUT']:
                return jsonify({"error": "No autenticado"}), 401
            return redirect(url_for('auth.login'))

        if not g.user or g.user.Role != 'admin':
            if request.method in ['POST', 'DELETE', 'PUT']:
                return jsonify({"error": "No autorizado"}), 403
            return redirect(url_for('auth.dashboard'))

        return view_func(*args, **kwargs)
    return wrapper



from app.services.asset_service import update_assets_background, update_prices_background

@csrf.exempt
@login_required
@auth_bp.route('/admin/update-assets', methods=['POST'])
def update_assets():
    update_assets_background()
    return jsonify({'success': True})


@csrf.exempt
@login_required
@auth_bp.route('/admin/update-prices', methods=['POST'])
def update_prices():
    update_prices_background()
    return jsonify({'success': True})

from flask import request, jsonify, session, render_template
from app.services.user_service import (
    update_user as update_user_service,
    get_all_users,
    admin_update_user as admin_update_user_service,
    delete_user as delete_user_service
)


# ✅ Actualiza un usuario (datos generales)
@auth_bp.route('/admin/user/update/<int:user_id>', methods=['POST'])
@csrf.exempt
@login_required
def update_user(user_id):
    try:
        data = request.get_json()
        update_user_service(user_id, data)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ✅ Vista de administración de usuarios
@auth_bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = get_all_users()
    return render_template('admin_users.html', users=users)


# ✅ Cambia el rol de un usuario (admin/user)
@auth_bp.route('/admin/user/admin-update/<int:user_id>', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def admin_update_user(user_id):
    data = request.get_json()
    admin_update_user_service(user_id, data)
    return jsonify({"success": True})


# ✅ Elimina un usuario (no puede eliminarse a sí mismo)
@auth_bp.route('/admin/user/delete/<int:user_id>', methods=['DELETE'])
@csrf.exempt
@login_required
@admin_required
def delete_user(user_id):
    current_user_id = session.get("user_id")
    print(f"🧪 Eliminando: user_id={user_id}, current_user_id={current_user_id}")

    success = delete_user_service(user_id, current_user_id)

    if not success:
        print("❌ No puedes eliminarte a ti mismo")
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400

    print("✅ Usuario eliminado correctamente")
    return jsonify({"success": True})



@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = User.query.get(user_id) if user_id else None




from app.services.asset_service import get_all_assets

@auth_bp.route('/admin/assets')
@admin_required
def admin_assets():
    assets = get_all_assets()
    return render_template('admin_assets.html', assets=assets)





from app.services.asset_service import update_asset as update_asset_service

@auth_bp.route('/admin/asset/update/<int:asset_id>', methods=['POST'])
@csrf.exempt
@admin_required
@login_required
def update_asset(asset_id):
    data = request.get_json()
    update_asset_service(asset_id, data)
    return jsonify({"success": True})




from app.services.asset_service import delete_asset as delete_asset_service

@auth_bp.route('/admin/asset/delete/<int:asset_id>', methods=['DELETE'])
@csrf.exempt
@admin_required
@login_required
def delete_asset(asset_id):
    delete_asset_service(asset_id)
    return jsonify({"success": True})




from app.services.auth_service import authenticate_user

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = authenticate_user(form.email.data, form.password.data)
        if user:
            if user.two_factor_enabled:
                session['pending_2fa'] = user.UserID
                return redirect(url_for('auth.verify_2fa_route'))
            session['user_id'] = user.UserID
            flash("✅ Inicio de sesión exitoso", "success")
            return redirect(url_for('auth.dashboard'))
        else:
            flash("❌ Credenciales incorrectas", "danger")
    return render_template("login.html", form=form, login_page=True)


from app.services.auth_service import register_user

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            register_user(form)
            flash("✅ Registro exitoso, ahora puedes iniciar sesión", "success")
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(f"❌ {str(e)}", "danger")
    return render_template("register.html", form=form, login_page=True)



from app.services.dashboard_service import get_dashboard_data

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get("user_id")
    sort_by = request.args.get('sort', 'marketcap')
    page = int(request.args.get('page', 1))
    per_page = 100

    data = get_dashboard_data(user_id, sort_by, page, per_page)

    return render_template(
        'dashboard.html',
        assets=data["assets"],
        total_value=data["total_value"],
        change_24h=data["change_24h"],
        top_asset=data["top_asset"],
        page=data["page"],
        total_pages=data["total_pages"],
        sort_by=data["sort_by"]
    )



from app.services.dashboard_service import get_market_overview

@auth_bp.route('/market/overview-data')
def market_overview_data():
    data = get_market_overview()
    return jsonify(data)


from app.services.dashboard_service import get_market_history

@auth_bp.route('/market/history')
def market_history():
    data = get_market_history()
    return jsonify(data)






@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("👋 Sesión cerrada", "info")
    return redirect(url_for('auth.login'))

from flask import render_template, session, redirect, url_for, flash
from app.forms import EditProfileForm, Disable2FAForm
from app.services import profile_service


@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = profile_service.get_user_by_id(session['user_id'])
    form = EditProfileForm()
    disable_2fa_form = Disable2FAForm()

    form.avatar.choices = profile_service.get_avatar_choices()

    if form.validate_on_submit():
        profile_service.update_user_from_form(user, form)
        flash("✅ Perfil actualizado", "success")
        return redirect(url_for('auth.dashboard'))
    elif session.get('user_id') and not form.errors:
        profile_service.populate_form_with_user_data(form, user)

    return render_template(
        'profile.html',
        form=form,
        user=user,
        disable_2fa_form=disable_2fa_form
    )
from app.services.dashboard_service import generate_dashboard_csv

@auth_bp.route('/dashboard/export')
def export_dashboard_csv():
    return generate_dashboard_csv()

from app.services.asset_detail_service import get_asset_detail

from app.services.asset_detail_service import get_asset_detail

@auth_bp.route('/asset/<string:id_coin>')
def asset_detail(id_coin):
    context = get_asset_detail(id_coin)
    return render_template("asset_detail.html", **context)


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

    asset = search_asset_by_query(query)
    if asset:
        return redirect(url_for('auth.asset_detail', id_coin=asset.id_coin))

    flash("Activo no encontrado.", "danger")
    return redirect(url_for('auth.dashboard'))


from app.services.search_service import search_asset_by_query, get_search_suggestions

@auth_bp.route('/search/suggestions')
def search_suggestions():
    query = request.args.get('q', '').strip().lower()

    if not query or len(query) < 2:
        return jsonify([])

    suggestions = get_search_suggestions(query)

    return jsonify([
        {
            "name": asset.Name,
            "symbol": asset.Symbol,
            "id_coin": asset.id_coin
        } for asset in suggestions
    ])




from app.services.biometric_service import generate_registration
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url

@auth_bp.route("/biometric/start-registration", methods=["POST"])
@login_required
def start_biometric_registration():
    user = User.query.get(session["user_id"])
    options = generate_registration(user)

    # Guarda challenge original (bytes) en sesión
    session["webauthn_challenge"] = options.challenge

    # Convertimos a dict manualmente con los campos necesarios en base64url
    options_json = {
        "rp": {
            "name": options.rp.name,
            "id": options.rp.id
        },
        "user": {
            "id": bytes_to_base64url(options.user.id),
            "name": options.user.name,
            "displayName": options.user.display_name
        },
        "challenge": bytes_to_base64url(options.challenge),
        "pubKeyCredParams": [param.__dict__ for param in options.pub_key_cred_params],
        "authenticatorSelection": options.authenticator_selection.__dict__,
        "timeout": options.timeout,
        "attestation": options.attestation,
    }

    return jsonify(options_json)


from app.services.biometric_service import verify_registration_response_service

@auth_bp.route("/biometric/finish-registration", methods=["POST"])
@login_required
def finish_biometric_registration():
    user = User.query.get(session["user_id"])
    data = request.get_json()
    expected_challenge = session.get("webauthn_challenge")

    try:
        verify_registration_response_service(user, data, expected_challenge)
        db.session.commit()
        return jsonify({"success": True, "message": "Biometría registrada correctamente"})
    except Exception as e:
        db.session.rollback()
        print(f"❌ WebAuthn registration error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400





from flask import Blueprint, request, jsonify, session
from app.models import User
from app.services.biometric_service import generate_authentication
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url


@auth_bp.route("/biometric/start-authentication", methods=["POST"])
def start_biometric_authentication():
    email = request.json.get("email")
    user = User.query.filter_by(Email=email).first()

    if not user or not user.BiometricCredentialID:
        return jsonify({"error": "Usuario no válido o sin biometría registrada"}), 400

    options = generate_authentication(user)
    session["webauthn_challenge"] = options.challenge
    session["webauthn_user_id"] = user.UserID  # guardamos temporalmente

    options_json = {
        "challenge": bytes_to_base64url(options.challenge),
        "allowCredentials": [
            {
                "type": "public-key",
                "id": bytes_to_base64url(cred.id),
                "transports": cred.transports or []
            } for cred in options.allow_credentials
        ],
        "timeout": options.timeout,
        "rpId": options.rp_id,
        "userVerification": options.user_verification,
    }

    return jsonify(options_json)


from app.services.biometric_service import verify_authentication_response_service

@auth_bp.route("/biometric/finish-authentication", methods=["POST"])
def finish_biometric_authentication():
    user_id = session.get("webauthn_user_id")
    expected_challenge = session.get("webauthn_challenge")

    if not user_id or not expected_challenge:
        return jsonify({"error": "Sesión inválida"}), 400

    user = User.query.get(user_id)
    data = request.get_json()

    try:
        verify_authentication_response_service(user, data, expected_challenge)
        session.pop("webauthn_user_id", None)
        session.pop("webauthn_challenge", None)
        session["user_id"] = user.UserID  # ¡Usuario autenticado!
        return jsonify({"success": True, "message": "Autenticación biométrica exitosa"})
    except Exception as e:
        print(f"❌ Error de autenticación biométrica: {e}")
        return jsonify({"success": False, "error": str(e)}), 400



from app.services.versus_service import (
    get_all_assets_for_versus,
    get_asset_by_symbol,
    get_price_history
)

@auth_bp.route('/versus')
def versus():
    return render_template('versus.html')


@auth_bp.route('/versus/assets')
def get_asset_list():
    assets = get_all_assets_for_versus()
    return jsonify({
        "assets": [{"Symbol": s, "Name": n, "LogoURL": l} for s, n, l in assets]
    })


@auth_bp.route('/versus/data')
def get_asset_data():
    symbol = request.args.get('symbol')

    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400

    asset = get_asset_by_symbol(symbol)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    data = get_price_history(asset.AssetID)

    return jsonify({
        "label": asset.Name,
        "symbol": asset.Symbol,
        "logo_url": asset.LogoURL,
        "data": data
    })

from app.services.portfolio_service import (
    get_user_portfolio, calculate_portfolio_summary, add_asset_to_portfolio,
    delete_asset_from_portfolio, get_portfolio_asset_list, get_asset_latest_price
)

@auth_bp.route('/portfolio')
@login_required
def portfolio():
    user_id = session['user_id']
    entries = get_user_portfolio(user_id)
    total_value, gain_loss_pct = calculate_portfolio_summary(entries)
    return render_template('portfolio.html',
        portfolio=entries,
        total_value=total_value,
        gain_loss_pct=gain_loss_pct
    )



@auth_bp.route('/portfolio/add', methods=['POST'])
@csrf.exempt
@login_required
def add_to_portfolio():
    data = request.get_json()
    user_id = session.get('user_id')

    try:
        quantity = Decimal(str(data['quantity']))
        purchase_usd = Decimal(str(data['purchase_usd']))
    except Exception:
        return jsonify({"error": "Formato inválido"}), 400

    success, error = add_asset_to_portfolio(user_id, data['symbol'], quantity, purchase_usd)
    if not success:
        return jsonify({"error": error}), 400

    return jsonify({"success": True})



@auth_bp.route('/portfolio/assets')
@login_required
def get_portfolio_assets():
    assets = get_portfolio_asset_list()
    return jsonify([
        {"symbol": s, "name": n} for s, n in assets
    ])


@auth_bp.route('/portfolio/price/<symbol>')
@login_required
def get_latest_price(symbol):
    price = get_asset_latest_price(symbol)
    if price is None:
        return jsonify({"error": "Activo no encontrado o sin precio"}), 404
    return jsonify({"price": price})


@auth_bp.route('/portfolio/delete', methods=['POST'])
@csrf.exempt
@login_required
def delete_from_portfolio():
    data = request.get_json()
    user_id = session['user_id']
    symbol = data.get("symbol")

    success = delete_asset_from_portfolio(user_id, symbol)
    if not success:
        return jsonify({"error": "Activo no encontrado"}), 404

    return jsonify({"success": True})

from app.services.holder_service import (
    get_assets_with_holders, get_all_holder_categories,
    get_holders_data, get_holders_summary
)

@auth_bp.route('/holders')
def holders_view():
    assets = get_assets_with_holders()
    categories = get_all_holder_categories()
    return render_template("holders.html", assets=assets, categories=categories)

@auth_bp.route('/holders/data')
def holders_data():
    return jsonify(get_holders_data())


# --- NUEVA RUTA EN FLASK (routes.py o donde tengas las views) ---
# Nueva ruta en auth_bp/routes.py o similar
from flask import request, jsonify
from sqlalchemy import func, desc
from app.models import Holder, Asset, HolderCategory

@auth_bp.route('/holders/summary')
def holders_summary():
    symbol = request.args.get("symbol")
    category = request.args.get("category")
    summary = get_holders_summary(symbol, category)
    return jsonify(summary)

from app.services.auth_service import generate_2fa_qr

@auth_bp.route('/2fa/setup')
@login_required
def setup_2fa():
    user = User.query.get(session['user_id'])
    form = TwoFactorForm()
    qr_b64, _ = generate_2fa_qr(user)
    return render_template("2fa_setup.html", qr_code=qr_b64, form=form)


from app.services.auth_service import verify_2fa, enable_2fa

@auth_bp.route('/2fa/confirm', methods=['POST'])
@login_required
def confirm_2fa():
    form = TwoFactorForm()
    user = User.query.get(session['user_id'])

    if form.validate_on_submit():
        if verify_2fa(user, form.otp_code.data):
            enable_2fa(user)
            flash("✅ 2FA activado correctamente", "success")
            return redirect(url_for('auth.profile'))
        else:
            flash("❌ Código incorrecto", "danger")
            return redirect(url_for('auth.setup_2fa'))

    flash("❌ Error en el formulario", "danger")
    return redirect(url_for('auth.setup_2fa'))


from app.services.auth_service import disable_2fa as disable_2fa_service
from app.forms import Disable2FAForm

@auth_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa_route():
    form = Disable2FAForm()
    if form.validate_on_submit():
        disable_2fa_service(g.user)
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




from app.services.auth_service import verify_2fa

@auth_bp.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa_route():
    if 'pending_2fa' not in session:
        flash("Sesión inválida", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['pending_2fa'])
    form = TwoFactorForm()

    if form.validate_on_submit():
        if verify_2fa(user, form.otp_code.data):
            session['user_id'] = user.UserID
            session.pop('pending_2fa', None)
            flash("✅ 2FA verificado correctamente", "success")
            return redirect(url_for('auth.dashboard'))
        else:
            flash("❌ Código incorrecto", "danger")

    return render_template("2fa_verify.html", form=form)


from app.services.auth_service import request_password_reset
from scripts.send_email import send_reset_email

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(Email=form.email.data).first()
        if user:
            token = request_password_reset(user)
            send_reset_email(user, token)  # ✅ ahora le pasas el token ya generado

        flash("📧 Se ha enviado un enlace de recuperación a tu correo si existe en el sistema.", "info")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html", form=form, login_page=True)





from app.services.auth_service import verify_reset_token, update_password

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = verify_reset_token(token)
    if not user:
        flash("❌ Enlace inválido o expirado", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        update_password(user, form.password.data)
        flash("✅ Contraseña actualizada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", form=form, login_page=True)

