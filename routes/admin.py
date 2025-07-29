from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import User, db
from utils import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@admin_required
def before_request():
    """在處理此藍圖中的任何請求之前，確保使用者是已登入的管理員。"""
    pass

@admin_bp.route('/users')
def user_list():
    users = User.query.all()
    return render_template('user_management.html', users=users)

@admin_bp.route('/users/create', methods=['POST'])
def create_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    if not all([username, password, role]):
        flash('所有欄位都是必填的！', 'danger')
        return redirect(url_for('admin.user_list'))

    if User.query.filter_by(username=username).first():
        flash('該使用者名稱已存在！', 'danger')
        return redirect(url_for('admin.user_list'))

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(new_user)
    db.session.commit()
    flash('新使用者已成功建立！', 'success')
    return redirect(url_for('admin.user_list'))

@admin_bp.route('/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    new_password = request.form.get('password')

    if new_role:
        # 防止 admin 修改自己的角色，導致失去管理權限
        if user.id == current_user.id and user.role == 'admin' and new_role != 'admin':
            flash('無法變更自己的管理員角色！', 'danger')
            return redirect(url_for('admin.user_list'))
        user.role = new_role
    
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    db.session.commit()
    flash(f"使用者 '{user.username}' 的資料已更新。", 'success')
    return redirect(url_for('admin.user_list'))

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    # 避免 admin 刪除自己
    if user_id == current_user.id:
        flash('無法刪除自己的帳號！', 'danger')
        return redirect(url_for('admin.user_list'))
        
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"使用者 '{user.username}' 已被刪除。", 'success')
    return redirect(url_for('admin.user_list'))
