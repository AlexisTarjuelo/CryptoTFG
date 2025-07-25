import os
from flask import current_app
from app import db
from app.models import User


def get_user_by_id(user_id):
    return User.query.get(user_id)


def get_avatar_choices():
    avatar_dir = os.path.join(current_app.static_folder, 'images', 'avatars')
    return [(f, f.split('.')[0].capitalize())
            for f in os.listdir(avatar_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]


def populate_form_with_user_data(form, user):
    form.first_name.data = user.FirstName
    form.phone.data = user.Phone
    form.avatar.data = user.Avatar
    form.last_name.data, form.second_last_name.data = (
        user.LastName.split(" ", 1) if " " in user.LastName else (user.LastName, "")
    )


def update_user_from_form(user, form):
    user.FirstName = form.first_name.data
    user.LastName = f"{form.last_name.data} {form.second_last_name.data}"
    user.Phone = form.phone.data
    user.Avatar = form.avatar.data
    if form.password.data:
        user.set_password(form.password.data)
    db.session.commit()
