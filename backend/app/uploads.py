import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx', 'ppt', 'pptx'}
MAX_FILE_BYTES = 10 * 1024 * 1024


def _ext(filename):
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def save_upload(file_storage, subfolder):
    original = secure_filename(file_storage.filename or '')
    ext = _ext(original)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_FILE_BYTES:
        raise ValueError("File is larger than 10 MB.")
    if size == 0:
        raise ValueError("File is empty.")

    uploads_root = current_app.config['UPLOAD_FOLDER']
    target_dir = os.path.join(uploads_root, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    disk_path = os.path.join(target_dir, stored_name)
    file_storage.save(disk_path)

    return f"/uploads/{subfolder}/{stored_name}"
