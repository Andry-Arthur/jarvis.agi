"""Google Drive integration.

Reuses the same OAuth credentials.json as Gmail.
Scopes: https://www.googleapis.com/auth/drive
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
    ]
    creds_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def _docs_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]
    token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("docs", "v1", credentials=creds)


class DriveSearchTool(Tool):
    name = "drive_search"
    description = "Search for files in Google Drive by name or content."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Maximum results (default 10)"},
        },
        "required": ["query"],
    }

    async def execute(self, query: str, max_results: int = 10) -> str:
        try:
            service = _get_service()
            results = (
                service.files()
                .list(
                    q=f"fullText contains '{query}' or name contains '{query}'",
                    pageSize=max_results,
                    fields="files(id, name, mimeType, modifiedTime, webViewLink)",
                )
                .execute()
            )
            files = results.get("files", [])
            if not files:
                return f"No files found matching '{query}'."
            lines = []
            for f in files:
                lines.append(
                    f"• [{f['name']}]({f.get('webViewLink','')}) ({f['mimeType']}) — {f.get('modifiedTime','')}"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.error("drive_search failed: %s", exc)
            return f"Error searching Drive: {exc}"


class DriveReadDocTool(Tool):
    name = "drive_read_doc"
    description = "Read the text content of a Google Doc by its file ID."
    parameters = {
        "type": "object",
        "properties": {
            "file_id": {"type": "string", "description": "Google Drive file ID"},
        },
        "required": ["file_id"],
    }

    async def execute(self, file_id: str) -> str:
        try:
            docs = _docs_service()
            doc = docs.documents().get(documentId=file_id).execute()
            text_parts = []
            for element in doc.get("body", {}).get("content", []):
                paragraph = element.get("paragraph", {})
                for elem in paragraph.get("elements", []):
                    text_run = elem.get("textRun", {})
                    text_parts.append(text_run.get("content", ""))
            return "".join(text_parts).strip()
        except Exception as exc:
            logger.error("drive_read_doc failed: %s", exc)
            return f"Error reading doc: {exc}"


class DriveCreateDocTool(Tool):
    name = "drive_create_doc"
    description = "Create a new Google Doc with initial content."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Document title"},
            "content": {"type": "string", "description": "Initial text content"},
        },
        "required": ["title"],
    }

    async def execute(self, title: str, content: str = "") -> str:
        try:
            docs = _docs_service()
            doc = docs.documents().create(body={"title": title}).execute()
            doc_id = doc["documentId"]
            if content:
                docs.documents().batchUpdate(
                    documentId=doc_id,
                    body={
                        "requests": [
                            {
                                "insertText": {
                                    "location": {"index": 1},
                                    "text": content,
                                }
                            }
                        ]
                    },
                ).execute()
            return f"Document created: https://docs.google.com/document/d/{doc_id}/edit"
        except Exception as exc:
            logger.error("drive_create_doc failed: %s", exc)
            return f"Error creating doc: {exc}"


class DriveUploadFileTool(Tool):
    name = "drive_upload_file"
    description = "Upload a local file to Google Drive."
    parameters = {
        "type": "object",
        "properties": {
            "local_path": {"type": "string", "description": "Path to the local file"},
            "folder_id": {"type": "string", "description": "Parent folder ID (optional)"},
        },
        "required": ["local_path"],
    }

    async def execute(self, local_path: str, folder_id: str = "") -> str:
        try:
            import mimetypes

            from googleapiclient.http import MediaFileUpload

            service = _get_service()
            mime_type, _ = mimetypes.guess_type(local_path)
            mime_type = mime_type or "application/octet-stream"
            file_name = os.path.basename(local_path)
            metadata: dict = {"name": file_name}
            if folder_id:
                metadata["parents"] = [folder_id]
            media = MediaFileUpload(local_path, mimetype=mime_type)
            result = (
                service.files()
                .create(body=metadata, media_body=media, fields="id, webViewLink")
                .execute()
            )
            return f"Uploaded: {result.get('webViewLink', result['id'])}"
        except Exception as exc:
            logger.error("drive_upload_file failed: %s", exc)
            return f"Error uploading file: {exc}"


class GoogleDriveIntegration(Integration):
    name = "google_drive"

    def is_configured(self) -> bool:
        return bool(
            os.getenv("GOOGLE_DRIVE_ENABLED", "").lower() in ("1", "true", "yes")
            or (os.getenv("GMAIL_CREDENTIALS_FILE") or os.path.exists("credentials.json"))
        )

    def get_tools(self) -> list[Tool]:
        return [
            DriveSearchTool(),
            DriveReadDocTool(),
            DriveCreateDocTool(),
            DriveUploadFileTool(),
        ]
