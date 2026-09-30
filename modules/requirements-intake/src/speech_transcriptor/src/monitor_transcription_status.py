# monitor_transcription_status.py
import logging
from loguru import logger

import os
import time
from dotenv import load_dotenv
import requests


from .transcriber_config import SERVICE_REGION, SUBSCRIPTION_KEY

from .job_csv_manager import read_jobs_csv, update_job_status



def get_transcription_status(transcription_id: str, max_retries=3, backoff_secs=5) -> dict:
    """
    Obtiene el estado actual del job de transcripción desde Azure.

    Args:
        transcription_id (str): Identificador del job de transcripción.
        max_retries (int): Número máximo de reintentos en caso de fallo.
        backoff_secs (int): Segundos de espera entre reintentos.

    Returns:
        dict: JSON con el estado del job, o None en caso de fallo.
    """
    url = f"https://{SERVICE_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2/transcriptions/{transcription_id}"
    headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY}

    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error al consultar el estado del job {transcription_id}: {e}")
            attempt += 1
            time.sleep(backoff_secs * attempt)

    logger.error(f"No se pudo obtener el estado del job {transcription_id} tras {max_retries} reintentos.")
    return None


def monitor_transcription_status(transcription_id: str, job_id: str, poll_interval=30) -> bool:
    """
    Monitorea el estado de un job de transcripción hasta que finalice o falle.
    Actualiza el estado en CSV.

    Args:
        transcription_id (str): Identificador del job de transcripción.
        job_id (str): Identificador único del trabajo en CSV.
        poll_interval (int): Intervalo de tiempo en segundos entre consultas.

    Returns:
        bool: True si la transcripción se completó con éxito, False si falló.
    """
    while True:
        data = get_transcription_status(transcription_id)
        if not data:
            # No se pudo obtener el estado; marcar como fallido
            logger.error(f"No se puede leer el audio")
            update_job_status(job_id, "transcription_status", "Failed")
            return False

        status = data.get("status", "Unknown")
        logger.info(f"Estado actual del job {transcription_id}: {status} | {data}")


        logger.info(f"Job {job_id} - Transcription status: {status}")
        if status == "Succeeded":
            logger.info("La transcripción se completó con éxito.")
            update_job_status(job_id, "transcription_status", "Succeeded")
            return True
        elif status in ("Failed", "FailedInternal"):
            logger.error("El job de transcripción ha fallado.")
            update_job_status(job_id, "transcription_status", "Failed")
            return False

        # Si aún está en progreso, esperar y volver a consultar
        logger.info(f"El job {transcription_id} sigue en progreso. Próxima consulta en {poll_interval} segundos.")
        time.sleep(poll_interval)
