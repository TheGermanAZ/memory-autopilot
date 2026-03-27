"""Generate TTS audio for all transcript lines via ElevenLabs API."""
import json
import os
import sys
from pathlib import Path

from elevenlabs import ElevenLabs

# Voice IDs — pick two distinct stock voices
CUSTOMER_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah (female)
AGENT_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel (male)

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "frontend" / "public" / "audio"


def generate_audio(client: ElevenLabs, text: str, voice_id: str, filename: str):
    output_path = OUTPUT_DIR / filename
    if output_path.exists():
        print(f"  Skipping {filename} (already exists)")
        return

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    print(f"  Generated {filename}")


def main():
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: Set ELEVENLABS_API_KEY environment variable")
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    transcript_files = [
        ROOT_DIR / "data" / "transcripts" / "call1.json",
        ROOT_DIR / "data" / "transcripts" / "call2_without_memory.json",
        ROOT_DIR / "data" / "transcripts" / "call2_with_memory.json",
    ]

    for tf in transcript_files:
        print(f"\nProcessing {tf}...")
        with open(tf) as f:
            data = json.load(f)

        for line in data["lines"]:
            voice_id = CUSTOMER_VOICE_ID if line["role"] == "customer" else AGENT_VOICE_ID
            generate_audio(client, line["text"], voice_id, line["audio"])

    print(f"\nDone! Audio files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
