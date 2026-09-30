
"""
storage_manager.backends.base
-----------------------------
Definiciones base para backends de almacenamiento.
"""
from __future__ import annotations
from typing import Protocol

class StorageError(Exception):
    """Error genérico de almacenamiento."""

class NotFoundError(StorageError):
    """Ruta/objeto no encontrado."""

class StorageBackend(Protocol):
    """
    Contrato mínimo para un backend de almacenamiento.
    Métodos: listar, crear carpeta, subir, borrar.
    """
    def listdir(self, path: str) -> list[str]:
        ...

    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        ...

    def upload(self, local_path: str, remote_path: str) -> None:
        ...

    def delete(self, path: str, recursive: bool = False) -> None:
        ...

    def read(self, path: str) -> bytes:
        ...
