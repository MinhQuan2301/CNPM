import hashlib
from sre_constants import error

from django.conf import settings
from django.shortcuts import render
from flask import Blueprint, request, flash, render_template, redirect, url_for
from flask_security.cli import roles
from wtforms.validators import email

from app import dao, db
from app.models import User, Role

user_register = Blueprint("user_register", __name__)

@user_register.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'POST':
        fullname = request.form.get("fullname")
        email = request.form.get('email')
        phone_number = request.form.get('phone-number')
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm-password")

        if not fullname or not email or not phone_number or not username or not password or not  confirm_password:
            return render_template('register.html',error_fullname="Phải nhập đầy đủ thông tin")

        if not User.is_email_valid(email):
            flash("Địa chỉ email không hợp lệ.", "danger")
            return render_template('register.html',  error_email="Địa chỉ email không hợp lệ")
        if password != confirm_password:
            return render_template('register.html', error_password="Mật khẩu xác nhận không khớp")
        existing_user = dao.get_user(username=username)
        existing_email = dao.get_user(email=email)
        if existing_user:
            return render_template('register.html', error_username='Tên đăng nhập đã tồn tại')
        if existing_email:
            return render_template('register.html', error_email='Email đã tồn tại')

        hashed_password = str(hashlib.md5(password.encode('utf-8')).hexdigest())
        user_role = dao.get_role("User")
        new_user = User(fullname=fullname,
                        phone_number=phone_number,
                        username = username,
                        password=hashed_password,
                        email=email,
                        roles=[user_role])

        db.session.add(new_user)
        db.session.commit()

        flash("Đăng ký thành công.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')



