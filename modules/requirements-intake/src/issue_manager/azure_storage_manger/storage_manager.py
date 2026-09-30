# storage_manager/client.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .file_manager import FileManager
from .backends.base import StorageBackend
from .backends.azure import AzureStorageBackend, AzureBackendConfig


class StorageManager:
    """
    Thin convenience wrapper over FileManager that anchors all operations under a base_uri.
    Public API matches your demo:
      - make_dirs(path)
      - upload_file(local_path, remote_path=None)
      - list_files()
      - delete_path(path, recursive=False)
      - read_text(path, encoding="utf-8")
      - read_bytes(path)
    """
    def __init__(self, backend: StorageBackend, base_uri: str):
        self._b: StorageBackend = backend
        self._fm = FileManager(backend)
        self.base_uri = base_uri.rstrip("/")

    # ------------- helpers -------------
    def _full(self, path: Optional[str]) -> str:
        """
        Compose an absolute remote path under the base_uri.
        Accepts None / "" / "." to mean the base itself.
        """
        if not path or path in (".", "/"):
            return self.base_uri
        # If caller already passed a fully qualified URL, keep it
        if "://" in path:
            return path
        return f"{self.base_uri}/{path.lstrip('/')}"

    # ------------- API (names as used by your demo) -------------
    def make_dirs(self, path: str) -> None:
        self._fm.makedirs(self._full(path), exist_ok=True)

    def upload_file(self, local_path: str, remote_path: Optional[str] = None) -> None:
        target = self._full(Path(local_path).name if not remote_path else remote_path)
        self._fm.upload(local_path, target)

    def list_files(self) -> list[str]:
        return self._fm.listdir(self._full(""))

    def list_path(self, path: str) -> list[str]:
        """List files/directories under a specific path."""
        return self._fm.listdir(self._full(path))

    def delete_path(self, path: str, recursive: bool = False) -> None:
        self._fm.delete(self._full(path), recursive=recursive)

    # New direct-read helpers (built on FileManager.read*)
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        return self._fm.read_text(self._full(path), encoding=encoding)

    def read_bytes(self, path: str) -> bytes:
        return self._fm.read_bytes(self._full(path))

    # Expose underlying filesystem if backends provide it (useful for advanced ops)
    @property
    def fs(self):
        return getattr(self._b, "fs", None)


def storage_manager(
    backend_name: str,
    *,
    protocol: str = "az",
    account_name: Optional[str] = None,
    credential: Optional[object] = None,
    connection_string: Optional[str] = None,
    base_uri: Optional[str] = None,
    create_parent_dirs: bool = True,
) -> StorageManager:
    """
    Factory that builds a StorageManager anchored at base_uri.
    Example:
        storage_manager(
            "Azure",
            protocol="az",
            account_name="myacct",
            connection_string="...",
            base_uri="az://my-container/some/prefix"
        )
    """
    if backend_name.lower() != "azure":
        raise ValueError("Only 'Azure' backend is supported in this factory.")

    if not base_uri:
        raise ValueError("base_uri is required (e.g. 'az://<container>/<prefix>').")

    cfg = AzureBackendConfig(
        protocol=protocol,
        account_name=account_name,
        credential=credential,
        connection_string=connection_string,
        create_parent_dirs=create_parent_dirs,
    )
    backend = AzureStorageBackend(cfg)
    return StorageManager(backend, base_uri=base_uri)