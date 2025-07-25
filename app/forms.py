from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.fields.choices import SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, InputRequired

# Validación personalizada de contraseña segura
password_requirements = Regexp(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\W).{8,}$',
    message='La contraseña debe tener al menos 8 caracteres, incluyendo mayúsculas, minúsculas y un carácter especial.'
)

class LoginForm(FlaskForm):
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar sesión')


class RegisterForm(FlaskForm):
    first_name = StringField('Nombre', validators=[DataRequired(message='El nombre es obligatorio.')])
    last_name = StringField('Primer Apellido', validators=[DataRequired(message='El primer apellido es obligatorio.')])
    second_last_name = StringField('Segundo Apellido',
                                   validators=[DataRequired(message='El segundo apellido es obligatorio.')])

    email = StringField('Correo', validators=[
        DataRequired(message='El correo es obligatorio.'),
        Email(message='Debes ingresar un correo válido.')
    ])

    phone = StringField('Teléfono', validators=[DataRequired(message='El teléfono es obligatorio.')])

    is_adult = BooleanField('¿Eres mayor de edad?', validators=[
        InputRequired(message='Debes confirmar que eres mayor de edad.')
    ])

    password = PasswordField('Contraseña', validators=[
        DataRequired(message='La contraseña es obligatoria.'),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        password_requirements  # Asume que esta es tu validación personalizada
    ])

    confirm_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(message='Debes confirmar la contraseña.'),
        EqualTo('password', message='Las contraseñas no coinciden.')
    ])

    accept_terms = BooleanField('Aceptar términos', validators=[
        InputRequired(message='Debes aceptar los términos y condiciones.')
    ])

    submit = SubmitField('Registrarse')


class EditProfileForm(FlaskForm):
    first_name = StringField('Nombre', validators=[DataRequired(), Length(min=2)])
    last_name = StringField('Primer Apellido', validators=[DataRequired(), Length(min=2)])
    second_last_name = StringField('Segundo Apellido', validators=[DataRequired(), Length(min=2)])
    phone = StringField('Teléfono', validators=[
        DataRequired(),
        Regexp(r'^[0-9]{7,15}$', message='Introduce un número de teléfono válido')
    ])
    password = PasswordField('Nueva contraseña', validators=[
        Optional(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        password_requirements
    ])
    confirm_password = PasswordField('Confirmar contraseña', validators=[
        Optional(),
        EqualTo('password', message='Las contraseñas no coinciden')
    ])
    avatar = SelectField('Avatar', choices=[])
    submit = SubmitField('Guardar cambios')


class TwoFactorForm(FlaskForm):
    otp_code = StringField('Código 2FA', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verificar')


class Disable2FAForm(FlaskForm):
    submit = SubmitField('❌ Desactivar 2FA')


class RequestResetForm(FlaskForm):
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar enlace de recuperación')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        password_requirements
    ])
    confirm_password = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Restablecer contraseña')
