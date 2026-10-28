"""Server-only access to managed images in a public Supabase Storage bucket."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import current_app
from werkzeug.exceptions import BadGateway

MIME_TYPES = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
              'gif': 'image/gif', 'webp': 'image/webp'}


def _endpoint(path):
    return current_app.config['SUPABASE_URL'].rstrip('/') + '/storage/v1/' + path


def _request(method, path, data=None, content_type='application/json'):
    key = current_app.config['SUPABASE_SERVICE_ROLE_KEY']
    request = Request(_endpoint(path), data=data, method=method, headers={
        'Authorization': 'Bearer ' + key, 'apikey': key, 'Content-Type': content_type,
    })
    return urlopen(request, timeout=30)


def _bucket():
    return quote(current_app.config['SUPABASE_STORAGE_BUCKET'], safe='')


def _valid_name(name):
    return bool(re.fullmatch(r'[0-9a-f]{32}\.(?:png|jpg|jpeg|gif|webp)', name))


def public_url(name):
    if not _valid_name(name):
        raise ValueError('Invalid managed image name.')
    return _endpoint('object/public/' + _bucket() + '/' + quote(name, safe=''))


def upload_image(upload, name):
    if not _valid_name(name):
        raise ValueError('Invalid managed image name.')
    try:
        upload.stream.seek(0)
        with _request('POST', 'object/' + _bucket() + '/' + name,
                      upload.stream.read(), MIME_TYPES[name.rsplit('.', 1)[1]]):
            pass
    except (HTTPError, URLError, OSError):
        # Never expose response bodies, headers, or service credentials.
        current_app.logger.error('Managed image upload failed.')
        raise BadGateway('Image storage is temporarily unavailable. Please try again.') from None


def delete_image(name):
    if not _valid_name(name):
        return
    try:
        with _request('DELETE', 'object/' + _bucket(), json.dumps({'prefixes': [name]}).encode()):
            pass
    except (HTTPError, URLError, OSError):
        current_app.logger.error('Could not remove managed image %s.', name)


def initialize_bucket():
    """Create the bucket if absent; existing private buckets stay private."""
    try:
        try:
            with _request('GET', 'bucket/' + _bucket()) as response:
                bucket = json.load(response)
            if not bucket.get('public'):
                raise RuntimeError('The configured image bucket must be public. Use a dedicated catalogue-image bucket.')
            return
        except HTTPError as exc:
            missing = exc.code == 404
            if exc.code == 400:
                # Older Storage gateways return HTTP 400 with a 404 statusCode.
                try:
                    details = json.load(exc)
                except (ValueError, TypeError):
                    details = {}
                missing = isinstance(details, dict) and str(details.get('statusCode')) == '404'
            if not missing:
                raise
        name = current_app.config['SUPABASE_STORAGE_BUCKET']
        data = json.dumps({'id': name, 'name': name, 'public': True,
                           'file_size_limit': current_app.config['MAX_CONTENT_LENGTH'],
                           'allowed_mime_types': sorted(set(MIME_TYPES.values()))}).encode()
        with _request('POST', 'bucket', data):
            pass
    except (HTTPError, URLError, OSError):
        raise RuntimeError('Could not initialize image storage. Check the Supabase project URL, server-only service-role key, and bucket name.') from None
