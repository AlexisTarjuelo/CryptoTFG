import pyotp
import qrcode
import io
import base64
from app import db
from app.models import User


def authenticate_user(email, password):
    """Verifica las credenciales del usuario."""
    user = User.query.filter_by(Email=email).first()
    if user and user.check_password(password):
        return user
    return None


def register_user(form):
    """Registra un nuevo usuario a partir de un formulario WTForm."""
    existing = User.query.filter_by(Email=form.email.data).first()
    if existing:
        raise ValueError("Este correo ya está registrado.")

    user = User(
        FirstName=form.first_name.data,
        LastName=f"{form.last_name.data} {form.second_last_name.data}",
        Email=form.email.data,
        Phone=form.phone.data,
        IsAdult=form.is_adult.data,
        AcceptedTerms=form.accept_terms.data
    )
    user.set_password(form.password.data)
    db.session.add(user)
    db.session.commit()
    return user


def generate_2fa_qr(user):
    """Genera un código QR para configurar 2FA."""
    if not user.two_factor_secret:
        user.generate_two_factor_secret()
        db.session.commit()

    otp_uri = user.get_otp_uri()
    qr_img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return qr_b64, otp_uri


def verify_2fa(user, code):
    """Verifica el código OTP ingresado por el usuario."""
    if not user.two_factor_secret:
        return False
    totp = pyotp.TOTP(user.two_factor_secret)
    return totp.verify(code)


def enable_2fa(user):
    user.enable_2fa()


def disable_2fa(user):
    user.two_factor_secret = None
    user.two_factor_enabled = False
    db.session.commit()



def reset_password(user, new_password):
    user.set_password(new_password)
    user.reset_security()
    db.session.commit()

def request_password_reset(user):
    """Retorna el token de reseteo de contraseña."""
    return user.get_reset_token()

def verify_reset_token(token):
    """Devuelve el usuario si el token es válido, o None si no lo es."""
    return User.verify_reset_token(token)

def update_password(user, new_password):
    """Actualiza la contraseña y resetea seguridad."""
    user.set_password(new_password)
    user.reset_security()
    db.session.commit()

