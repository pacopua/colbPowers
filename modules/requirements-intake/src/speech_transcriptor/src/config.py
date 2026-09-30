"""Configuration for speech transcription."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptionConfig:
    """Configuration for Azure Speech Service transcription.
    
    Attributes:
        subscription_key: Azure Speech Service subscription key
        region: Azure region (e.g., 'eastus', 'westeurope')
        language: Language code for transcription (e.g., 'en-US', 'es-ES')
        output_format: Output format ('simple' or 'detailed')
    """
    subscription_key: str
    region: str
    language: str = "es-ES"
    output_format: str = "simple"
    diarization_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> "TranscriptionConfig":
        """Create configuration from environment variables.
        
        Expected environment variables:
        - AZURE_SPEECH_KEY: Subscription key
        - AZURE_SPEECH_REGION: Service region
        - AZURE_SPEECH_LANGUAGE (optional): Language code
        
        Returns:
            TranscriptionConfig instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        import os
        
        subscription_key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")
        language = os.getenv("AZURE_SPEECH_LANGUAGE", "es-ES")
        
        if not subscription_key:
            raise ValueError("AZURE_SPEECH_KEY environment variable is required")
        if not region:
            raise ValueError("AZURE_SPEECH_REGION environment variable is required")
            
        return cls(
            subscription_key=subscription_key,
            region=region,
            language=language
        )
