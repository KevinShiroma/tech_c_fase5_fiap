import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger("bot_sdr")

def converter_para_wav(audio_input_path: str) -> str:
    """Converte áudio do Telegram (.oga/.ogg) para WAV PCM 16kHz mono aceito perfeitamente pelo Azure Speech SDK."""
    import av
    import wave

    wav_path = audio_input_path + ".wav"
    container = av.open(audio_input_path)
    stream = container.streams.audio[0]
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    
    with wave.open(wav_path, 'wb') as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(16000)
        for frame in container.decode(stream):
            for resampled_frame in resampler.resample(frame):
                wav_out.writeframes(resampled_frame.to_ndarray().tobytes())
    return wav_path

async def transcrever_audio(audio_file_path: str) -> Optional[str]:
    """Voice AI: Transcreve notas de voz do Telegram utilizando o Azure Cognitive Services Speech."""
    load_dotenv(override=True)
    speech_key = os.getenv("AZURE_SPEECH_KEY", "").strip()
    speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus2").strip()

    if not speech_key:
        logger.warning("AZURE_SPEECH_KEY não configurada no .env.")
        return None

    wav_path = None
    try:
        # 1. Converte .oga/.ogg do Telegram para WAV 16kHz mono
        wav_path = converter_para_wav(audio_file_path)
        
        # 2. Transcreve com Azure Cognitive Services Speech SDK
        import azure.cognitiveservices.speech as speechsdk
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        speech_config.speech_recognition_language = "pt-BR"
        
        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        
        result = speech_recognizer.recognize_once_async().get()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.info(f"[Azure Speech SDK] Transcrição bem-sucedida: '{result.text}'")
            return result.text
        else:
            logger.warning(f"Azure Speech SDK não reconheceu a fala (Razão: {result.reason})")
            return None
    except Exception as e:
        logger.error(f"Erro ao transcrever com Azure Speech: {e}")
        return None
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
