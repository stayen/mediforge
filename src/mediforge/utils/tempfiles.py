"""Temporary file and directory management."""

import shutil
import tempfile
import uuid
from pathlib import Path


class TempDirectory:
    """
    Managed temporary directory with conditional cleanup.

    Usage:
        with TempDirectory(keep=False) as path:
            # Use path for intermediate files
            ...
        # Directory is deleted unless keep=True or error occurred
    """

    def __init__(
        self,
        keep: bool = False,
        prefix: str = "mediforge-",
        base_dir: Path | None = None,
    ):
        self.keep = keep
        self.prefix = prefix
        self.base_dir = base_dir
        self.path: Path | None = None
        self._error_occurred = False

    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(
            prefix=self.prefix,
            dir=self.base_dir,
        ))
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._error_occurred = True

        if self.path and self.path.exists():
            if self.keep or self._error_occurred:
                # Log instead of print - caller handles user output
                pass
            else:
                shutil.rmtree(self.path)

        return False  # Don't suppress exceptions

    def create_subdir(self, name: str) -> Path:
        """Create a subdirectory within the temp directory."""
        if self.path is None:
            raise RuntimeError("TempDirectory not entered")
        subdir = self.path / name
        subdir.mkdir(exist_ok=True)
        return subdir

    def get_preserved_path(self) -> Path | None:
        """Get path if it was preserved (for error reporting)."""
        if self.path and self.path.exists() and (self.keep or self._error_occurred):
            return self.path
        return None


def generate_temp_filename(prefix: str, suffix: str) -> str:
    """Generate a unique temporary filename."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
