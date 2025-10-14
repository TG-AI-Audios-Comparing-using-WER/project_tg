import os
import json
from textwrap import indent
import wave
from pydub import AudioSegment
from mutagen.mp3 import MP3
from google.cloud import speech_v1 as speech
from google.cloud import storage

from dotenv import load_dotenv

load_dotenv()
GCP_CLIENT_KEY = os.getenv("KEY_SPEECH_CLIENT")
BUCKET_NAME = os.getenv("BUCKET_NAME") 
PROJECT_ID = os.getenv("PROJECT_ID")   

# Definição dos clients
credentials_path = os.path.join(f"{os.path.dirname(__file__)}\keys\{GCP_CLIENT_KEY}.json")
with open(credentials_path, 'r') as f:
    credentials_info = json.load(f)
    
# Cliente Speech-to-Text
speech_client = speech.SpeechClient.from_service_account_file(credentials_path)
# Cliente Cloud Storage
storage_client = storage.Client.from_service_account_info(credentials_info)

def convert_to_mono(input_file, output_file):
    """Converte o áudio para mono."""
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_channels(1)
    audio.export(output_file, format='wav')
    print(f"Convertido para mono: {output_file}")
    return output_file

def get_audio_duration(file_path):
    """Obtém a duração do arquivo de áudio em segundos."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        # Verufica se o arquivo é mp3 para utilizar a biblitoteca "mutagen"
        if ext == ".mp3":
            return MP3(file_path).info.length
        
        # Se não for, utiliza a biblioteca "pydub"
        return len(AudioSegment.from_file(file_path)) / 1000.0
 # Converter de ms para segundos
    except Exception as e:
        print(f"Erro ao obter duração do arquivo {file_path}: {e}")
        return 0

def get_wav_sample_rate(file_path):
    """Obtém a taxa de amostragem de um arquivo WAV."""
    with wave.open(file_path, 'rb') as wav_file:
        return wav_file.getframerate()

def get_mp3_sample_rate(file_path):
    """Obtém a taxa de amostragem de um arquivo MP3 usando Mutagen."""
    try:
        audio_info = MP3(file_path).info
        return audio_info.sample_rate
    except Exception as e:
        print(f"Erro ao ler taxa de amostragem do MP3 com Mutagen: {e}")
        return None # Retorna None se falhar

def upload_audio_to_storage(audio_file_path):
    """Faz upload do arquivo de áudio para o Google Cloud Storage."""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_name = f"audio/{os.path.basename(audio_file_path)}"
        blob = bucket.blob(blob_name)
        
        print(f"📤 Fazendo upload para Storage: {blob_name}")
        blob.upload_from_filename(audio_file_path)
        
        # Retorna a URI do arquivo no Storage
        gcs_uri = f"gs://{BUCKET_NAME}/{blob_name}"
        print(f"✅ Upload concluído: {gcs_uri}")
        return gcs_uri
        
    except Exception as e:
        print(f"❌ Erro no upload para Storage: {e}")
        return None

def transcribe_audio_from_storage(gcs_uri, encoding, sample_rate):
    """Transcreve um arquivo de áudio do Google Cloud Storage."""
    try:
        audio = speech.RecognitionAudio(uri=gcs_uri)
        config = speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=sample_rate,
            model="latest_long", 
            language_code='pt-BR',
        )
        
        print(f"🎤 Iniciando transcrição do Storage...")
        operation = speech_client.long_running_recognize(config=config, audio=audio)
        
        print(f"⏳ Aguardando transcrição...")
        response = operation.result(timeout=300)  # 5 minutos timeout

        # Extrai texto consolidado
        transcription = " ".join(
            result.alternatives[0].transcript for result in response.results
        )

        print(f"✅ Transcrição concluída!")
        return transcription
        
    except Exception as e:
        print(f"❌ Erro na transcrição do Storage: {e}")
        return None

def transcribe_audio(audio_file, encoding, sample_rate):
    """Transcreve um arquivo de áudio usando a API Speech-to-Text (método direto para arquivos pequenos)."""
    try:
        with open(audio_file, 'rb') as audio:
            content = audio.read()
        
        # Verificar tamanho do arquivo (limite de 10MB)
        file_size_mb = len(content) / (1024 * 1024)
        print(f"📊 Tamanho do arquivo: {file_size_mb:.2f} MB")
        
        duration_sec = get_audio_duration(audio_file)
        if duration_sec > 60 or file_size_mb > 10:
            print(f"⚠️ Áudio longo ({duration_sec:.1f}s / {file_size_mb:.2f}MB). Usando Storage...")
            gcs_uri = upload_audio_to_storage(audio_file)
            if gcs_uri:
                return transcribe_audio_from_storage(gcs_uri, encoding, sample_rate)
            else:
                return None
        
        # Para arquivos pequenos, usar método direto
        audio_obj = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=sample_rate,
            model="latest_long", 
            language_code='pt-BR',
        )
        
        print(f"🎤 Transcrevendo arquivo pequeno diretamente...")
        response = speech_client.recognize(config=config, audio=audio_obj)

        transcription = " ".join(
            result.alternatives[0].transcript for result in response.results
        )
        
        print(f"✅ Transcrição concluída!")
        return transcription
        
    except Exception as e:
        print(f"❌ Erro na transcrição: {e}")
        return None

def process_audio(input_file, output_dir):
    """Processa o arquivo de áudio e retorna a transcrição."""
    file_name, file_ext = os.path.splitext(input_file)

    if file_ext == '.wav':
        # Usar o diretório de saída para arquivos mono temporários
        mono_file = os.path.join('settings/temp', f'{os.path.basename(file_name)}_mono.wav')
        if not os.path.exists(mono_file):
            print(f"Criando arquivo mono: {mono_file}")
            convert_to_mono(input_file, mono_file)
        sample_rate = get_wav_sample_rate(input_file)
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        return transcribe_audio(mono_file, encoding, sample_rate)
    elif file_ext == '.flac':
        encoding = speech.RecognitionConfig.AudioEncoding.FLAC
        sample_rate = AudioSegment.from_file(input_file).frame_rate
        return transcribe_audio(input_file, encoding, sample_rate)
    elif file_ext == '.mp3':
        print("Entrei aqui quando o arquivo é mp3")
        encoding = speech.RecognitionConfig.AudioEncoding.MP3
        sample_rate = get_mp3_sample_rate(input_file)
        print("Sample rate do arquivo:", file_name, "-->",sample_rate)
        return transcribe_audio(input_file, encoding, sample_rate)
    elif file_ext == '.ogg':
        encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS
        sample_rate = AudioSegment.from_file(input_file).frame_rate
        return transcribe_audio(input_file, encoding, sample_rate)
    else:
        return None
