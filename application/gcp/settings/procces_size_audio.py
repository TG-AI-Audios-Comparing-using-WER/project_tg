import os

from .audio_settings import *
from pydub import AudioSegment

def split_audio(input_file, segment_duration_ms=300000):  # 5 minutos em milissegundos
    """Divide um arquivo de áudio em segmentos."""
    audio = AudioSegment.from_file(input_file)
    total_duration_ms = len(audio)
    segments = []
    start_ms = 0
    while start_ms < total_duration_ms:
        end_ms = min(start_ms + segment_duration_ms, total_duration_ms)
        segment = audio[start_ms:end_ms]
        segments.append(segment)
        start_ms = end_ms
    return segments

def process_large_audio(input_file, output_dir):
    """Processa arquivos de áudio grandes dividindo-os em segmentos."""
    segments = split_audio(input_file)
    transcriptions = []
    for i, segment in enumerate(segments):
        segment_file = os.path.join(output_dir, f"segment_{i}.wav")
        segment.export(segment_file, format="wav")
        transcription = transcribe_audio(segment_file, speech.RecognitionConfig.AudioEncoding.LINEAR16, get_wav_sample_rate(segment_file))
        transcriptions.append(transcription)
        os.remove(segment_file) #remove os arquivos temporarios.
    return " ".join(transcriptions)