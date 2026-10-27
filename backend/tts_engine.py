import os
import subprocess
import asyncio
import edge_tts
import re

VOICE_MAP = {
    "kannada": "kn-IN-GaganNeural",
    "hindi": "hi-IN-MadhurNeural",
    "english_in": "en-IN-PrabhatNeural",
    "english_us": "en-US-ChristopherNeural"
}

def detect_language(text: str) -> str:
    """Detects Kannada, Hindi, or English text ranges."""
    if re.search(r'[\u0C80-\u0CFF]', text):
        return VOICE_MAP["kannada"]
    elif re.search(r'[\u0900-\u097F]', text):
        return VOICE_MAP["hindi"]
    else:
        return VOICE_MAP["english_in"]

async def speak_text(text: str):
    """Generates audio with Edge-TTS and plays it natively via Windows PowerShell."""
    if not text or len(text.strip()) == 0:
        return

    voice = detect_language(text)
    output_file = os.path.abspath("temp_output.mp3").replace("\\", "/")

    try:
        communicate = edge_tts.Communicate(text, voice)
        await asyncio.wait_for(communicate.save(output_file), timeout=4.0)

        ps_cmd = (
            f"Add-Type -AssemblyName presentationCore; "
            f"$player = New-Object System.Windows.Media.MediaPlayer; "
            f"$player.Open('{output_file}'); "
            f"$player.Play(); "
            f"Start-Sleep -s 1; "
            f"while ($player.NaturalDuration.HasTimeSpan -and $player.Position -lt $player.NaturalDuration.TimeSpan) {{ Start-Sleep -m 100 }}"
        )

        # Offload blocking PowerShell playback execution to background thread executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, 
            lambda: subprocess.run(["powershell", "-c", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        )

        if os.path.exists(output_file):
            os.remove(output_file)

    except asyncio.TimeoutError:
        print("[TTS Warning]: Edge-TTS speech generation timed out.")
    except Exception as e:
        print(f"[TTS Error]: {str(e)}")
