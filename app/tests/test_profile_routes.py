import pytest
from flask import session
from app.models import User
from app import db

@pytest.fixture
def create_user_and_login(client, app):
    def _create_user():
        with app.app_context():
            user = User(
                FirstName='Carlos',
                LastName='Sánchez Pérez',
                Email='carlos@example.com',
                Phone='123456789',
                IsAdult=True,
                AcceptedTerms=True
            )
            user.set_password('Segura$123')
            db.session.add(user)
            db.session.commit()

            with client.session_transaction() as sess:
                sess['user_id'] = user.UserID

            return user
    return _create_user

def test_profile_page_loads(client, app, create_user_and_login):
    create_user_and_login()
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Perfil' in response.data

def test_edit_profile_update_success(client, app, create_user_and_login):
    user = create_user_and_login()

    data = {
        'first_name': 'Carlos',
        'last_name': 'Sánchez',
        'second_last_name': 'Pérez',
        'phone': '987654321',
        'password': 'Nueva$1234',
        'confirm_password': 'Nueva$1234',
        'avatar': 'dino1.png',
        'submit': True
    }

    response = client.post('/profile', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Perfil actualizado' in response.data

    updated_user = db.session.get(User, user.UserID)
    assert updated_user.Phone == '987654321'
    assert updated_user.check_password('Nueva$1234') is True
    assert updated_user.Avatar == 'dino1.png'

def test_edit_profile_requires_login(client):
    response = client.get('/profile', follow_redirects=True)
    assert b'Iniciar sesi' in response.data or b'Login' in response.data
