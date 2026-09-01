import asyncio
from pathlib import Path

from app.services.stt.elevenlabs import ElevenLabsSTTService


async def main():
    audio_path = Path("tests/sample.wav")

    audio_data = audio_path.read_bytes()

    stt = ElevenLabsSTTService()

    text = await stt.transcribe(
        audio_data=audio_data,
        mime_type="audio/wav",
    )

    print("\nTRANSCRIPTION:")
    print(text)


if __name__ == "__main__":
    asyncio.run(main())