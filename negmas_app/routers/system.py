"""System-level API endpoints for file operations and platform utilities."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/system", tags=["system"])


class OpenFolderRequest(BaseModel):
    """Request to open a folder in the system file explorer."""

    path: str


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
