"""System-level API endpoints for file operations and platform utilities."""

from __future__ import annotations

import platform
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/system", tags=["system"])


class OpenFolderRequest(BaseModel):
    """Request to open a folder in the system file explorer."""

    path: str


class BrowseRequest(BaseModel):
    """Request to open a file/folder browser dialog."""

    initial_dir: str | None = None
    title: str | None = None
    file_types: list[tuple[str, str]] | None = None  # e.g., [("JSON files", "*.json")]


class BrowseResponse(BaseModel):
    """Response from file/folder browser dialog."""

    path: str | None
    cancelled: bool


@router.post("/open-folder")
async def open_folder(request: OpenFolderRequest) -> dict[str, str]:
    """Open a folder in the system's file explorer.

    Args:
        request: Request containing the folder path to open.

    Returns:
        Success message.

    Raises:
        HTTPException: If the path doesn't exist or can't be opened.
    """
    folder_path = Path(request.path)

    if not folder_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Path does not exist: {request.path}"
        )

    if not folder_path.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Path is not a directory: {request.path}"
        )

    try:
        system = platform.system()

        if system == "Darwin":  # macOS
            subprocess.run(["open", str(folder_path)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", str(folder_path)], check=True)
        elif system == "Linux":
            # Try common Linux file managers
            file_managers = ["xdg-open", "nautilus", "dolphin", "thunar", "nemo"]
            opened = False
            for fm in file_managers:
                try:
                    subprocess.run([fm, str(folder_path)], check=True)
                    opened = True
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue

            if not opened:
                raise HTTPException(
                    status_code=500,
                    detail="Could not find a suitable file manager on this Linux system",
                )
        else:
            raise HTTPException(
                status_code=500, detail=f"Unsupported platform: {system}"
            )

        return {"status": "success", "message": f"Opened folder: {request.path}"}

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


def _run_folder_dialog(initial_dir: str | None, title: str | None) -> str | None:
    """Run folder selection dialog in a separate thread (required for tkinter)."""
    import tkinter as tk
    from tkinter import filedialog

    result: list[str | None] = [None]

    def show_dialog():
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes("-topmost", True)  # Bring dialog to front

        selected = filedialog.askdirectory(
            initialdir=initial_dir or str(Path.home()),
            title=title or "Select Folder",
        )

        result[0] = selected if selected else None
        root.destroy()

    # Run in main thread context
    show_dialog()
    return result[0]


def _run_file_dialog(
    initial_dir: str | None,
    title: str | None,
    file_types: list[tuple[str, str]] | None,
) -> str | None:
    """Run file selection dialog in a separate thread (required for tkinter)."""
    import tkinter as tk
    from tkinter import filedialog

    result: list[str | None] = [None]

    def show_dialog():
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes("-topmost", True)  # Bring dialog to front

        # Default file types if none provided
        ftypes = file_types or [("All files", "*.*")]

        selected = filedialog.askopenfilename(
            initialdir=initial_dir or str(Path.home()),
            title=title or "Select File",
            filetypes=ftypes,
        )

        result[0] = selected if selected else None
        root.destroy()

    # Run in main thread context
    show_dialog()
    return result[0]


@router.post("/browse-folder", response_model=BrowseResponse)
async def browse_folder(request: BrowseRequest) -> BrowseResponse:
    """Open a native folder selection dialog.

    Args:
        request: Request with optional initial directory and title.

    Returns:
        Selected folder path or cancelled status.
    """
    try:
        # Run tkinter dialog (must be in main thread on macOS)
        selected_path = _run_folder_dialog(request.initial_dir, request.title)

        if selected_path:
            return BrowseResponse(path=selected_path, cancelled=False)
        else:
            return BrowseResponse(path=None, cancelled=True)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to open folder dialog: {e}"
        )


@router.post("/browse-file", response_model=BrowseResponse)
async def browse_file(request: BrowseRequest) -> BrowseResponse:
    """Open a native file selection dialog.

    Args:
        request: Request with optional initial directory, title, and file types.

    Returns:
        Selected file path or cancelled status.
    """
    try:
        # Convert file_types from list of lists to list of tuples if needed
        file_types: list[tuple[str, str]] | None = None
        if request.file_types:
            file_types = [(str(ft[0]), str(ft[1])) for ft in request.file_types]

        selected_path = _run_file_dialog(request.initial_dir, request.title, file_types)

        if selected_path:
            return BrowseResponse(path=selected_path, cancelled=False)
        else:
            return BrowseResponse(path=None, cancelled=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open file dialog: {e}")
