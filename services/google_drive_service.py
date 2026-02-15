import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config

SCOPES = [
    "https://www.googleapis.com/auth/drive",
]

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _get_drive_service():
    """Create an authenticated Google Drive service."""
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def upload_file(file_path: str, file_name: str | None = None) -> str:
    """Upload a file to the configured Google Drive folder.

    Returns the web view link of the uploaded file.
    """
    service = _get_drive_service()

    if file_name is None:
        file_name = os.path.basename(file_path)

    ext = os.path.splitext(file_path)[1].lower()
    mime_type = MIME_TYPES.get(ext, "application/octet-stream")

    file_metadata = {
        "name": file_name,
        "parents": [config.GOOGLE_DRIVE_FOLDER_ID],
    }

    media = MediaFileUpload(file_path, mimetype=mime_type)
    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    return uploaded.get("webViewLink", uploaded.get("id"))
