"""
GitGallery application configuration.

Central configuration for paths, limits, and application constants.
For local testing you can hardcode GitHub OAuth credentials below.
Replace the placeholders with your actual values.
"""

from pathlib import Path
from typing import Final
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
load_dotenv()
# Base directory for GitGallery
USER_HOME: Final[Path] = Path.home()
APP_BASE_DIR: Final[Path] = USER_HOME / "GitGallery"

# Application folders
REPOS_DIR: Final[Path] = APP_BASE_DIR / "repos"
DATA_DIR: Final[Path] = APP_BASE_DIR / "data"
LOGS_DIR: Final[Path] = APP_BASE_DIR / "logs"
CONFIG_DIR: Final[Path] = APP_BASE_DIR / "config"
THUMBNAILS_DIR: Final[Path] = APP_BASE_DIR / "thumbnails"

# Index files
REPO_INDEX_FILENAME: Final[str] = "repo_index.json"
GALLERY_INDEX_FILENAME: Final[str] = "gallery_index.json"

# ---------------------------------------------------------------------
# Repository limits
# ---------------------------------------------------------------------

# Maximum repository size before splitting
MAX_REPO_SIZE_MB: Final[int] = 800
MAX_REPO_SIZE_BYTES: Final[int] = MAX_REPO_SIZE_MB * 1024 * 1024

# Maximum images per repository
MAX_IMAGES_PER_REPO: Final[int] = 300

# ---------------------------------------------------------------------
# GitHub OAuth Configuration
# ---------------------------------------------------------------------

"""
Create OAuth App here:
https://github.com/settings/developers

IMPORTANT SETTINGS:

Authorization callback URL:
http://127.0.0.1:8765/callback
"""

#REPLACE THESE WITH YOUR VALUES

GITHUB_OAUTH_CLIENT_ID: Final[str] = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")

GITHUB_OAUTH_CLIENT_SECRET: Final[str] = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")

if not GITHUB_OAUTH_CLIENT_ID or not GITHUB_OAUTH_CLIENT_SECRET:
    raise RuntimeError(
        "GitHub OAuth credentials not configured. Please set them in the .env file."
    )

# GitHub permissions
GITHUB_OAUTH_SCOPES: Final[list[str]] = [
    "repo",
    "read:user"
]

# OAuth URLs
GITHUB_AUTHORIZE_URL: Final[str] = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL: Final[str] = "https://github.com/login/oauth/access_token"

# ---------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------

# Allowed image formats
ALLOWED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp"}
)

# Maximum file size
MAX_FILE_SIZE_MB: Final[int] = 20
MAX_FILE_SIZE_BYTES: Final[int] = MAX_FILE_SIZE_MB * 1024 * 1024

# Folder safety limits
MAX_FOLDER_NAME_LENGTH: Final[int] = 200
MAX_PATH_COMPONENTS: Final[int] = 50

# ---------------------------------------------------------------------
# Thumbnail configuration
# ---------------------------------------------------------------------

# Thumbnail width
THUMBNAIL_WIDTH_PX: Final[int] = 300

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

LOG_FILENAME: Final[str] = "gitgallery.log"

# ---------------------------------------------------------------------
# Directory initialization
# ---------------------------------------------------------------------

def ensure_directories() -> None:
    """
    Create required GitGallery directories if they do not exist.
    """

    directories = [
        APP_BASE_DIR,
        REPOS_DIR,
        DATA_DIR,
        LOGS_DIR,
        CONFIG_DIR,
        THUMBNAILS_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)