from cgitb import text
from email import message
import os
import base64
import json

from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
      
load_dotenv()

def load_models_config():
    config_path = Path(__file__).parent.parent / "model" / "models_api.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Definindo variáveis
endpoint = os.getenv("ENDPOINT_URL")
deployment = os.getenv("DEPLOYMENT_NAME")
api_key = os.getenv("OPENAI_API_KEY")


models_config = load_models_config()
gpt_config = models_config.get("gpt", {})
model_name = gpt_config.get("model_name", "")
audio_extension_file = gpt_config.get("audio_extension_file", "")
audio_input_formats = gpt_config.get("audio_input_format", [])

# Initialize Azure OpenAI client with Entra ID authentication

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version="2025-01-01-preview",
)

# Definir caminhos
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# Caminho dos Datasets
datasets_path =  os.path.join(project_root, 'project_tg/Datasets_Audios_Medicos/Audios')

# Listas para armazenar os caminhos dos arquivos
audio_files = []
ai_files = []

for audios in os.listdir(datasets_path):
    item_path = os.path.join(datasets_path, audios)
    
    # Verifica se existe um arquivo de áudio com uma das extensões permitidas pela api
    audio_found = False
    for ext in audio_input_formats:
        if os.path.exists(item_path):
            ai_file_path = os.path.join(item_path, f"{audios}{audio_extension_file}")
            audio_files.append(item_path)
            ai_files.append(ai_file_path)
            audio_found = True
            print(f"Arquivo de áudio encontrado: {item_path}")
            break  # Para de procurar outras extensões para esta consulta
    
    if not audio_found:
        print(f"Não possuem arquivos de áudio compatíveis para essa consulta: {audios}")

for audio_file_path, ai_file_path in zip(audio_files, ai_files):

    print(ai_file_path)
    # Caminho completo para salvar o arquivo de transcrição
    output_file_path = os.path.join(project_root, 'project_tg/Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gpt4o', os.path.basename(ai_file_path))


    if os.path.exists(f'{output_file_path}/{os.path.basename(ai_file_path)}'):
        print(f"Transcrição já existe para o arquivo: {audio_file_path}")

    with open(audio_file_path, 'rb') as audio_reader:
        encoded_string = base64.b64encode(audio_reader.read()).decode('utf-8')

    file_extension = os.path.splitext(audio_file_path)[1].lstrip('.')


    # Realizar as requisições na API do Chat Completions

    completion = client.chat.completions.create(
        model=model_name,
        modalities=['text', 'audio'],
        audio={
            "voice": "alloy", 
            "format": file_extension
        },
        messages=[
            {
                "role": "user",
                "content":[
                    {
                        "type": "text",
                        "text": "Transcreva detalhadamente todo o áudio falado em português. O áudio consiste em diversas frases ditas no dia dia, videos e diversos e você deve transcrever cada palavra, frase e sentença dita pelas pessas na conversa. Se alguém formar um número com 54 ou 2, escreva-o por extenso como 'cinquenta e quatro' e 'dois' ."
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": encoded_string,
                            "format": file_extension
                        }
                    }
                ]
            }
        ]
    )
    
    transcription = completion.choices[0].message.audio.transcript

    # Escreve a transcrição no arquivo, garantindo a classificação UTF-8
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(transcription)

    print(f"Transcription saved to: {output_file_path}")