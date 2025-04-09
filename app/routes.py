# routes.py
import os
from decimal import Decimal

from flask import render_template, redirect, url_for, flash, session, request, Blueprint, current_app, Response, \
    make_response
from sqlalchemy import func
from werkzeug.security import check_password_hash

from app import db
from app.models import User, Asset, AssetPrice
from app.forms import LoginForm, RegisterForm, EditProfileForm

auth_bp = Blueprint('auth', __name__, template_folder='templates')


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
    return render_template("login.html", form=form)


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
    return render_template("register.html", form=form)


from flask import render_template, request, redirect, url_for, session
from sqlalchemy import func
from decimal import Decimal
from app import db
from app.models import Asset, AssetPrice

@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Parámetros de orden y página
    sort_by = request.args.get('sort', 'marketcap')
    page = int(request.args.get('page', 1))
    per_page = 100

    # Subconsulta: última fecha por AssetID
    subquery = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('max_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

    # Consulta principal usando with_entities
    query = (
        db.session.query(
            Asset.AssetID,       # p[0]
            Asset.Name,          # p[1]
            Asset.Symbol,        # p[2]
            Asset.LogoURL,       # p[3]
            AssetPrice.PriceUSD, # p[4]
            AssetPrice.MarketCap,# p[5]
            AssetPrice.TotalVolume # p[6]
        )
        .join(AssetPrice, Asset.AssetID == AssetPrice.AssetID)
        .join(subquery, (AssetPrice.AssetID == subquery.c.AssetID) & (AssetPrice.RecordedAt == subquery.c.max_date))
    )

    # Orden dinámico
    if sort_by == 'price':
        query = query.order_by(AssetPrice.PriceUSD.desc())
    elif sort_by == 'volume':
        query = query.order_by(AssetPrice.TotalVolume.desc())
    else:
        query = query.order_by(AssetPrice.MarketCap.desc())

    # Paginación
    paginated = query.paginate(page=page, per_page=per_page)

    # Calcular total de precios visibles
    total_value = sum(float(p[4]) if p[4] else 0 for p in paginated.items)

    # Activo con mayor MarketCap
    top_asset = max(paginated.items, key=lambda x: x[5] if x[5] else Decimal(0)) if paginated.items else None

    # Cambio simulado por ahora
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

    # Cargar avatares dinámicamente
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
