from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('viewer', 'editor', 'admin'), nullable=False)
    last_login = db.Column(db.DateTime)

class TempSpec(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spec_code = db.Column(db.String(20), nullable=False)
    applicant = db.Column(db.String(50))
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.Enum('pending_approval', 'active', 'expired', 'terminated'), nullable=False, default='pending_approval')
    created_at = db.Column(db.DateTime)
    extension_count = db.Column(db.Integer, default=0)
    termination_reason = db.Column(db.Text, nullable=True)

    # 關聯到 Upload 和 SpecHistory，並設定級聯刪除
    uploads = db.relationship('Upload', back_populates='spec', cascade='all, delete-orphan')
    history = db.relationship('SpecHistory', back_populates='spec', cascade='all, delete-orphan')

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temp_spec_id = db.Column(db.Integer, db.ForeignKey('temp_spec.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(200))
    upload_time = db.Column(db.DateTime)
    
    spec = db.relationship('TempSpec', back_populates='uploads')

class SpecHistory(db.Model):
    __tablename__ = 'SpecHistory'
    id = db.Column(db.Integer, primary_key=True)
    spec_id = db.Column(db.Integer, db.ForeignKey('temp_spec.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立與 User 和 TempSpec 的關聯，方便查詢
    user = db.relationship('User')
    spec = db.relationship('TempSpec', back_populates='history')
