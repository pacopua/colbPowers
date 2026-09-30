import base64
import hashlib
import hmac
import logging
import datetime
import mimetypes
import urllib.parse

from azure.storage.blob import BlobServiceClient, ContentSettings
from .transcriber_config import AZURE_STORAGE_CONNECTION_STRING

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
logger = logging.getLogger(__name__)


def _generate_sas_token(account_name: str, account_key: str, container_name: str,
                         blob_name: str, start: datetime.datetime, expiry: datetime.datetime) -> str:
    """
    Manually generate a SAS token using sv=2020-08-04.
    The newer SDK-generated versions (sv=2026-xx-xx) are rejected by Azure Speech
    diarization, while this older version works correctly.
    """
    start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
    expiry_str = expiry.strftime('%Y-%m-%dT%H:%M:%SZ')
    canonicalized_resource = f"/blob/{account_name}/{container_name}/{blob_name}"

    # String-to-sign format for sv=2020-08-04 service SAS on a blob (15 fields, no signedEncryptionScope)
    string_to_sign = "\n".join([
        "r",                    # signedPermissions
        start_str,              # signedStart
        expiry_str,             # signedExpiry
        canonicalized_resource, # canonicalizedResource
        "",                     # signedIdentifier
        "",                     # signedIP
        "https",                # signedProtocol
        "2020-08-04",           # signedVersion
        "b",                    # signedResource
        "",                     # signedSnapshotTime
        "",                     # rscc (Cache-Control)
        "",                     # rscd (Content-Disposition)
        "",                     # rsce (Content-Encoding)
        "",                     # rscl (Content-Language)
        "",                     # rsct (Content-Type)
    ])

    key_bytes = base64.b64decode(account_key)
    sig = base64.b64encode(
        hmac.new(key_bytes, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    ).decode('utf-8')

    return (
        f"sp=r"
        f"&st={start_str}"
        f"&se={expiry_str}"
        f"&spr=https"
        f"&sv=2020-08-04"
        f"&sr=b"
        f"&sig={urllib.parse.quote(sig, safe='')}"
    )


def upload_file_to_blob(blob_name: str, file_path: str, folder_path: str = None, container_name: str = "speech-issues") -> str:
    """Uploads file to blob and returns a SAS URL compatible with Azure Speech diarization."""
    if folder_path:
        blob_name = f"{folder_path.rstrip('/')}/{blob_name.lstrip('/')}"

    service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = service_client.get_container_client(container_name)
    if not container_client.exists():
        container_client.create_container()

    blob_client = container_client.get_blob_client(blob_name)

    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = "application/octet-stream"

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))

    items = dict(item.split('=', 1) for item in AZURE_STORAGE_CONNECTION_STRING.split(';') if '=' in item)
    account_name = items.get('AccountName')
    account_key = items.get('AccountKey')

    start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)

    sas_token = _generate_sas_token(account_name, account_key, container_name, blob_name, start, expiry)
    base_url = blob_client.url.split('?')[0]
    url_with_sas = f"{base_url}?{sas_token}"
    logger.info(f"Blob uploaded: {blob_name}. SAS URL generated.")
    return url_with_sas

def download_file(blob_name: str, local_path: str, container_name: str = "speech-issues"):
    service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    
    with open(local_path, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

def get_blob_content_as_text(blob_name: str, container_name: str = "speech-issues") -> str:
    service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    return blob_client.download_blob().readall().decode("utf-8")
