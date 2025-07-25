# scripts/send_email.py

from flask_mail import Message
from flask import url_for, current_app, render_template_string
from datetime import datetime
from app import mail

def send_reset_email(user, token):
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    reset_url = url_for('auth.reset_password', token=token, _external=True)

    # 🌱 Texto plano para clientes que no renderizan HTML
    plain_text = f"""
Hola {user.FirstName},

Has solicitado restablecer tu contraseña.

Haz clic o copia el siguiente enlace en tu navegador:
{reset_url}

Este enlace expirará en 15 minutos. Si no hiciste esta solicitud, simplemente ignora este correo.

CryptoTFG
"""

    # 🎨 HTML mejorado
    html_body = render_template_string("""
    <div style="font-family: Poppins, sans-serif; background-color: #0A0E17; padding: 2rem; color: #ffffff;">
      <div style="max-width: 600px; margin: auto; background-color: #101823; border: 1px solid #3EC894; border-radius: 12px; padding: 2rem;">
        <div style="text-align: center;">
          <img src="https://cryptotfg.com/static/images/logo_cryptotfg.png" alt="Logo CryptoTFG" style="width: 120px; margin-bottom: 1rem;">
          <h2 style="color: #6EF1B3;">Recuperación de contraseña</h2>
        </div>
        <p>Hola {{ user.FirstName }},</p>
        <p>Hemos recibido una solicitud para restablecer tu contraseña. Haz clic en el siguiente botón para continuar:</p>
        <div style="text-align: center; margin: 2rem 0;">
          <a href="{{ reset_url }}" style="background-color: #6EF1B3; color: #0A0E17; padding: 0.8rem 1.5rem; border-radius: 8px; text-decoration: none; font-weight: bold;">
            Restablecer contraseña
          </a>
        </div>
        <p>Este enlace expirará en 15 minutos. Si no solicitaste esta acción, puedes ignorar este mensaje.</p>
        <p style="margin-top: 2rem;">— El equipo de <strong>CryptoTFG</strong></p>
      </div>
      <p style="text-align: center; font-size: 0.8rem; color: #999999; margin-top: 1rem;">
        © {{ current_year }} CryptoTFG. Todos los derechos reservados.
      </p>
    </div>
    """, user=user, reset_url=reset_url, current_year=datetime.now().year)

    msg = Message(
        subject="🔐 Recupera tu contraseña - CryptoTFG",
        recipients=[user.Email],
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        body=plain_text,
        html=html_body
    )

    mail.send(msg)
