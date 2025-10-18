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

for audios in os.listdir(datasets_path):
    item_path = os.path.join(datasets_path, audios)
    
    # Verifica se existe um arquivo de áudio com uma das extensões permitidas pela api
    audio_found = False
    for ext in audio_input_formats:
        if os.path.exists(item_path):
            audio_files.append(item_path)
            audio_found = True
            # print(f"Arquivo de áudio encontrado: {item_path}")
            break  # Para de procurar outras extensões para esta consulta
    
    if not audio_found:
        print(f"Não possuem arquivos de áudio compatíveis para essa consulta: {audios}")

for audio_file_path in audio_files:

    # Caminho completo para salvar o arquivo de transcrição
    output_file_path = os.path.join(f"{project_root}/project_tg/Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gpt4o/{os.path.basename(audio_file_path[:-4])}{audio_extension_file}")

    if os.path.exists(output_file_path):
        print(f"Transcrição já existe para o arquivo: {audio_file_path}")
        pass

    
    else:
        with open(audio_file_path, 'rb') as audio_reader:
            encoded_string = base64.b64encode(audio_reader.read()).decode('utf-8')

        file_extension = os.path.splitext(audio_file_path)[1].lstrip('.')

        # Realizar as requisições na API do Chat Completions
        completion = client.chat.completions.create(
            model=model_name,
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
                            "text": ''' Por favor, transcreva o conteúdo completo do áudio que será enviado a seguir. Transcreva o que ouve, preservando pontuação, ortografia e expressões tal como foram ditas. Além disso, insira no início de cada nova frase a marcação de tempo no formato [MM:SS] indicando o momento aproximado em que a frase começou. Transcreva **exatamente** o que foi dito, sem resumir, sem interpretar, sem nenhuma mensagem introdutória.'''
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