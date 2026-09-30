
"""
storage_manager.backends.azure
-------------------------------
Backend de Azure (Blob / ADLS Gen2) usando fsspec + adlfs.

Requisitos:
    pip install fsspec adlfs
    # Si autenticas con AAD:
    pip install azure-identity
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import logging

from .base import StorageBackend, StorageError, NotFoundError

logger = logging.getLogger("storage_manager.azure")

@dataclass(frozen=True)
class AzureBackendConfig:
    """
    Configuración del backend Azure.
    - protocol: 'az' (Blob) o 'abfs' (ADLS Gen2 con HNS)
    - account_name: nombre de la cuenta (sin sufijos .blob.core...)
    - credential: DefaultAzureCredential(), SAS string, account key, etc. (opcional)
    - connection_string: alternativa a account_name+credential (opcional)
    - create_parent_dirs: crear directorios/prefijos padre automáticamente
    """
    protocol: str                 # "az" o "abfs"
    account_name: Optional[str] = None
    credential: Optional[object] = None
    connection_string: Optional[str] = None
    create_parent_dirs: bool = True

class AzureStorageBackend(StorageBackend):
    """
    Implementación mínima con fsspec/adlfs.
    Opera sobre rutas 'az://<container>/path' o 'abfs://<fs>/path' según protocol.
    """
    def __init__(self, config: AzureBackendConfig):
        try:
            import fsspec  # type: ignore
        except Exception as e:
            raise StorageError("Se requiere 'fsspec' para AzureStorageBackend") from e

        self._fsspec = fsspec
        self.cfg = config
        if self.cfg.protocol not in {"az", "abfs"}:
            raise ValueError("protocol debe ser 'az' (Blob) o 'abfs' (ADLS Gen2)")

        try:
            self.fs = self._fsspec.filesystem(
                self.cfg.protocol,
                account_name=self.cfg.account_name,
                credential=self.cfg.credential,
                connection_string=self.cfg.connection_string,
            )
        except Exception as e:
            raise StorageError(f"No se pudo inicializar el filesystem Azure: {e}") from e

    # ----- utilidades internas -----
    def _ensure_parents(self, path: str) -> None:
        if not self.cfg.create_parent_dirs:
            return
        parent = self._parent_dir(path)
        if parent:
            try:
                self.fs.makedirs(parent, exist_ok=True)
            except Exception as e:
                logger.debug("makedirs no aplicable para %s: %s", parent, e)

    @staticmethod
    def _parent_dir(path: str) -> str:
        p = path.rstrip("/")
        if "://" not in p:
            # local (no debería usarse aquí)
            import os
            return os.path.dirname(p)
        scheme, rest = p.split("://", 1)
        if "/" not in rest:
            return f"{scheme}://{rest}"
        parent = rest.rsplit("/", 1)[0]
        return f"{scheme}://{parent}"

    # ----- implementación del contrato -----
    def listdir(self, path: str) -> list[str]:
        try:
            return list(self.fs.ls(path))
        except FileNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except Exception as e:
            raise StorageError(f"Error listando {path}: {e}") from e

    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        try:
            self.fs.makedirs(path, exist_ok=exist_ok)
        except Exception as e:
            raise StorageError(f"Error creando carpeta {path}: {e}") from e

    def upload(self, local_path: str, remote_path: str) -> None:
        try:
            self._ensure_parents(remote_path)
            self.fs.put(local_path, remote_path)
        except FileNotFoundError as e:
            # Check if it's actually the local file that is missing
            import os
            if not os.path.exists(local_path):
                raise NotFoundError(f"Local no encontrado: {local_path}") from e
            # Otherwise it might be a remote path issue (e.g. container not found)
            raise StorageError(f"Error subiendo a {remote_path} (posiblemente ruta remota inválida): {e}") from e
        except Exception as e:
            raise StorageError(f"Error subiendo a {remote_path}: {e}") from e

    def delete(self, path: str, recursive: bool = False) -> None:
        try:
            self.fs.rm(path, recursive=recursive)
        except FileNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except Exception as e:
            raise StorageError(f"Error borrando {path}: {e}") from e

    def read(self, path: str) -> bytes:
        try:
            with self.fs.open(path, "rb") as f:
                return f.read()
        except FileNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except Exception as e:
            raise StorageError(f"Error leyendo {path}: {e}") from e
