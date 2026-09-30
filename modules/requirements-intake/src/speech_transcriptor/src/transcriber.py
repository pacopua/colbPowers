# transcriber.py
import logging
import os
import time
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from .blob_utils import upload_file_to_blob
from .create_transcription_job import create_transcription_job
from .get_transcription_results import download_file, get_transcription_results
from .job_csv_manager import read_jobs_csv, update_job_status
from .monitor_transcription_status import monitor_transcription_status
from .process_transcription import process_all_transcriptions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


def get_recording_name(audio_url: str) -> str:
    """
    Extrae el nombre base (sin extensión) de la URL de un audio.

    Args:
        audio_url (str): URL del archivo de audio.

    Returns:
        str: Nombre base del archivo de audio.
    """
    path = urlparse(audio_url).path
    base_name = os.path.basename(path)
    recording_name, _ = os.path.splitext(base_name)
    return recording_name


def transcribe(audio_url: str, job_id: str) -> str:
    """Maneja el proceso completo de transcripción para una URL de audio dada y un job_id.
    Retorna el nombre del blob final (JSON preprocesado) o None si falla.

    Args:
        audio_url (str): URL del archivo de audio en Azure Blob Storage.
        job_id (str): Identificador único del trabajo en CSV.

    Returns:
        str: Nombre del blob final preprocesado o None.
    """
    logging.info("Iniciando el proceso de transcripción...")

    final_blob_name = None
    recording_name = get_recording_name(audio_url)
    logging.info(f"Nombre de la grabación: {recording_name}")

    # 1. Crear (o reutilizar) el job de transcripción
    # Ensure file is fully available - wait a bit after upload before starting job
    time.sleep(10)
    transcription_id = create_transcription_job(audio_url, job_id)
    if not transcription_id:
        logging.error("No se pudo iniciar el job de transcripción.")
        return None

    logging.info(f"Transcription iniciado con ID: {transcription_id}")

    # 2. Monitorear hasta que finalice o falle
    success = monitor_transcription_status(transcription_id, job_id, poll_interval=2)
    if not success:
        logging.error("El job de transcripción falló o excedió el tiempo de espera.")
        return None
    logging.info("Transcripción completada con éxito.")

    # 3. Obtener y descargar los resultados
    results = get_transcription_results(transcription_id)
    if not results:
        logging.error("No se encontraron resultados de transcripción.")
        return None

    # 4. Procesar los resultados de la transcripción
    with TemporaryDirectory() as temp_dir:
        url = results[0]
        raw_blob_name = f"raw_transcription_{recording_name}.json"
        raw_file_path = os.path.join(temp_dir, "raw_transcription.json")

        # 4a. Descargar el archivo de transcripción crudo
        if not download_file(url, raw_file_path):
            logging.error(f"No se pudo descargar el archivo de transcripción desde {url}.")
            update_job_status(job_id, "transcription_status", "Failed")
            return None
        logging.info(f"Archivo de transcripción crudo descargado: {raw_file_path}")

        # 4b. Subir el archivo crudo a Azure Blob Storage
        try:
            upload_file_to_blob(
                file_path=raw_file_path,
                blob_name=raw_blob_name,
                folder_path="transcriptions/raw",
            )
            logging.info(f"Transcripción cruda subida como '{raw_blob_name}'.")
        except Exception as e:
            logging.exception(f"Error al subir la transcripción cruda '{raw_blob_name}': {e!s}")
            update_job_status(job_id, "transcription_status", "Failed")
            return None

        # 4c. Procesar la transcripción
        process_all_transcriptions(temp_dir, temp_dir)
        update_job_status(job_id, "processing_status", "Processed")

        # 4d. Subir la transcripción preprocesada
        for f in os.listdir(temp_dir):
            if f.startswith("preprocessed_") and f.endswith(".json"):
                preprocessed_file_path = os.path.join(temp_dir, f)
                preprocessed_blob_name = f"transcription_{recording_name}.json"
                preprocessed_renamed_path = os.path.join(temp_dir, preprocessed_blob_name)

                # Renombrar localmente
                os.rename(preprocessed_file_path, preprocessed_renamed_path)

                # Subir a la carpeta "transcriptions/preprocessed"
                try:
                    upload_file_to_blob(
                        file_path=preprocessed_renamed_path,
                        blob_name=preprocessed_blob_name,
                        folder_path="transcriptions/preprocessed",
                    )
                    logging.info(f"Transcripción preprocesada subida como '{preprocessed_blob_name}'.")
                    final_blob_name = preprocessed_blob_name
                except Exception as e:
                    logging.exception(f"Error al subir la transcripción preprocesada '{preprocessed_blob_name}': {e!s}")
                    update_job_status(job_id, "processing_status", "Failed")
                    return None

    if final_blob_name:
        logging.info("Proceso de transcripción completado con éxito.")
        update_job_status(job_id, "acta_status", "Ready for Acta Generation")
    else:
        logging.warning("No se encontró ningún archivo JSON preprocesado; retornando None.")

    return final_blob_name


if __name__ == "__main__":
    # Ejemplo de uso
    test_audio_url = "https://transcripcionespepi.blob.core.windows.net/pepi-batch-transcript-container/some_audio.mp3"
    test_job_id = "test-job-1234"  # Este debería ser un UUID generado
    blob_name = transcribe(test_audio_url, test_job_id)
    if blob_name:
        logging.info(f"Nombre final del blob preprocesado: {blob_name}")
    else:
        logging.error("La transcripción falló o no se generó ningún archivo preprocesado.")
