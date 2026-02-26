import os
import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse

from utils.hashing import sha256_file


# ===== LOGGING SETUP =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== CONFIG =====
STORAGE_PATH = os.getenv(
    "STORAGE_PATH",
    "/u/dramirez/WORK/sts_metrology/metrology_db/data/"
)
TEMP_PATH = "./temp_uploads"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".txt", ".csv", ".dat", ".json"}

os.makedirs(STORAGE_PATH, exist_ok=True)
os.makedirs(TEMP_PATH, exist_ok=True)

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# ===== CUSTOM EXCEPTIONS =====
class InvalidFile(Exception):
    """Exception raised when a file is invalid or cannot be accessed."""
    pass


# ===== VALIDATION HELPERS =====
def is_ascii(file_bytes: bytes) -> bool:
    """Check if file content is ASCII-compatible."""
    return all(b < 128 for b in file_bytes)


def validate_file_content(content: bytes, filename: str) -> tuple[bool, str]:
    """
    Validate file content against multiple criteria.
    
    Args:
        content: The file content as bytes
        filename: The original filename
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Check if file is empty
        if not content:
            return False, "File is empty"
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            return False, f"File exceeds maximum size of {MAX_FILE_SIZE} bytes"
        
        # Check ASCII compatibility
        if not is_ascii(content):
            return False, "File contains non-ASCII characters"
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext and file_ext not in ALLOWED_EXTENSIONS:
            return False, f"File extension {file_ext} not allowed"
        
        # Additional check: try to decode as text
        try:
            content.decode("ascii")
        except UnicodeDecodeError as e:
            return False, f"File is not valid ASCII: {str(e)}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Validation error for {filename}: {str(e)}")
        return False, f"Validation error: {str(e)}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    
    Args:
        filename: The original filename
        
    Returns:
        str: The sanitized filename
    """
    return os.path.basename(filename)


def cleanup_session(session_dir: str) -> None:
    """
    Safely clean up a temporary session directory.
    
    Args:
        session_dir: Path to the session directory
    """
    try:
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir, ignore_errors=False)
            logger.info(f"Cleaned up session directory: {session_dir}")
    except Exception as e:
        logger.error(f"Failed to clean up session directory {session_dir}: {str(e)}")


# ===== FILE OPERATIONS =====
def save_temp_files(files: list[UploadFile]) -> tuple[str, list[str], list[str]]:
    """
    Save uploaded files to a temporary session directory.
    
    Args:
        files: List of uploaded files
        
    Returns:
        tuple: (session_id, saved_files, error_messages)
    """
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(TEMP_PATH, session_id)
    
    saved_files = []
    error_messages = []
    
    try:
        os.makedirs(session_dir, exist_ok=True)
        
        for file in files:
            try:
                # Sanitize filename
                safe_filename = sanitize_filename(file.filename)
                
                # Read file content
                content = file.file.read()
                
                # Validate file content
                is_valid, error_msg = validate_file_content(content, safe_filename)
                if not is_valid:
                    error_messages.append(f"{safe_filename}: {error_msg}")
                    logger.warning(f"Validation failed for {safe_filename}: {error_msg}")
                    continue
                
                # Write to temporary location
                temp_path = os.path.join(session_dir, safe_filename)
                with open(temp_path, "wb") as f:
                    f.write(content)
                
                saved_files.append(safe_filename)
                logger.info(f"Saved temporary file: {safe_filename}")
            
            except Exception as e:
                error_msg = f"{file.filename}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(f"Error processing file {file.filename}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error creating session directory {session_dir}: {str(e)}")
        cleanup_session(session_dir)
        error_messages.append(f"Session creation failed: {str(e)}")
    
    return session_id, saved_files, error_messages


