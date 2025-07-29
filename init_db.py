# -*- coding: utf-8 -*-
import os
import secrets
import string
from flask import Flask
from werkzeug.security import generate_password_hash
from models import db, User
from config import Config

def create_default_admin(app):
    """在應用程式上下文中建立一個預設的管理員帳號。"""
    with app.app_context():
        # 檢查管理員是否已存在
        if User.query.filter_by(username='admin').first():
            print("ℹ️  'admin' 使用者已存在，跳過建立程序。")
            return

        # 產生一個安全隨機的密碼
        password_length = 12
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*()'
        password = ''.join(secrets.choice(alphabet) for i in range(password_length))
        
        # 建立新使用者
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash(password),
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        
        print("✅ 預設管理員帳號已建立！")
        print("   ===================================")
        print(f"   👤 使用者名稱: admin")
        print(f"   🔑 密碼: {password}")
        print("   ===================================")
        print("   請妥善保管此密碼，並在首次登入後考慮變更。")

def init_database(app):
    """初始化資料庫：刪除所有現有資料表並重新建立。"""
    with app.app_context():
        print("🔄 開始進行資料庫初始化...")
        # 為了安全，先刪除所有表格，再重新建立
        db.drop_all()
        print("   - 所有舊資料表已刪除。")
        db.create_all()
        print("   - 所有新資料表已根據 models.py 建立。")
        print("✅ 資料庫結構已成功初始化！")

if __name__ == '__main__':
    # 建立一個暫時的 Flask app 來提供資料庫操作所需的應用程式上下文
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 將資料庫物件與 app 綁定
    db.init_app(app)

    print("=================================================")
    print("          ⚠️  資料庫初始化腳本  ⚠️")
    print("=================================================")
    print("此腳本將會刪除所有現有的資料，並重新建立資料庫結構。")
    print("這個操作是不可逆的！")
    
    # 讓使用者確認操作
    confirmation = input("👉 您確定要繼續嗎？ (yes/no): ")

    if confirmation.lower() == 'yes':
        init_database(app)
        create_default_admin(app)
        print("\n🎉 全部完成！")
    else:
        print("❌ 操作已取消。")