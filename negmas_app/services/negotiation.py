"""Negotiation service - handles running negotiations."""

import asyncio
import sys
import uuid
from typing import Any, AsyncGenerator

from ..models import NegotiationParams


class NegotiationService:
    """Service for managing and running negotiations."""

    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}

    def create_job(self, params: NegotiationParams) -> str:
        """Create a new negotiation job and return its ID."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "params": params,
            "status": "pending",
            "output": [],
            "result": None,
            "return_code": None,
        }
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get the status of a job."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            "status": job["status"],
            "output_lines": len(job["output"]),
            "return_code": job["return_code"],
        }

    async def run_negotiation(
        self, job_id: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run a negotiation and yield status updates."""
        job = self._jobs.get(job_id)
        if not job:
            yield {"event": "error", "message": "Job not found"}
            return

        params: NegotiationParams = job["params"]
        cmd = [sys.executable, "-m", "negmas.scripts.negotiate"] + params.to_cli_args()

        yield {"event": "status", "status": "running", "command": " ".join(cmd)}

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        job["status"] = "running"

        while True:
            if process.stdout is None:
                break
            line = await process.stdout.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace")
            job["output"].append(decoded)
            yield {"event": "output", "line": decoded}

        await process.wait()

        job["status"] = "completed" if process.returncode == 0 else "failed"
        job["return_code"] = process.returncode

        yield {
            "event": "complete",
            "status": job["status"],
            "return_code": process.returncode,
            "plot_path": params.plot_path,
        }


# Global service instance
negotiation_service = NegotiationService()