def move_to_storage(session_id: str, overwrite: bool = False) -> tuple[list[str], list[str], list[str]]:
    """
    Move files from temporary session to permanent storage.
    
    Args:
        session_id: The session ID to move
        overwrite: Whether to overwrite existing files
        
    Returns:
        tuple: (saved_files, conflicts, error_messages)
    """
    session_dir = os.path.join(TEMP_PATH, session_id)
    saved_files = []
    conflicts = []
    error_messages = []
    
    if not os.path.exists(session_dir):
        logger.warning(f"Session directory not found: {session_dir}")
        return saved_files, conflicts, ["Session not found"]
    
    try:
        for filename in os.listdir(session_dir):
            temp_file = os.path.join(session_dir, filename)
            final_file = os.path.join(STORAGE_PATH, filename)
            
            try:
                # Check for conflicts
                if os.path.exists(final_file) and not overwrite:
                    conflicts.append(filename)
                    logger.info(f"File conflict detected: {filename}")
                    continue
                
                # Move file to storage
                shutil.move(temp_file, final_file)
                saved_files.append(filename)
                logger.info(f"Moved file to storage: {filename}")
            
            except Exception as e:
                error_msg = f"Failed to move {filename}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(error_msg)
    
    except Exception as e:
        error_msg = f"Error reading session directory: {str(e)}"
        error_messages.append(error_msg)
        logger.error(error_msg)
    
    finally:
        # Always cleanup the session directory
        cleanup_session(session_dir)
    
    return saved_files, conflicts, error_messages


# ===== ROUTES =====
@app.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Display the file upload page."""
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "message": None,
            "conflicts": [],
            "session_id": None,
            "errors": []
        },
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
):
    """Handle file upload."""
    try:
        session_id, saved_files, upload_errors = save_temp_files(files)
        saved, conflicts, move_errors = move_to_storage(session_id, overwrite=False)
        
        all_errors = upload_errors + move_errors
        message = [f"{f}: saved" for f in saved]
        
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "message": message,
                "conflicts": conflicts,
                "session_id": session_id if conflicts else None,
                "errors": all_errors,
            },
        )
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "message": None,
                "conflicts": [],
                "session_id": None,
                "errors": [f"Upload failed: {str(e)}"],
            },
        )


@app.post("/overwrite", response_class=HTMLResponse)
async def overwrite_files(
    request: Request,
    session_id: str = Form(...),
):
    """Handle file overwrite."""
    try:
        saved, _, move_errors = move_to_storage(session_id, overwrite=True)
        message = [f"{f}: overwritten" for f in saved]
        
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "message": message,
                "conflicts": [],
                "session_id": None,
                "errors": move_errors,
            },
        )
    
    except Exception as e:
        logger.error(f"Overwrite error: {str(e)}")
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "message": None,
                "conflicts": [],
                "session_id": None,
                "errors": [f"Overwrite failed: {str(e)}"],
            },
        )


@app.get("/files", response_class=HTMLResponse)
async def list_files(request: Request):
    """List all uploaded files."""
    files_list = []
    
    try:
        for fname in os.listdir(STORAGE_PATH):
            fpath = os.path.join(STORAGE_PATH, fname)
            if os.path.isfile(fpath):
                try:
                    stat = os.stat(fpath)
                    files_list.append({
                        "name": fname,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    logger.error(f"Error processing file {fname}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
    
    return templates.TemplateResponse(
        "files.html",
        {"request": request, "files": files_list}
    )


@app.get("/download/{filename}", response_class=FileResponse)
async def download_file(filename: str):
    """Download a file from storage."""
    try:
        # Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(filename)
        file_path = os.path.join(STORAGE_PATH, safe_filename)
        
        # Verify file exists and is within storage path
        if not os.path.isfile(file_path):
            logger.warning(f"Download attempt for non-existent file: {safe_filename}")
            raise HTTPException(status_code=404, detail="File not found")
        
        # Additional safety check
        real_path = os.path.realpath(file_path)
        real_storage = os.path.realpath(STORAGE_PATH)
        if not real_path.startswith(real_storage):
            logger.warning(f"Path traversal attempt detected: {filename}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"File downloaded: {safe_filename}")
        return FileResponse(
            file_path,
            media_type="application/octet-stream",
            filename=safe_filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")


@app.post("/delete/{filename}", response_class=HTMLResponse)
async def delete_file(request: Request, filename: str):
    """Delete a file from storage."""
    try:
        # Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(filename)
        file_path = os.path.join(STORAGE_PATH, safe_filename)
        
        # Verify file exists and is within storage path
        if not os.path.isfile(file_path):
            logger.warning(f"Delete attempt for non-existent file: {safe_filename}")
            raise HTTPException(status_code=404, detail="File not found")
        
        # Additional safety check
        real_path = os.path.realpath(file_path)
        real_storage = os.path.realpath(STORAGE_PATH)
        if not real_path.startswith(real_storage):
            logger.warning(f"Path traversal attempt detected: {filename}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        os.remove(file_path)
        logger.info(f"File deleted: {safe_filename}")
        
        return await list_files(request)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        raise HTTPException(status_code=500, detail="Delete failed")
