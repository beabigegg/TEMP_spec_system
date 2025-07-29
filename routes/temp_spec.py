# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import TempSpec, db, Upload, SpecHistory
from utils import fill_template, editor_or_admin_required, add_history_log, admin_required
import os
import tempfile
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
import re
import mistune

temp_spec_bp = Blueprint('temp_spec', __name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@temp_spec_bp.before_request
@login_required
def before_request():
    """在處理此藍圖中的任何請求之前，確保使用者已登入。"""
    pass

def _generate_next_spec_code():
    """
    產生下一個暫時規範編號。
    規則: PE + 民國年(3碼) + 月份(2碼) + 流水號(2碼)
    """
    now = datetime.now()
    roc_year = now.year - 1911
    prefix = f"PE{roc_year}{now.strftime('%m')}"

    latest_spec = TempSpec.query.filter(
        TempSpec.spec_code.startswith(prefix)
    ).order_by(TempSpec.spec_code.desc()).first()

    if latest_spec:
        last_seq = int(latest_spec.spec_code[-2:])
        new_seq = last_seq + 1
    else:
        new_seq = 1
    
    return f"{prefix}{new_seq:02d}"

@temp_spec_bp.route('/preview', methods=['POST'])
def preview_spec():
    """產生預覽 PDF 並返回"""
    data = request.json
    
    values = {
        'serial_number': data.get('serial_number', 'PREVIEW-SN'),
        'theme': data.get('theme', 'PREVIEW-THEME'),
        'applicant': data.get('applicant', ''),
        'applicant_phone': data.get('applicant_phone', ''),
        'station': data.get('station', ''),
        'tccs_info': data.get('tccs_info', ''),
        'start_date': data.get('start_date', datetime.today().strftime('%Y-%m-%d')),
        'end_date': (datetime.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'package': data.get('package', ''),
        'lot_number': data.get('lot_number', ''),
        'equipment_type': data.get('equipment_type', ''),
        'change_before': data.get('change_before', ''),
        'change_after': data.get('change_after', ''),
        'data_needs': data.get('data_needs', ''),
    }

    temp_docx_path = tempfile.mktemp(suffix=".docx")
    temp_pdf_path = tempfile.mktemp(suffix=".pdf")

    try:
        template_path = os.path.join(BASE_DIR, 'template_with_placeholders.docx')
        fill_template(values, template_path, temp_docx_path, temp_pdf_path)

        with open(temp_pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        import io
        return_data = io.BytesIO(pdf_data)

        try:
            if os.path.exists(temp_docx_path):
                os.remove(temp_docx_path)
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        except Exception as e:
            current_app.logger.error(f"無法刪除暫存檔: {e}")

        return send_file(return_data, mimetype='application/pdf')

    except Exception as e:
        current_app.logger.error(f"預覽生成失敗: {e}")
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        return jsonify({"error": str(e)}), 500

@temp_spec_bp.route('/create', methods=['GET', 'POST'])
@editor_or_admin_required
def create_temp_spec():
    if request.method == 'POST':
        data = request.form
        now = datetime.now()
        serial_number = _generate_next_spec_code()
        stations = request.form.getlist('station')
        if '其他' in stations and data.get('station_other'):
            stations[stations.index('其他')] = data.get('station_other')
        station_str = ', '.join(stations)
        tccs_info = f"{data.get('tccs_level', '')} ({data.get('tccs_4m', '')})"

        values = {
            'serial_number': serial_number,
            'theme': data['theme'],
            'applicant': data.get('applicant', ''),
            'applicant_phone': data.get('applicant_phone', ''),
            'station': station_str,
            'tccs_info': tccs_info,
            'start_date': data.get('start_date', ''),
            'package': data.get('package', ''),
            'lot_number': data.get('lot_number', ''),
            'equipment_type': data.get('equipment_type', ''),
            'change_before': data.get('change_before', ''),
            'change_after': data.get('change_after', ''),
            'data_needs': data.get('data_needs', ''),
        }

        generated_folder = os.path.join(BASE_DIR, current_app.config['GENERATED_FOLDER'])
        os.makedirs(generated_folder, exist_ok=True)
        word_path = os.path.join(generated_folder, f"{values['serial_number']}.docx")
        pdf_path = os.path.join(generated_folder, f"{values['serial_number']}.pdf")

        db_content_parts = []
        db_content_parts.append("變更前：\n")
        db_content_parts.append(values['change_before'])
        db_content_parts.append("\n\n變更後：\n")
        db_content_parts.append(values['change_after'])
        db_content_parts.append("\n\n資料收集需求：\n")
        db_content_parts.append(values['data_needs'])
        db_content = "".join(db_content_parts)
        
        try:
            start_date_obj = datetime.strptime(values['start_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date_obj = datetime.today().date()
        
        end_date_obj = start_date_obj + timedelta(days=30)
        values['end_date'] = end_date_obj.strftime('%Y-%m-%d')

        spec = TempSpec(
            spec_code=values['serial_number'],
            applicant=values['applicant'],
            title=values['theme'],
            content=db_content,
            start_date=start_date_obj,
            end_date=end_date_obj,
            created_at=now,
            status='pending_approval'
        )
        db.session.add(spec)
        db.session.flush()
        add_history_log(spec.id, '建立', f"建立暫時規範，編號為 {spec.spec_code}")
        db.session.commit()

        # 在產生用於下載的 PDF 前，需將 Markdown 轉為 HTML
        values['change_before'] = mistune.html(values['change_before'])
        values['change_after'] = mistune.html(values['change_after'])
        try:
            fill_template(values, os.path.join(BASE_DIR, 'template_with_placeholders.docx'), word_path, pdf_path)
        except Exception as e:
            current_app.logger.error(f"檔案生成失敗: {e}")
            flash('檔案生成失敗，可能是 Word 模板或 PDF 轉換器問題，請聯絡管理員。', 'danger')
            return redirect(url_for('temp_spec.create_temp_spec'))
            
        return send_file(word_path, as_attachment=True)

    next_spec_code = _generate_next_spec_code()
    return render_template('create_temp_spec.html', next_spec_code=next_spec_code)

@temp_spec_bp.route('/list')
def spec_list():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '')
    status_filter = request.args.get('status', '')
    specs_query = TempSpec.query

    if query:
        search_term = f"%{query}%"
        specs_query = specs_query.filter(
            db.or_(
                TempSpec.spec_code.ilike(search_term),
                TempSpec.title.ilike(search_term)
            )
        )
    
    if status_filter:
        specs_query = specs_query.filter(TempSpec.status == status_filter)

    pagination = specs_query.order_by(TempSpec.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    specs = pagination.items
    return render_template('spec_list.html', specs=specs, pagination=pagination, query=query, status=status_filter)

@temp_spec_bp.route('/activate/<int:spec_id>', methods=['GET', 'POST'])
@admin_required
def activate_spec(spec_id):
    spec = TempSpec.query.get_or_404(spec_id)
    if request.method == 'POST':
        uploaded_file = request.files.get('signed_file')
        if not uploaded_file or uploaded_file.filename == '':
            flash('您必須上傳一個檔案。', 'danger')
            return redirect(url_for('temp_spec.activate_spec', spec_id=spec.id))

        filename = secure_filename(f"{spec.spec_code}_signed_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
        upload_folder = os.path.join(BASE_DIR, current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        uploaded_file.save(file_path)

        new_upload = Upload(
            temp_spec_id=spec.id,
            filename=filename,
            upload_time=datetime.now()
        )
        db.session.add(new_upload)

        spec.status = 'active'
        add_history_log(spec.id, '啟用', f"上傳已簽核檔案 '{filename}'")
        db.session.commit()
        flash(f"規範 '{spec.spec_code}' 已生效！", 'success')
        return redirect(url_for('temp_spec.spec_list'))

    return render_template('activate_spec.html', spec=spec)

@temp_spec_bp.route('/terminate/<int:spec_id>', methods=['GET', 'POST'])
@editor_or_admin_required
def terminate_spec(spec_id):
    spec = TempSpec.query.get_or_404(spec_id)
    if request.method == 'POST':
        reason = request.form.get('reason')
        if not reason:
            flash('請填寫提早結束的原因。', 'danger')
            return redirect(url_for('temp_spec.terminate_spec', spec_id=spec.id))
        
        spec.status = 'terminated'
        spec.termination_reason = reason
        spec.end_date = datetime.today().date()
        add_history_log(spec.id, '終止', f"原因: {reason}")
        db.session.commit()
        flash(f"規範 '{spec.spec_code}' 已被提早終止。", 'warning')
        return redirect(url_for('temp_spec.spec_list'))

    return render_template('terminate_spec.html', spec=spec)

@temp_spec_bp.route('/download_initial/<int:spec_id>')
def download_initial_pdf(spec_id):
    spec = TempSpec.query.get_or_404(spec_id)
    generated_folder = os.path.join(BASE_DIR, current_app.config['GENERATED_FOLDER'])
    pdf_path = os.path.join(generated_folder, f"{spec.spec_code}.pdf")

    if not os.path.exists(pdf_path):
        flash('找不到最初產生的 PDF 檔案，可能已被刪除或移動。', 'danger')
        return redirect(url_for('temp_spec.spec_list'))

    return send_file(pdf_path, as_attachment=True)

@temp_spec_bp.route('/download_initial_word/<int:spec_id>')
@login_required
def download_initial_word(spec_id):
    spec = TempSpec.query.get_or_404(spec_id)
    # 安全性檢查：只有 editor 和 admin 可以下載 word
    if current_user.role not in ['editor', 'admin']:
        flash('權限不足，無法下載 Word 檔案。', 'danger')
        abort(403)

    generated_folder = os.path.join(BASE_DIR, current_app.config['GENERATED_FOLDER'])
    word_path = os.path.join(generated_folder, f"{spec.spec_code}.docx")

    if not os.path.exists(word_path):
        flash('找不到最初產生的 Word 檔案，可能已被刪除或移動。', 'danger')
        return redirect(url_for('temp_spec.spec_list'))

    return send_file(word_path, as_attachment=True)

@temp_spec_bp.route('/download_signed/<int:spec_id>')
def download_signed_pdf(spec_id):
    latest_upload = Upload.query.filter_by(temp_spec_id=spec_id).order_by(Upload.upload_time.desc()).first()

    if not latest_upload:
        flash('找不到任何已上傳的簽核檔案。', 'danger')
        return redirect(url_for('temp_spec.spec_list'))

    upload_folder = os.path.join(BASE_DIR, current_app.config['UPLOAD_FOLDER'])
    return send_file(os.path.join(upload_folder, latest_upload.filename), as_attachment=True)

@temp_spec_bp.route('/extend/<int:spec_id>', methods=['GET', 'POST'])
@editor_or_admin_required
def extend_spec(spec_id):
    spec = TempSpec.query.get_or_404(spec_id)
    
    if request.method == 'POST':
        new_end_date_str = request.form.get('new_end_date')
        uploaded_file = request.files.get('new_file')

        if not new_end_date_str:
            flash('請選擇新的結束日期', 'danger')
            return redirect(url_for('temp_spec.extend_spec', spec_id=spec.id))

        spec.end_date = datetime.strptime(new_end_date_str, '%Y-%m-%d').date()
        spec.extension_count += 1
        spec.status = 'active'

        if uploaded_file and uploaded_file.filename != '':
            filename = secure_filename(uploaded_file.filename)
            upload_folder = os.path.join(BASE_DIR, current_app.config['UPLOAD_FOLDER'])
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            uploaded_file.save(file_path)

            new_upload = Upload(
                temp_spec_id=spec.id,
                filename=filename,
                upload_time=datetime.now()
            )
            db.session.add(new_upload)
        
        details = f"展延結束日期至 {spec.end_date.strftime('%Y-%m-%d')}"
        if 'new_upload' in locals():
            details += f"，並上傳新檔案 '{new_upload.filename}'"
        add_history_log(spec.id, '展延', details)
        
        db.session.commit()
        flash(f"規範 '{spec.spec_code}' 已成功展延！", 'success')
        return redirect(url_for('temp_spec.spec_list'))

    default_new_end_date = spec.end_date + timedelta(days=30)
    return render_template('extend_spec.html', spec=spec, default_new_end_date=default_new_end_date)

@temp_spec_bp.route('/history/<int:spec_id>')
def spec_history(spec_id):
    spec = TempSpec.query.get_or_404(spec_id)
    history = SpecHistory.query.filter_by(spec_id=spec_id).order_by(SpecHistory.timestamp.desc()).all()
    return render_template('spec_history.html', spec=spec, history=history)

@temp_spec_bp.route('/delete/<int:spec_id>', methods=['POST'])
@admin_required
def delete_spec(spec_id):
    spec = TempSpec.query.get_or_404(spec_id)
    spec_code = spec.spec_code

    files_to_delete = []
    generated_folder = os.path.join(BASE_DIR, current_app.config['GENERATED_FOLDER'])
    files_to_delete.append(os.path.join(generated_folder, f"{spec.spec_code}.docx"))
    files_to_delete.append(os.path.join(generated_folder, f"{spec.spec_code}.pdf"))

    upload_folder = os.path.join(BASE_DIR, current_app.config['UPLOAD_FOLDER'])
    for upload_record in spec.uploads:
        files_to_delete.append(os.path.join(upload_folder, upload_record.filename))

    image_folder = os.path.join(BASE_DIR, 'static', 'uploads', 'images')
    if spec.content:
        image_urls = re.findall(r'!\[.*?\]\((.*?)\)', spec.content)
        for url in image_urls:
            if url.startswith('/static/uploads/images/'):
                img_filename = os.path.basename(url)
                files_to_delete.append(os.path.join(image_folder, img_filename))

    for f_path in files_to_delete:
        try:
            if os.path.exists(f_path):
                os.remove(f_path)
        except Exception as e:
            current_app.logger.error(f"刪除檔案失敗: {f_path}, 原因: {e}")

    db.session.delete(spec)
    db.session.commit()

    flash(f"規範 '{spec_code}' 及其所有相關檔案已成功刪除。", 'success')
    return redirect(url_for('temp_spec.spec_list'))