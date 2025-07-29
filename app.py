from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, current_user
from models import db, User
from routes.auth import auth_bp
from routes.temp_spec import temp_spec_bp
from routes.upload import upload_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object('config.Config')

# 初始化資料庫
db.init_app(app)

# 初始化登入管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "請先登入以存取此頁面。"
login_manager.login_message_category = "info"

# 預設首頁導向登入畫面
@app.route('/')
def index():
    return redirect(url_for('auth.login'))

# 載入登入使用者
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 註冊 Blueprint 模組路由
app.register_blueprint(auth_bp)
app.register_blueprint(temp_spec_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(admin_bp)

# 註冊錯誤處理函式
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

if __name__ == '__main__':
    app.run(debug=True)
