import os
import tempfile
from app import db
from app.models import User
from app.forms import EditProfileForm
from app.services import profile_service


def create_test_user():
    user = User(
        FirstName='Juan',
        LastName='Pérez López',
        Email='juan@example.com',
        Phone='1234567890',
        IsAdult=True,
        AcceptedTerms=True,
        Avatar='dino1.png'
    )
    user.set_password('Clave$123')
    db.session.add(user)
    db.session.commit()
    return user


def test_get_user_by_id(app):
    with app.app_context():
        user = create_test_user()
        fetched = profile_service.get_user_by_id(user.UserID)
        assert fetched is not None
        assert fetched.Email == user.Email


def test_populate_form_with_user_data(app):
    with app.app_context():
        user = create_test_user()
        form = EditProfileForm()

        profile_service.populate_form_with_user_data(form, user)

        assert form.first_name.data == 'Juan'
        assert form.phone.data == '1234567890'
        assert form.avatar.data == 'dino1.png'
        assert form.last_name.data == 'Pérez'
        assert form.second_last_name.data == 'López'


def test_update_user_from_form(app):
    with app.app_context():
        user = create_test_user()
        form = EditProfileForm(data={
            'first_name': 'Carlos',
            'last_name': 'Ramírez',
            'second_last_name': 'Díaz',
            'phone': '9876543210',
            'avatar': 'dino2.png',
            'password': 'NuevaClave$123',
            'confirm_password': 'NuevaClave$123'
        })

        profile_service.update_user_from_form(user, form)
        updated = User.query.get(user.UserID)

        assert updated.FirstName == 'Carlos'
        assert updated.LastName == 'Ramírez Díaz'
        assert updated.Phone == '9876543210'
        assert updated.Avatar == 'dino2.png'
        assert updated.check_password('NuevaClave$123')



