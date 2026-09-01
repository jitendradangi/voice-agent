from typing import Any

from app.services.stt.elevenlabs import ElevenLabsSTTService


class VoiceService:

    def __init__(
        self,
        stt_service: ElevenLabsSTTService,
        agent: Any,
    ):
        self.stt_service = stt_service
        self.agent = agent

    async def process_audio(
        self,
        audio_data: bytes,
        mime_type: str,
    ) -> str:

        transcript = await self.stt_service.transcribe(
            audio_data=audio_data,
            mime_type=mime_type,
        )

        if not transcript.strip():
            return "I couldn't understand the audio."

        response = await self.agent.run(
            message=transcript
        )

        return response