# get_transcription_results.py
import logging
import os
import requests
from dotenv import load_dotenv


from .transcriber_config import SERVICE_REGION, SUBSCRIPTION_KEY



def get_transcription_results(transcription_id: str) -> list:
    """
    Recupera las URLs de los archivos de resultados de una transcripción completada.

    Args:
        transcription_id (str): Identificador del job de transcripción.

    Returns:
        list: Lista de URLs de contenido de los archivos de transcripción.
    """
    url = f"https://{SERVICE_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2/transcriptions/{transcription_id}/files"
    headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        files_info = response.json().get("values", [])
        
        transcription_urls = []
        for file in files_info:
            if file.get("kind") == "Transcription" and "contentUrl" in file.get("links", {}):
                transcription_urls.append(file["links"]["contentUrl"])
                
        return transcription_urls
    except requests.exceptions.RequestException as e:
        logging.exception(f"Error al obtener los resultados de la transcripción {transcription_id}: {e}")
        return []


def download_file(url: str, destination: str) -> bool:
    """
    Descarga un archivo desde una URL y lo guarda localmente.

    Args:
        url (str): URL del archivo a descargar.
        destination (str): Ruta local donde se guardará el archivo.

    Returns:
        bool: True si la descarga fue exitosa, False en caso contrario.
    """
    try:
        # Timeout set to 300s (5 min) for large JSON files
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logging.info(f"Archivo descargado: {destination}")
        return True
    except requests.exceptions.RequestException as e:
        logging.exception(f"Error al descargar el archivo desde {url}: {e}")
        return False
    except Exception as e:
        logging.exception(f"Error al guardar el archivo en {destination}: {e}")
        return False
