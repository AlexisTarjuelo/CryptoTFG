from app.forms import RegisterForm, LoginForm




def test_register_form_invalid_password(app):
    form = RegisterForm(data={
        'first_name': 'Ana',
        'last_name': 'López',
        'second_last_name': 'Mendez',
        'email': 'ana@example.com',
        'phone': '1234567890',
        'is_adult': True,
        'password': 'simple',  # No cumple con los requisitos
        'confirm_password': 'simple',
        'accept_terms': True
    })
    assert not form.validate()
    assert any("debe tener al menos" in e.lower() or "requisitos" in e.lower() for e in form.password.errors)


def test_register_form_password_mismatch(app):
    form = RegisterForm(data={
        'first_name': 'Sara',
        'last_name': 'Diaz',
        'second_last_name': 'Ramos',
        'email': 'sara@example.com',
        'phone': '1234567890',
        'is_adult': True,
        'password': 'Segura$123',
        'confirm_password': 'OtraClave$123',
        'accept_terms': True
    })
    assert not form.validate()
    assert 'Las contraseñas no coinciden.' in form.confirm_password.errors


def test_register_form_missing_terms(app):
    form = RegisterForm(data={
        'first_name': 'Luis',
        'last_name': 'Martínez',
        'second_last_name': 'Suárez',
        'email': 'luis@example.com',
        'phone': '1234567890',
        'is_adult': True,
        'password': 'Segura$123',
        'confirm_password': 'Segura$123',
        'accept_terms': False  # No aceptó términos
    })
    assert not form.validate()
    assert 'Debes aceptar los términos y condiciones.' in form.accept_terms.errors


def test_login_form_valid(app):
    form = LoginForm(data={
        'email': 'test@example.com',
        'password': 'Cualquier123!'
    })
    assert form.validate()
