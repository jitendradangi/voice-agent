import logging
from typing import Any

from elevenlabs.client import ElevenLabs

from app.core.config import settings
from app.services.stt.base import BaseSTTService

logger = logging.getLogger(__name__)


class ElevenLabsSTTService(BaseSTTService):

    def __init__(self):
        api_key = settings.ELEVENLABS_API_KEY

        if not api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY is not configured."
            )

        self.client = ElevenLabs(
            api_key=api_key
        )

    async def transcribe(
        self,
        audio_data: bytes,
        mime_type: str,
    ) -> str:

        try:
            response = self.client.speech_to_text.convert(
                file=audio_data,
                model_id="scribe_v2",
            )

            text = getattr(response, "text", None)

            if not text:
                raise ValueError(
                    "ElevenLabs returned an empty transcription."
                )

            return text.strip()

        except Exception as e:
            logger.error(
                "ElevenLabs STT failed: %s",
                e,
                exc_info=True,
            )
            raise