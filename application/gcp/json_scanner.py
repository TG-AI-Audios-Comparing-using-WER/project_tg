import os
import json

def read_json_files(json_path):
    '''
    Function to read json file from gcp speech-to-text and transform into a txt file
    '''

    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return data

def get_filename(datasets_path):
    ai_files = []
    for dataset in os.listdir(datasets_path):
        item_path = os.path.join(datasets_path, dataset)
        # Verifica se 'item' é uma pasta
        if os.path.isdir(item_path):
            # Filtra apenas os arquivos de áudio com extensão .wav ou .mp3
            audio_files = [file for file in os.listdir(item_path) if file.endswith('.wav') or file.endswith('.mp3')]
            
            # Se houver pelo menos um arquivo de áudio, processa os arquivos JSON
            if audio_files:                
                # Caminho para o arquivo de saída
                output_file_path = os.path.join(datasets_path, dataset, f"{dataset}_google_stt.txt")
                
                ai_files.append(output_file_path)
                
    return ai_files     

# Obter o diretório atual do script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Subir até o diretório raiz do projeto
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

dataset_json = os.path.join(project_root, 'project_tg/Datasets_Audios_Medicos/Transcriptions/json')
datasets_path = os.path.join(project_root, 'project_tg/Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gcp')

output_files = get_filename(datasets_path)

for json_file, ai_file in zip(os.listdir(dataset_json), output_files):

    json_path = os.path.join(dataset_json, json_file)

    # Verifica se o arquivo de transcrição já existe
    if os.path.exists(ai_file):
        print(f"O arquivo: {ai_file} ja existe para a transcrição: {json_path}")
        continue  # Pula para o próximo arquivo de áudio

    transcription = read_json_files(json_path)
    if transcription:
        with open(ai_file, 'w', encoding='utf-8') as file:
            file.write(transcription)
        print(f"O arquivo: {ai_file} foi gerado para a transcrição: {json_path}")
    else:
        print(f'Formato de arquivo não suportado: {ai_file}')