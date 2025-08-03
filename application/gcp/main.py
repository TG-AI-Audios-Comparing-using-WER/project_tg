
import os
import json

def read_json_files(json_path):
    '''
    Function to read json file from gcp speech-to-text and transform into a txt file
    '''
    # Inicializa uma string para armazenar todos os transcripts concatenados
    all_transcripts = ""

    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        results = data['results']

        # Identificando as Listas que compõem o arquivo
        for result in results:
            for transcript in result['alternatives']:
                all_transcripts += transcript['transcript'] + "\n"
    return all_transcripts

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

dataset_json = 'application/gcp/json'
datasets_path = 'Datasets_Audios_Medicos/Transcriptions/transcription_modelo/transcription_gcp'

output_files = get_filename(datasets_path)

print(dataset_json)
print(output_files)

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