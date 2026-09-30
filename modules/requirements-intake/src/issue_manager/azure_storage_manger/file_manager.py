"""
storage_manager.manager
-----------------------
Gestor de archivos de alto nivel que usa un backend inyectado.
Operaciones mínimas: listar, crear carpeta, subir, borrar, leer.
"""
from __future__ import annotations

import logging
from .backends.base import StorageBackend

logger = logging.getLogger("storage_manager")


class FileManager:
    def __init__(self, backend: StorageBackend):
        self._b = backend

    # -------- Listar / crear / subir / borrar --------
    def listdir(self, path: str) -> list[str]:
        logger.debug("listdir(%s)", path)
        return self._b.listdir(path)

    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        logger.info("makedirs(%s, exist_ok=%s)", path, exist_ok)
        self._b.makedirs(path, exist_ok=exist_ok)

    def upload(self, local_path: str, remote_path: str) -> None:
        logger.info("upload(%s -> %s)", local_path, remote_path)
        self._b.upload(local_path, remote_path)

    def delete(self, path: str, recursive: bool = False) -> None:
        logger.info("delete(%s, recursive=%s)", path, recursive)
        self._b.delete(path, recursive=recursive)

    # --------------------- Leer -----------------------
    def read(self, path: str, *, as_text: bool = True, encoding: str = "utf-8") -> str | bytes:
        """
        Lee un archivo del backend.

        Args:
            path: Ruta remota relativa al "base_uri" del backend (p.ej. "carpeta/nota.txt").
            as_text: Si True, devuelve str decodificado con 'encoding'; si False, bytes.
            encoding: Codificación para decodificar cuando as_text=True.

        Returns:
            str | bytes: Contenido del archivo.

        Raises:
            NotImplementedError: Si el backend no implementa 'read'.
            FileNotFoundError / IOError: Errores de E/S propagados desde el backend.
        """
        logger.info("read(%s, as_text=%s, encoding=%s)", path, as_text, encoding)
        if not hasattr(self._b, "read"):
            raise NotImplementedError("El backend no implementa 'read(path)'.")
        data: bytes = self._b.read(path)  # type: ignore[attr-defined]
        return data.decode(encoding) if as_text else data

    def read_bytes(self, path: str) -> bytes:
        """
        Atajo para leer bytes de un archivo remoto.
        """
        logger.debug("read_bytes(%s)", path)
        return self.read(path, as_text=False)  # type: ignore[return-value]

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """
        Atajo para leer texto (str) de un archivo remoto con la codificación indicada.
        """
        logger.debug("read_text(%s, encoding=%s)", path, encoding)
        return self.read(path, as_text=True, encoding=encoding)  # type: ignore[return-value]
