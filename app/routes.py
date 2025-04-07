from flask import render_template, redirect, url_for, flash, session, request, Blueprint
from werkzeug.security import check_password_hash

from app import db
from app.models import User
from app.forms import LoginForm, RegisterForm

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
            return redirect(url_for('dashboard'))  # o cambia esto a la vista inicial
        flash("❌ Credenciales incorrectas", "danger")
    return render_template("login.html", form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(Email=form.email.data).first()
        if existing:
            flash("❌ Este correo ya está registrado", "danger")
            return redirect(url_for('register'))

        new_user = User(
            FirstName=form.first_name.data,
            LastName=form.last_name.data + ' ' + form.second_last_name.data,
            Email=form.email.data,
            Phone=form.phone.data,
            IsAdult=form.is_adult.data,
            AcceptedTerms=form.accept_terms.data
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Registro exitoso", "success")
        return redirect(url_for('login'))
    return render_template("register.html", form=form)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("👋 Sesión cerrada", "info")
    return redirect(url_for('login'))


