import os
import json
import mimetypes
from dotenv import load_dotenv
from google import genai
from google.genai import types
from typing import Optional
from pathlib import Path

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Constants
CONFIG_PATH = Path("../model/models_api.json")
AUDIO_DIR = Path("../../Datasets_Audios_Medicos/Audios")
OUTPUT_DIR = Path("../../Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gemini")
MAX_INLINE_SIZE = 20 * 1024 * 1024  # 20 MB

def load_config() -> dict:
    """Load and return the configuration from JSON file."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_gemini_config() -> dict:
    """Extract and return Gemini-specific configuration."""
    config = load_config()
    return config["gemini"]

def initialize_gemini_client() -> genai.Client:
    """Initialize and return the Gemini client."""
    return genai.Client(api_key=API_KEY)

def get_file_extension(file_path: str) -> str:
    """Extract and return the lowercase file extension without the dot."""
    return os.path.splitext(file_path)[1][1:].lower()

def get_mime_type(file_path: str) -> Optional[str]:
    """Determine and return the MIME type for the given file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type

def process_audio(file_path: str, client: genai.Client, config: dict) -> str:
    """
    Process audio file and return transcription.
    
    Args:
        file_path: Path to the audio file
        client: Initialized Gemini client
        config: Gemini configuration dictionary
        
    Returns:
        str: Transcription text
    """
    extension = get_file_extension(file_path)
    if extension not in config["audio_input_format"]:
        raise ValueError(f"Extensão '.{extension}' não suportada. Formatos válidos: {config['audio_input_format']}")
    
    mime_type = get_mime_type(file_path)
    if not mime_type:
        raise ValueError(f"Não foi possível identificar o mime_type para a extensão '.{extension}'")

    print(f"Arquivo: {file_path}")
    print(f"Extensão detectada: {extension}")
    print(f"MIME type: {mime_type}")

    file_size = os.path.getsize(file_path)
    
    if file_size <= MAX_INLINE_SIZE:
        with open(file_path, 'rb') as f:
            audio_bytes = f.read()
        print("Enviando áudio inline...")
        response = client.models.generate_content(
            model=config["model_name"],
            contents=[
                '''Transcreva o áudio fornecido de forma clara e fiel ao conteúdo falado.
 
                Além disso, inclua *timestamps estruturados* para cada linha ou fragmento da transcrição. Os timestamps devem estar no formato `hh:mm:ss`, indicando com precisão o momento de início de cada trecho falado.
                
                A estrutura de saída deve ser a seguinte:
                
                [hh:mm:ss] Texto transcrito correspondente a este momento do áudio.
                
                Exemplo de estrutura desejada:
                [00:00:03] Olá, este é um exemplo de transcrição.
                [00:00:07] A cada nova fala ou frase, um novo timestamp deve ser adicionado.
                [00:00:12] Certifique-se de que os tempos estejam corretos e bem distribuídos ao longo do áudio.''',
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            ]
        )
    else:
        print("Fazendo upload do áudio via File API...")
        uploaded_file = client.files.upload(file=file_path)
        response = client.models.generate_content(
            model=config["model_name"],
            contents=[
                '''Transcreva o áudio fornecido de forma clara e fiel ao conteúdo falado.
 
                Além disso, inclua *timestamps estruturados* para cada linha ou fragmento da transcrição. Os timestamps devem estar no formato `hh:mm:ss`, indicando com precisão o momento de início de cada trecho falado.
                
                A estrutura de saída deve ser a seguinte:
                
                [hh:mm:ss] Texto transcrito correspondente a este momento do áudio.
                
                Exemplo de estrutura desejada:
                [00:00:03] Olá, este é um exemplo de transcrição.
                [00:00:07] A cada nova fala ou frase, um novo timestamp deve ser adicionado.
                [00:00:12] Certifique-se de que os tempos estejam corretos e bem distribuídos ao longo do áudio.''',
                uploaded_file
            ]
        )

    return response.text
    return "teste"

def save_transcription(file_path: Path, content: str) -> None:
    """Save transcription content to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """Main execution function."""
    gemini_config = get_gemini_config()
    client = initialize_gemini_client()
    
    processed_files = 0
    skipped_files = 0
    error_files = 0
    
    for filename in os.listdir(AUDIO_DIR):
        file_path = AUDIO_DIR / filename
        
        if not file_path.is_file():
            continue

        print(f"\nProcessando: {filename}")
        base_name = os.path.splitext(filename)[0]
        transcription_path = OUTPUT_DIR / f"{base_name}{gemini_config['audio_extension_file']}"

        if transcription_path.exists():
            print(f"Transcrição já existe para '{filename}', pulando...")
            skipped_files += 1
            continue

        try:
            result = process_audio(str(file_path), client, gemini_config)
            save_transcription(transcription_path, result)
            print(f"Transcrição salva com sucesso em: {transcription_path}")
            processed_files += 1
        except Exception as e:
            print(f"Erro ao processar '{filename}': {e}")
            error_files += 1

    print("\nResumo do processamento:")
    print(f"Arquivos processados com sucesso: {processed_files}")
    print(f"Arquivos pulados (já existentes): {skipped_files}")
    print(f"Arquivos com erro: {error_files}")
    print("\nProcessamento concluído! Todas as transcrições foram finalizadas.")

if __name__ == '__main__':
    main()
