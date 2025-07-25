import pyotp
from app import db
from app.models import User


def create_user_with_2fa(client, app):
    with app.app_context():
        user = User(
            FirstName='Two',
            LastName='Factor',
            Email='2fa@example.com',
            Phone='111222333',
            IsAdult=True,
            AcceptedTerms=True
        )
        user.set_password('Clave$123')
        user.generate_two_factor_secret()
        db.session.add(user)
        db.session.commit()

        client.post('/login', data={
            'email': '2fa@example.com',
            'password': 'Clave$123'
        }, follow_redirects=True)

        return user


def test_2fa_setup_page_loads(client, app):
    create_user_with_2fa(client, app)
    response = client.get('/2fa/setup')
    assert response.status_code == 200
    assert b'<img' in response.data or b'QR' in response.data


def test_2fa_confirm_valid_code(client, app):
    user = create_user_with_2fa(client, app)
    totp = pyotp.TOTP(user.two_factor_secret)
    valid_code = totp.now()

    response = client.post('/2fa/confirm', data={
        'otp_code': valid_code
    }, follow_redirects=True)

    assert b'2FA activado correctamente' in response.data
    assert User.query.get(user.UserID).two_factor_enabled is True


def test_2fa_confirm_invalid_code(client, app):
    create_user_with_2fa(client, app)

    response = client.post('/2fa/confirm', data={
        'otp_code': '000000'  # código inválido
    }, follow_redirects=True)

    assert b'C' in response.data  # Código incorrecto


def test_2fa_disable(client, app):
    user = create_user_with_2fa(client, app)
    user.enable_2fa()
    db.session.commit()

    response = client.post('/2fa/disable', data={}, follow_redirects=True)
    assert b'2FA desactivado' in response.data

    updated_user = User.query.get(user.UserID)
    assert updated_user.two_factor_enabled is False
    assert updated_user.two_factor_secret is None


def test_2fa_verification_success(client, app):
    with app.app_context():
        user = User(
            FirstName='Pending',
            LastName='2FA',
            Email='pending@example.com',
            Phone='999888777',
            IsAdult=True,
            AcceptedTerms=True
        )
        user.set_password('Clave$123')
        user.generate_two_factor_secret()
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['pending_2fa'] = user.UserID

        totp = pyotp.TOTP(user.two_factor_secret)
        valid_code = totp.now()

        response = client.post('/2fa/verify', data={
            'otp_code': valid_code
        }, follow_redirects=True)

        assert b'2FA verificado correctamente' in response.data
        with client.session_transaction() as sess:
            assert 'pending_2fa' not in sess
            assert sess.get('user_id') == user.UserID


def test_2fa_verification_invalid_code(client, app):
    with app.app_context():
        user = User(
            FirstName='Failing',
            LastName='2FA',
            Email='fail@example.com',
            Phone='123123123',
            IsAdult=True,
            AcceptedTerms=True
        )
        user.set_password('Clave$123')
        user.generate_two_factor_secret()
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['pending_2fa'] = user.UserID

        response = client.post('/2fa/verify', data={
            'otp_code': '000000'
        }, follow_redirects=True)

        assert b'c' in response.data or b'incorrecto' in response.data
