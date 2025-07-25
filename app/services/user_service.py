# app/services/user_service.py

from app import db
from app.models import User

def get_all_users():
    return User.query.all()

def get_user_by_id(user_id):
    return User.query.get_or_404(user_id)

def update_user(user_id, data):
    user = get_user_by_id(user_id)

    user.FirstName = data.get('first_name', user.FirstName)
    user.LastName = data.get('last_name', user.LastName)
    user.Email = data.get('email', user.Email)
    user.Phone = data.get('phone', user.Phone)

    new_role = data.get('role', user.Role)
    if new_role in ['admin', 'user']:
        user.Role = new_role

    db.session.commit()
    return user

def delete_user(user_id, current_user_id):
    if user_id == current_user_id:
        return False
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return True


def admin_update_user(user_id, data):
    user = get_user_by_id(user_id)

    user.FirstName = data.get("first_name", user.FirstName)
    user.LastName = data.get("last_name", user.LastName)
    user.Email = data.get("email", user.Email)
    user.Phone = data.get("phone", user.Phone)
    user.Role = data.get("role", user.Role)

    db.session.commit()
    return user