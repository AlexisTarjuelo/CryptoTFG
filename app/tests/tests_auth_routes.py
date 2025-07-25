from app import db
from app.models import User


# 🔧 Función auxiliar para crear usuarios en las pruebas
def create_user(email="test@example.com", password="Secure$123", two_factor=False):
    user = User(
        FirstName='Test',
        LastName='User',
        SecondLastName='Example',
        Email=email,
        Phone='1234567890',
        is_adult=True,
        two_factor_enabled=two_factor
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


# 🧪 PRUEBAS DE REGISTRO
def test_register_page_loads(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Registrarse' in response.data

def test_successful_registration(client):
    response = client.post('/register', data={
        'first_name': 'Ana',
        'last_name': 'Gomez',
        'second_last_name': 'Lopez',
        'email': 'ana@example.com',
        'phone': '1234567890',
        'is_adult': True,
        'password': 'Segura$123',
        'confirm_password': 'Segura$123',
        'accept_terms': True
    }, follow_redirects=True)

    assert b'Registro exitoso' in response.data
    assert User.query.filter_by(Email='ana@example.com').first() is not None

def test_duplicate_email(client):
    client.post('/register', data={
        'first_name': 'Luis',
        'last_name': 'Perez',
        'second_last_name': 'Mendez',
        'email': 'luis@example.com',
        'phone': '1234567890',
        'is_adult': True,
        'password': 'Segura$123',
        'confirm_password': 'Segura$123',
        'accept_terms': True
    })

    response = client.post('/register', data={
        'first_name': 'Luis',
        'last_name': 'Perez',
        'second_last_name': 'Mendez',
        'email': 'luis@example.com',
        'phone': '1234567890',
        'is_adult': True,
        'password': 'Segura$123',
        'confirm_password': 'Segura$123',
        'accept_terms': True
    }, follow_redirects=True)

    assert b'correo ya est' in response.data.lower()


# 🧪 PRUEBAS DE LOGIN
def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Iniciar sesi' in response.data

def test_login_valid_credentials(client, app):
    with app.app_context():
        create_user(email="login@example.com", password="Secure$123")

    response = client.post('/login', data={
        'email': 'login@example.com',
        'password': 'Secure$123'
    }, follow_redirects=True)

    assert b'Inicio de sesi' in response.data
    assert b'dashboard' in response.data or response.status_code == 200

def test_login_invalid_credentials(client):
    response = client.post('/login', data={
        'email': 'noexiste@example.com',
        'password': 'incorrecta'
    }, follow_redirects=True)

    assert b'Credenciales incorrectas' in response.data

def test_login_user_with_2fa_sets_pending_session(client, app):
    with app.app_context():
        user = create_user(email="2fa@example.com", password="Secure$123", two_factor=True)

    # Aseguramos que la sesión esté limpia
    with client.session_transaction() as sess:
        sess.clear()

    response = client.post('/login', data={
        'email': '2fa@example.com',
        'password': 'Secure$123'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/verify-2fa' in response.headers['Location']

    # Verificamos que se haya guardado 'pending_2fa' en la sesión
    with client.session_transaction() as sess:
        assert sess.get('pending_2fa') == user.UserID
