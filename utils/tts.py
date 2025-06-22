import os
import edge_tts
from pydub import AudioSegment

async def text_to_mp3(text: str, file_path: str) -> str:
    tts = edge_tts.Communicate(text, voice="tr-TR-AhmetNeural")
    await tts.save(file_path)
    audio = AudioSegment.from_mp3(file_path)
    audio = audio.set_frame_rate(44100).set_channels(2)
    audio.export(file_path, format="mp3", bitrate="192k")
    return os.path.abspath(file_path)
