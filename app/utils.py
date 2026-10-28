import os
import uuid
from pathlib import Path
from flask import current_app, g, url_for
from werkzeug.exceptions import BadRequest
from app import db


def allowed_file(filename):
    return bool(filename and '.' in filename and
                filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS'])


def validate_image(upload):
    if not allowed_file(upload.filename):
        raise ValueError('Choose a PNG, JPEG, GIF, or WebP image.')
    try:
        from PIL import Image
        upload.stream.seek(0)
        with Image.open(upload.stream) as image:
            expected = {'png': 'PNG', 'jpg': 'JPEG', 'jpeg': 'JPEG', 'gif': 'GIF', 'webp': 'WEBP'}
            if image.format != expected[upload.filename.rsplit('.', 1)[1].lower()]:
                raise ValueError('Image contents do not match the filename.')
            if image.width * image.height > 25_000_000:
                raise ValueError('Image must contain no more than 25 million pixels.')
            image.verify()
    except Exception as exc:
        raise ValueError('Choose a valid image matching its file extension (maximum 25 million pixels).') from exc
    finally:
        upload.stream.seek(0)


def image_url(value):
    if not value:
        return ''
    if value.startswith(('http://', 'https://')):
        return value
    if value.startswith('supabase/'):
        from app.storage import public_url
        return public_url(value.removeprefix('supabase/'))
    if value.startswith('uploads/'):
        return url_for('public.upload', filename=value.removeprefix('uploads/'))
    return url_for('static', filename=value)


def http_url(value):
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(value or '')
        return value if parsed.scheme.lower() in {'http', 'https'} and parsed.hostname else '#'
    except ValueError:
        return '#'


def phone_digits(value):
    return ''.join(char for char in (value or '') if char in '0123456789')


def save_upload(file_storage):
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None
    try:
        validate_image(file_storage)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    safe_name = f'{uuid.uuid4().hex}.{ext}'
    if current_app.config['STORAGE_BACKEND'] == 'supabase':
        from app.storage import upload_image
        value = f'supabase/{safe_name}'
        g.new_uploads = getattr(g, 'new_uploads', []) + [value]
        upload_image(file_storage, safe_name)
        return value
    dest = Path(current_app.config['UPLOAD_FOLDER']) / safe_name
    g.new_uploads = getattr(g, 'new_uploads', []) + [f'uploads/{safe_name}']
    file_storage.save(dest)
    return f'uploads/{safe_name}'


def _remove_upload(value):
    if value and value.startswith('supabase/'):
        from app.storage import delete_image
        delete_image(value.removeprefix('supabase/'))
        return
    # Only generated uploads may be deleted, never bundled assets or external images.
    if not value or not value.startswith('uploads/'):
        return
    name = value.removeprefix('uploads/')
    if not name or name != os.path.basename(name):
        return
    try:
        (Path(current_app.config['UPLOAD_FOLDER']) / name).unlink(missing_ok=True)
    except OSError:
        current_app.logger.exception('Could not remove uploaded image %s', name)


def remove_after_commit(value):
    if value:
        g.obsolete_uploads = getattr(g, 'obsolete_uploads', []) + [value]


def commit_changes():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        cleanup_pending_uploads()
        raise
    g.new_uploads = []
    from app.models import ClothingImage, SiteSettings, Achievement, ClientShowcase
    for value in getattr(g, 'obsolete_uploads', []):
        referenced = (ClothingImage.query.filter_by(image_url=value).first() or
                      Achievement.query.filter_by(image_url=value).first() or
                      ClientShowcase.query.filter_by(image_url=value).first() or
                      SiteSettings.query.filter(db.or_(SiteSettings.logo == value,
                                                       SiteSettings.designer_image == value)).first())
        if not referenced:
            _remove_upload(value)
    g.obsolete_uploads = []


def cleanup_pending_uploads(error=None):
    for value in getattr(g, 'new_uploads', []):
        _remove_upload(value)
    g.new_uploads = []
