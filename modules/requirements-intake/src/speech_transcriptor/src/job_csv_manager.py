# job_csv_manager.py
import csv
import logging
import os
import time
from typing import Dict

# Use absolute path based on this file's location
basedir = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(basedir, "jobs.csv")

FIELDNAMES = [
    "job_id",
    "transcription_id",
    "audio_url",
    "upload_status",
    "transcription_status",
    "processing_status",
    "acta_status",
    "docx_template_path",
    "last_update",
    "title",
    "acta_number",
]

LOCK_FILE = os.path.join(basedir, "jobs.csv.lock")


def ensure_data_folder_exists() -> None:
    """Verifica que la carpeta donde se ubica el CSV exista; si no, la crea."""
    folder = os.path.dirname(CSV_PATH)
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def ensure_csv_file_exists() -> None:
    """Verifica que el archivo CSV exista; de lo contrario, lo crea con la cabecera."""
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def acquire_lock(timeout=10, check_interval=0.1) -> bool:
    """Adquiere un bloqueo para acceder al archivo CSV.

    Args:
        timeout (int): Tiempo máximo en segundos para esperar el bloqueo.
        check_interval (float): Intervalo en segundos para verificar el bloqueo.

    Returns:
        bool: True si se adquirió el bloqueo, False si se agotó el tiempo.
    """
    ensure_data_folder_exists()
    start_time = time.time()
    while os.path.exists(LOCK_FILE):
        if time.time() - start_time > timeout:
            logging.error("Timeout al intentar adquirir el bloqueo para jobs.csv.")
            return False
        time.sleep(check_interval)
    try:
        with open(LOCK_FILE, "w") as f:
            f.write("lock")
        logging.info("Bloqueo adquirido para jobs.csv.")
        return True
    except Exception as e:
        logging.exception(f"Error al crear el lock file: {e}")
        return False


def release_lock() -> None:
    """Libera el bloqueo del archivo CSV."""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            logging.info("Bloqueo liberado para jobs.csv.")
        except Exception as e:
            logging.exception(f"Error al eliminar el lock file: {e}")


def read_jobs_csv() -> Dict[str, dict]:
    """Lee el archivo CSV y retorna un diccionario con la información de los trabajos indexados por job_id."""
    ensure_data_folder_exists()
    ensure_csv_file_exists()

    if not acquire_lock():
        logging.error("No se pudo adquirir el bloqueo para leer jobs.csv.")
        raise Exception("No se pudo adquirir el bloqueo para leer jobs.csv.")

    jobs = {}
    try:
        with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                job_id = row["job_id"]
                if job_id in jobs:
                    logging.warning(f"job_id duplicado encontrado: {job_id}. Ignorando esta entrada.")
                    continue  # Ignorar entradas duplicadas
                jobs[job_id] = row
        return jobs
    finally:
        release_lock()


def write_jobs_csv(jobs: Dict[str, dict]) -> None:
    """Escribe en el archivo CSV toda la información de los trabajos de manera atómica."""
    ensure_data_folder_exists()
    temp_path = CSV_PATH + ".tmp"
    if not acquire_lock():
        logging.error("No se pudo adquirir el bloqueo para escribir jobs.csv.")
        raise Exception("No se pudo adquirir el bloqueo para escribir jobs.csv.")

    try:
        with open(temp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for job_data in jobs.values():
                writer.writerow(job_data)
        os.replace(temp_path, CSV_PATH)  # Escritura atómica
        logging.info("jobs.csv actualizado de manera atómica.")
    except Exception as e:
        logging.exception(f"Error al escribir en jobs.csv: {e}")
        raise
    finally:
        release_lock()


def create_job_entry(job_id: str, audio_url: str, docx_template_path: str, acta_details: dict) -> None:
    """Crea una nueva entrada de trabajo en el CSV con los estados iniciales."""
    jobs = read_jobs_csv()
    if job_id in jobs:
        logging.error(f"Intento de crear un job_id ya existente: {job_id}.")
        raise ValueError(f"job_id {job_id} ya existe.")
    jobs[job_id] = {
        "job_id": job_id,
        "title": acta_details["titulo"],
        "acta_number": acta_details["numero_acta"],
        "transcription_id": "",
        "audio_url": audio_url,
        "upload_status": "Uploaded",
        "transcription_status": "Not Started",
        "processing_status": "Not Started",
        "acta_status": "Not Started",
        "docx_template_path": docx_template_path,
        "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_jobs_csv(jobs)
    logging.info(f"Creada entrada de trabajo con job_id: {job_id}")


def update_job_status(job_id: str, stage: str, status: str) -> None:
    """Actualiza el estado de una etapa específica para un trabajo dado."""
    jobs = read_jobs_csv()
    if job_id in jobs:
        jobs[job_id][stage] = status
        jobs[job_id]["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
        write_jobs_csv(jobs)
        logging.info(f"Actualizado estado '{stage}' a '{status}' para job_id: {job_id}")
    else:
        logging.error(f"Intento de actualizar job_id inexistente: {job_id}.")
        raise ValueError(f"Job ID {job_id} no encontrado en el CSV.")


def set_transcription_id(job_id: str, transcription_id: str) -> None:
    """Asigna el transcription_id a un trabajo."""
    jobs = read_jobs_csv()
    if job_id in jobs:
        jobs[job_id]["transcription_id"] = transcription_id
        jobs[job_id]["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
        write_jobs_csv(jobs)
        logging.info(f"Asignado transcription_id '{transcription_id}' a job_id: {job_id}")
    else:
        logging.error(f"Intento de asignar transcription_id a job_id inexistente: {job_id}.")
        raise ValueError(f"Job ID {job_id} no encontrado en el CSV.")


def delete_job_entry(job_id: str):
    """Elimina una entrada de trabajo del CSV basado en el job_id."""
    if not os.path.exists(CSV_PATH):
        logging.warning(f"Intento de eliminar job_id '{job_id}' pero el CSV no existe.")
        return

    jobs = read_jobs_csv()
    if job_id in jobs:
        del jobs[job_id]
        write_jobs_csv(jobs)
        logging.info(f"Eliminado job_id: {job_id}")
    else:
        logging.warning(f"Intento de eliminar job_id inexistente: {job_id}.")


def remove_duplicate_job_entries() -> None:
    """Detecta y elimina entradas duplicadas en el CSV basándose en 'job_id'.
    Solo conserva la primera aparición de cada 'job_id'.
    """
    jobs = read_jobs_csv()
    unique_jobs = {}
    duplicates = set()

    for job_id, job_data in jobs.items():
        if job_id not in unique_jobs:
            unique_jobs[job_id] = job_data
        else:
            duplicates.add(job_id)

    if duplicates:
        logging.warning(f"Se encontraron y eliminaron los siguientes job_ids duplicados: {', '.join(duplicates)}")
        write_jobs_csv(unique_jobs)
        print(f"Se eliminaron {len(duplicates)} entradas duplicadas en '{CSV_PATH}'.")
    else:
        logging.info("No se encontraron job_ids duplicados en el CSV.")
        print("No se encontraron job_ids duplicados en el CSV.")
