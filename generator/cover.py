import os
import click
from google.auth import default
from googleapiclient.discovery import build
import arrow
import fitz  # PyMuPDF
import config

DEFAULT_COVER_ID = "1HB1fUAY3uaARoHzSDh2TymfvNBvpKOEE221rubsjKoQ"


def create_cover_from_template(
    template_cover_id: str, replacement_map: dict, copy_title: str = None
):
    """
    Copies the original Google Doc, performs text replacements on the copy,
    exports that copy to PDF, and saves it locally.

    :param original_doc_id: ID of the source Google Doc
    :param replacement_map: dict mapping placeholder → replacement text
    :param pdf_output_path: local filename for the exported PDF
    :param copy_title: Optional new title for the copied Doc
    """
    # 1) Authenticate
    creds, _ = default(
        scopes=[
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    # 2) Copy the original Doc
    copy_metadata = {"name": copy_title or f"Copy of {template_cover_id}"}
    copy = drive.files().copy(fileId=template_cover_id, body=copy_metadata).execute()
    copy_id = copy["id"]
    print(f"Created copy: {copy_id} (title: {copy.get('name')})")

    # 3) Build batchUpdate requests for all placeholders
    requests = []
    for placeholder, new_text in replacement_map.items():
        requests.append(
            {
                "replaceAllText": {
                    "containsText": {"text": placeholder, "matchCase": True},
                    "replaceText": new_text,
                }
            }
        )
    result = (
        docs.documents()
        .batchUpdate(documentId=copy_id, body={"requests": requests})
        .execute()
    )
    total = 0
    for reply in result.get("replies", []):
        if reply is None:
            continue
        try:
            replace_all_text = reply.get("replaceAllText")
            if replace_all_text is not None and isinstance(replace_all_text, dict):
                occurrences = replace_all_text.get("occurrencesChanged")
                if isinstance(occurrences, int):
                    total += occurrences
        except (KeyError, TypeError, AttributeError):
            # Skip replies that have malformed structure
            pass
    print(f"Replaced {total} occurrences in the copy.")

    return copy_id


def generate_cover(drive, cache_dir, cover_file_id=None):
    if not cover_file_id:
        cover_file_id = config.load_cover_config()
        if not cover_file_id:
            click.echo("No cover file ID configured. Skipping cover generation.")
            return

    # Generate the formatted date
    today = arrow.now()
    formatted_date = today.format("Do MMMM YYYY")

    cover_id = create_cover_from_template(cover_file_id, {"{{DATE}}": formatted_date})
    pdf_blob = (
        drive.files().export(fileId=cover_id, mimeType="application/pdf").execute()
    )

    covers_dir = os.path.join(
        os.path.expanduser("~/.cache"), "songbook-generator", "cache", "covers"
    )
    os.makedirs(covers_dir, exist_ok=True)
    pdf_output_path = os.path.join(covers_dir, f"{cover_id}.pdf")
    with open(pdf_output_path, "wb") as f:
        f.write(pdf_blob)
    try:
        cover_pdf = fitz.open(pdf_output_path)
    except fitz.EmptyFileError:
        raise ValueError(
            f"Downloaded cover file is corrupted: {pdf_output_path}. Please check the file on Google Drive."
        )
    try:
        drive.files().delete(fileId=cover_id).execute()
        print(f"Deleted copy: {cover_id} from Google Drive.")
    except Exception as e:
        print(f"Failed to delete copy: {cover_id}. Error: {e}")
    return cover_pdf
