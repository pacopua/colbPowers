import logging
import time
import requests

from .transcriber_config import SERVICE_REGION, SUBSCRIPTION_KEY
from .job_csv_manager import read_jobs_csv, update_job_in_csv, write_jobs_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


def get_transcription_status(transcription_id, max_retries=3, backoff_secs=5):
    """
    Devuelve el JSON con el estado de la transcripción (status, etc.) desde Azure.
    Incluye reintentos para mitigar errores de red.
    """
    region = SERVICE_REGION
    subscription_key = SUBSCRIPTION_KEY

    url = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.2/transcriptions/{transcription_id}"
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}

    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(url, headers=headers,
            timeout=None
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.exception(f"Error al consultar el estado del job {transcription_id}")
            attempt += 1
            time.sleep(backoff_secs * attempt)

    logging.error(f"No se pudo obtener el estado del job {transcription_id} tras {max_retries} reintentos.")
    return None


def monitor_transcription_status(transcription_id, poll_interval=2):
    """
    Monitorea el estado de un job hasta que finalice o falle.
    Si el job ya está finalizado en el CSV, se salta la consulta.
    Actualiza el CSV en cada ciclo, para que sea retomable.
    """
    while True:
        # Si en el CSV ya está marcado como final, se retorna sin llamar a la API
        finalizado = check_if_job_final_in_csv(transcription_id)
        if finalizado is not None:
            return finalizado  # True=Succeeded, False=Failed

        data = get_transcription_status(transcription_id)
        if not data:
            # No pudimos obtener estado
            return False

        status = data.get("status", "Unknown")
        logging.info(f"Estado actual del job {transcription_id}: {status}")

        # Actualizar en CSV
        update_job_in_csv(transcription_id, "", status)  # No sobreescribimos audio_url si ya existe
        if status == "Succeeded":
            logging.info("La transcripción se completó con éxito.")
            return True
        elif status in ("Failed", "FailedInternal"):
            logging.error("La transcripción ha fallado.")
            return False

        time.sleep(poll_interval)


def check_if_job_final_in_csv(transcription_id):
    """
    Verifica en el CSV si un job ya está en estado final (Succeeded o Failed).
    - Retorna True si 'Succeeded'
    - Retorna False si 'Failed'
    - Retorna None si no está finalizado
    """
    jobs = read_jobs_csv()
    if transcription_id in jobs:
        status = jobs[transcription_id]["status"]
        if status == "Succeeded":
            logging.info(f"Job {transcription_id} ya está en 'Succeeded' (CSV).")
            return True
        elif status == "Failed":
            logging.info(f"Job {transcription_id} ya está en 'Failed' (CSV).")
            return False
    return None
