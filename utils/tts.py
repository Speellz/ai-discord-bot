import edge_tts
from pydub import AudioSegment
import os

async def metni_sese_cevir(metin: str, dosya_adi="cevap.mp3"):
    print("🔄 Edge TTS ile ses dönüştürülüyor...")
    tts = edge_tts.Communicate(metin, voice="tr-TR-AhmetNeural")
    await tts.save(dosya_adi)

    print("🎙 Ses dosyası optimize ediliyor...")
    audio = AudioSegment.from_mp3(dosya_adi)
    audio = audio.set_frame_rate(44100).set_channels(2)
    audio.export(dosya_adi, format="mp3", bitrate="192k")

    print(f"✅ Ses dosyası başarıyla oluşturuldu: {os.path.abspath(dosya_adi)}")
    return dosya_adi
