from abc import ABC, abstractmethod


class BaseSTTService(ABC):

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        mime_type: str,
    ) -> str:
        """
        Convert audio data into text.
        """
        pass