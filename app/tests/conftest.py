import pytest
from config import TestingConfig
from app import create_app, db
from app.models import User

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_login(client, app):
    with app.app_context():
        admin = User(
            FirstName='Admin',
            LastName='Test',
            Email='admin@example.com',
            Phone='000000000',
            IsAdult=True,
            AcceptedTerms=True,
            Role='admin'
        )
        admin.set_password('Admin$123')
        db.session.add(admin)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = admin.UserID

    return admin
