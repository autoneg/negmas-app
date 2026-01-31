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


def _run_folder_dialog_macos(initial_dir: str | None, title: str | None) -> str | None:
    """Run folder selection dialog on macOS using AppleScript."""
    import shlex

    prompt = title or "Select Folder"
    # Build AppleScript command
    script = f'POSIX path of (choose folder with prompt "{prompt}"'
    if initial_dir and Path(initial_dir).exists():
        script += f' default location POSIX file "{initial_dir}"'
    script += ")"

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        if result.returncode == 0:
            # Remove trailing newline and slash
            path = result.stdout.strip().rstrip("/")
            return path if path else None
        return None  # User cancelled or error
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def _run_file_dialog_macos(
    initial_dir: str | None,
    title: str | None,
    file_types: list[tuple[str, str]] | None,
) -> str | None:
    """Run file selection dialog on macOS using AppleScript."""
    prompt = title or "Select File"
    script = f'POSIX path of (choose file with prompt "{prompt}"'
    if initial_dir and Path(initial_dir).exists():
        script += f' default location POSIX file "{initial_dir}"'
    # Note: AppleScript file type filtering is complex, skipping for simplicity
    script += ")"

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            return path if path else None
        return None
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def _run_folder_dialog_windows(
    initial_dir: str | None, title: str | None
) -> str | None:
    """Run folder selection dialog on Windows using PowerShell."""
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = '{title}'
    {initial_dir_line}
    $result = $dialog.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
        Write-Output $dialog.SelectedPath
    }}
    """.format(
        title=title or "Select Folder",
        initial_dir_line=f"$dialog.SelectedPath = '{initial_dir}'"
        if initial_dir
        else "",
    )

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            return path if path else None
        return None
    except Exception:
        return None


def _run_file_dialog_windows(
    initial_dir: str | None,
    title: str | None,
    file_types: list[tuple[str, str]] | None,
) -> str | None:
    """Run file selection dialog on Windows using PowerShell."""
    # Build filter string
    filter_str = "All files (*.*)|*.*"
    if file_types:
        filters = [f"{desc} ({pattern})|{pattern}" for desc, pattern in file_types]
        filter_str = "|".join(filters)

    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = '{title}'
    $dialog.Filter = '{filter}'
    {initial_dir_line}
    $result = $dialog.ShowDialog()
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
        Write-Output $dialog.FileName
    }}
    """.format(
        title=title or "Select File",
        filter=filter_str,
        initial_dir_line=f"$dialog.InitialDirectory = '{initial_dir}'"
        if initial_dir
        else "",
    )

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            return path if path else None
        return None
    except Exception:
        return None


def _run_folder_dialog_linux(initial_dir: str | None, title: str | None) -> str | None:
    """Run folder selection dialog on Linux using zenity or kdialog."""
    # Try zenity first (GNOME)
    try:
        cmd = ["zenity", "--file-selection", "--directory"]
        if title:
            cmd.extend(["--title", title])
        if initial_dir and Path(initial_dir).exists():
            cmd.extend(["--filename", initial_dir + "/"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return result.stdout.strip() or None
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # Try kdialog (KDE)
    try:
        cmd = ["kdialog", "--getexistingdirectory"]
        if initial_dir and Path(initial_dir).exists():
            cmd.append(initial_dir)
        if title:
            cmd.extend(["--title", title])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return result.stdout.strip() or None
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return None


def _run_file_dialog_linux(
    initial_dir: str | None,
    title: str | None,
    file_types: list[tuple[str, str]] | None,
) -> str | None:
    """Run file selection dialog on Linux using zenity or kdialog."""
    # Try zenity first
    try:
        cmd = ["zenity", "--file-selection"]
        if title:
            cmd.extend(["--title", title])
        if initial_dir and Path(initial_dir).exists():
            cmd.extend(["--filename", initial_dir + "/"])
        if file_types:
            for desc, pattern in file_types:
                cmd.extend(["--file-filter", f"{desc} | {pattern}"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return result.stdout.strip() or None
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # Try kdialog
    try:
        cmd = ["kdialog", "--getopenfilename"]
        if initial_dir and Path(initial_dir).exists():
            cmd.append(initial_dir)
        else:
            cmd.append(".")
        if file_types:
            # kdialog filter format: "*.txt *.doc | Text files"
            patterns = " ".join(p for _, p in file_types)
            cmd.append(patterns)
        if title:
            cmd.extend(["--title", title])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return result.stdout.strip() or None
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return None


def _run_folder_dialog(initial_dir: str | None, title: str | None) -> str | None:
    """Run folder selection dialog using platform-appropriate method."""
    system = platform.system()

    if system == "Darwin":
        return _run_folder_dialog_macos(initial_dir, title)
    elif system == "Windows":
        return _run_folder_dialog_windows(initial_dir, title)
    elif system == "Linux":
        return _run_folder_dialog_linux(initial_dir, title)
    else:
        return None


def _run_file_dialog(
    initial_dir: str | None,
    title: str | None,
    file_types: list[tuple[str, str]] | None,
) -> str | None:
    """Run file selection dialog using platform-appropriate method."""
    system = platform.system()

    if system == "Darwin":
        return _run_file_dialog_macos(initial_dir, title, file_types)
    elif system == "Windows":
        return _run_file_dialog_windows(initial_dir, title, file_types)
    elif system == "Linux":
        return _run_file_dialog_linux(initial_dir, title, file_types)
    else:
        return None


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
