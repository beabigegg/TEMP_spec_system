from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models import User, db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user:
            print(f"🔍 嘗試登入使用者：{username}")
        else:
            print("⚠️ 使用者不存在")

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.now()
            db.session.commit()
            print("✅ 登入成功")
            return redirect(url_for('temp_spec.spec_list'))
        else:
            print("❌ 登入失敗，帳號或密碼錯誤")
            flash('帳號或密碼錯誤，請重新輸入', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
