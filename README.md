# GitGallery

**GitGallery** is a desktop application that lets you store and manage photos using your own GitHub repositories as storage. All data stays in your account; the app does not host or store your photos remotely.

## Important: Use Private Repositories

GitGallery stores images directly inside GitHub repositories.  
To keep your photos private, **you should always use a PRIVATE repository**.

If you upload images to a **public repository**, those images will be publicly accessible on GitHub and can be viewed or downloaded by anyone.

Recommended workflow:

1. Create a **private repository** on GitHub.
2. Connect your account through the GitGallery OAuth flow.
3. Select or create the **private repository** when storing images.

GitGallery **does not encrypt images in V1**, therefore repository visibility is the primary mechanism controlling access to your photos.

## Disclaimer

GitGallery is a **personal project created for educational and experimental purposes**.

This software is provided **as-is**, without any guarantees regarding security, reliability, or data protection.

By using this project, you acknowledge that:

- GitGallery is not intended to be a production-grade secure storage system.
- Sensitive or confidential data should not be stored using this application.
- Repository privacy settings on GitHub determine who can access uploaded images.
- The author assumes no responsibility for data loss, exposure, or misuse resulting from the use of this software.

Users are responsible for managing their GitHub repositories, privacy settings, and account security.

## Features (V1)

- **Connect GitHub** — Sign in with GitHub OAuth (no passwords stored).
- **Repositories** — Choose an existing repo or create a new one.
- **Upload** — Add images to folders; batch uploads in a single commit.
- **Gallery** — View thumbnails (from cache), open full image, download, delete (single or multi-select). Drag-and-drop images to upload.
- **Folders** — Organize photos into collections inside the repo.
- **Sync** — Pull then push (with loading indicator). Git runs in background threads.
- **How-To Guide** — Steps for Git, SSH keys, and GitHub setup.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitGallery Desktop App                     │
├─────────────────────────────────────────────────────────────────┤
│  UI Layer (PySide6)                                               │
│  ├── Dashboard (sidebar: Gallery, Upload, Folders, Repos, Sync)  │
│  ├── Connect GitHub Dialog (OAuth)                                │
│  ├── Repo Selector / Create Repo                                 │
│  ├── Upload Dialog, Folder Dialog                                 │
│  ├── Gallery View (thumbnails, multi-select, download, delete, drag-drop) │
│  └── How-To Page                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Workers (QThread)                                                │
│  ├── git_worker      — clone, add, commit, push, pull, sync       │
│  └── upload_worker   — copy, thumbnails, gallery index            │
├─────────────────────────────────────────────────────────────────┤
│  Core Layer                                                       │
│  ├── github_connector   — OAuth, GitHub API (repos, create)        │
│  ├── git_manager       — Git CLI (shallow clone, add, commit…)    │
│  ├── repo_manager      — repo_index.json, gallery_index.json      │
│  ├── file_manager      — list folders/photos, copy, delete         │
│  ├── thumbnail_manager — Pillow 300px thumbnails → thumbnails/    │
│  └── sync_manager      — pull then push                           │
├─────────────────────────────────────────────────────────────────┤
│  Data / Storage                                                   │
│  ├── ~/GitGallery/repos/       — cloned repositories (shallow)    │
│  ├── ~/GitGallery/data/        — repo_index.json, gallery_index.json │
│  ├── ~/GitGallery/thumbnails/  — cached thumbnails (300px)        │
│  └── ~/GitGallery/logs/        — gitgallery.log                   │
└─────────────────────────────────────────────────────────────────┘
```

- **Repository layout:** Photos live under folder names inside the repo, e.g. `vacation/photo1.jpg`, `family/photo2.png`.
- **Automatic splitting (V1 ready):** When a repo exceeds 800 MB or 300 images, the architecture supports creating additional repos (e.g. `vacation1`, `vacation2`) and mapping them in `repo_index.json` so the user still sees one logical folder.

## Requirements

- **Python** 3.11+
- **Git** installed and on PATH
- **GitHub account** and (for OAuth) a GitHub OAuth App

## Installation

1. **Clone or download** this project.

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # or: source .venv/bin/activate   # Linux/macOS
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**

   ```bash
   python run.py
   ```
   Or from project root: `python -m gitgallery.app.main`

## GitHub Connection (OAuth)

To use “Connect GitHub Account” in the app you need a **GitHub OAuth App**:

1. Go to [GitHub → Settings → Developer settings → OAuth Apps](https://github.com/settings/developers) and **New OAuth App**.
2. Set **Authorization callback URL** to: `http://127.0.0.1:8765/callback`
3. Copy the **Client ID** (and optionally **Client secret** if you use a confidential app).
4. Set the Client ID in the app (e.g. in `gitgallery/app/config.py`: `GITHUB_OAUTH_CLIENT_ID`) or via environment variable if you add support.

