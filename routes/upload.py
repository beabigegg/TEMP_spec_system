from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import time

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/image', methods=['POST'])
def upload_image():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file part'}), 400

    # 建立一個獨特的檔名
    extension = os.path.splitext(file.filename)[1]
    filename = f"{int(time.time())}_{secure_filename(file.filename)}"
    
    # 確保上傳資料夾存在
    # 為了讓圖片能被網頁存取，我們將它存在 static 資料夾下
    image_folder = os.path.join(current_app.static_folder, 'uploads', 'images')
    os.makedirs(image_folder, exist_ok=True)
    
    file_path = os.path.join(image_folder, filename)
    file.save(file_path)

    # 回傳 TinyMCE 需要的 JSON 格式
    # 路徑必須是相對於網域根目錄的 URL
    location = f"/static/uploads/images/{filename}"
    return jsonify({'location': location})
