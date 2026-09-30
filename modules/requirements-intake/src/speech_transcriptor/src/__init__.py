import logging
import os

from dotenv import load_dotenv

#from colbai_utils.azure_keyvalut import get_secrets

load_dotenv()
#kv_name = os.getenv("KEY_VAULT_NAME", "kv-prosolvers-dev")

SUBSCRIPTION_KEY = (
    os.getenv("SPEECH_SUBSCRIPTION_KEY") or os.getenv("SUBSCRIPTION_KEY")
    if (os.getenv("SPEECH_SUBSCRIPTION_KEY") or os.getenv("SUBSCRIPTION_KEY"))
    else get_secrets(["speech-subscription-key"], kv_name)[0]
)
SERVICE_REGION = (
    os.getenv("SERVICE_REGION")
    if os.getenv("SERVICE_REGION")
    else get_secrets(["service-region"], kv_name)[0]
)
