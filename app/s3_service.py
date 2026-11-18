import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import current_app, url_for

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


def allowed_file(filename):
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_s3_client():
    if not BOTO3_AVAILABLE:
        return None
        
    s3_bucket = current_app.config.get('S3_BUCKET')
    if not s3_bucket:
        return None

    region = current_app.config.get('AWS_DEFAULT_REGION', 'ap-south-1')
    access_key = current_app.config.get('AWS_ACCESS_KEY_ID')
    secret_key = current_app.config.get('AWS_SECRET_ACCESS_KEY')

    # If keys are provided explicitly, use them; otherwise boto3 automatically checks IAM Role
    if access_key and secret_key:
        return boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
    else:
        return boto3.client('s3', region_name=region)


def upload_image(file_storage, folder='hazards'):
    """
    Uploads a file to Amazon S3 (if configured) or stores it locally.
    Returns a tuple: (image_url, image_key_or_filename)
    """
    if not file_storage or file_storage.filename == '':
        return None, None

    if not allowed_file(file_storage.filename):
        raise ValueError("Invalid file extension. Only JPG, PNG, and WEBP images are allowed.")

    filename = secure_filename(file_storage.filename)
    unique_prefix = uuid.uuid4().hex[:10]
    safe_name = f"{unique_prefix}_{filename}"
    object_key = f"{folder}/{safe_name}"

    s3_bucket = current_app.config.get('S3_BUCKET')
    s3_client = get_s3_client()

    if s3_client and s3_bucket:
        try:
            # Upload directly to Amazon S3
            content_type = file_storage.content_type or 'image/jpeg'
            s3_client.upload_fileobj(
                file_storage,
                s3_bucket,
                object_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Generate pre-signed URL or public URL
            region = current_app.config.get('AWS_DEFAULT_REGION', 'ap-south-1')
            s3_url = f"https://{s3_bucket}.s3.{region}.amazonaws.com/{object_key}"
            return s3_url, object_key
        except (BotoCoreError, ClientError, Exception) as e:
            current_app.logger.warning(f"S3 upload failed: {e}. Falling back to local filesystem.")

    # Local fallback
    upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_folder / safe_name
    file_storage.seek(0)
    file_storage.save(str(file_path))
    
    local_url = f"/static/uploads/{safe_name}"
    return local_url, safe_name