The app never stores your GitHub password. Tokens are used only in memory for the session (V1).

## How-To Guide (in app)

The in-app **How-To Guide** covers:

1. **Create a GitHub account** — [github.com](https://github.com)
2. **Install Git** — [git-scm.com](https://git-scm.com/downloads)
3. **Generate SSH key** — e.g. `ssh-keygen -t ed25519 -C "your_email@example.com"`
4. **Add SSH key to GitHub** — Settings → SSH and GPG keys → New SSH key
5. **Connect GitHub to GitGallery** — Use the Connect button and authorize the OAuth app

## Example Workflow

1. Launch GitGallery → **Connect GitHub Account** (mandatory on first run).
2. **Select** an existing repository or **Create New Repository** (e.g. `my-photos`).
3. Click **Upload** → choose images → choose or create a **folder** → upload (single commit for the batch).
4. Use **Gallery** to view thumbnails, open full image, **Download**, or **Delete** (single or multi-select).
5. Use **Sync** to run `git pull` and then `git push` for your repos.

## Error Handling

The app handles and shows clear messages for:

- Git not installed or not in PATH  
- SSH authentication failure (clone/push)  
- GitHub API errors  
- Repository not found  
- Network failure  
- Merge conflicts (with guidance to resolve manually)

## Security

- **No passwords or tokens are stored** on disk (OAuth token only in memory for the session).
- Folder and file names are validated (validators.py) to prevent path traversal.
- Allowed image types: **jpg, jpeg, png, webp** only. Max file size **20MB**.
- Architecture is prepared for future end-to-end encryption (not implemented in V1).

## Logging

All operations (uploads, deletions, repo operations, sync, errors) are logged to:

- `~/GitGallery/logs/gitgallery.log`

## Project Layout

```
GitGallery/
├── gitgallery/
│   ├── app/           — main.py, config.py
│   ├── core/          — git_manager, github_connector, repo_manager, file_manager,
│   │                    sync_manager, thumbnail_manager
│   ├── workers/       — git_worker.py, upload_worker.py (QThread)
│   ├── ui/            — dashboard, dialogs, gallery_view, howto_page
│   ├── models/        — repository, folder, photo
│   ├── utils/         — logger, helpers, validators
│   └── data/          — repo_index.json, gallery_index.json
├── logs/
├── tests/             — test_helpers, test_validators, test_repo_manager
├── requirements.txt
├── run.py
└── README.md
```

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **Git not found** | Install Git and ensure it is on your PATH. On Windows, restart the terminal after installing. |
| **GitHub connection fails** | Create an OAuth App, set callback URL to `http://127.0.0.1:8765/callback`, and set `GITHUB_OAUTH_CLIENT_ID` in config or environment. |
| **SSH clone/push fails** | Generate an SSH key (`ssh-keygen -t ed25519`), add the public key to GitHub (Settings → SSH and GPG keys). |
| **Upload fails: file too large** | Images must be ≤ 20MB. Use jpg, jpeg, png, or webp only. |
| **Sync shows merge conflict** | Resolve conflicts manually in the repo folder (e.g. edit files, `git add`, `git commit`), then run Sync again or push from the repo. |
| **Gallery empty after adding repo** | Ensure the repo has at least one folder with images (jpg/jpeg/png/webp). The app builds the gallery index from the repo on first load. |
| **Thumbnails not showing** | Thumbnails are generated on upload. For existing images, open the repo in GitGallery and the index is built from the filesystem once. |

## License

Use and modify as needed for your project.
