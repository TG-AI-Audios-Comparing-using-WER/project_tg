# Script com o objetivo de trazer informações sobre o dataset

import numpy
import os
from openai import project
import pandas as pd
import json
from typing import Dict, Union


def get_statistics(json_file_path: str, manual_transcription_file: str) -> Dict[str, Union[int, float]]:

    file_count = 0
    time_count = 0
    word_count = 0

    # Definir caminhos - partir da pasta wer atual
    current_dir = os.path.dirname(os.path.abspath(__file__))  # pasta wer
    parent_dir = os.path.dirname(current_dir)  # Datasets_Audios_Medicos
    
    # Construir caminhos completos
    json_folder_path = os.path.join(parent_dir, json_file_path)
    manual_folder_path = os.path.join(parent_dir, manual_transcription_file)

    # Verificar se os diretórios existem
    if not os.path.exists(json_folder_path):
        raise FileNotFoundError(f"Diretório não encontrado: {json_folder_path}")
    if not os.path.exists(manual_folder_path):
        raise FileNotFoundError(f"Diretório não encontrado: {manual_folder_path}")

    for json_file in os.listdir(json_folder_path):
        if json_file.endswith('.json'):
            file_count += 1
            with open(os.path.join(json_folder_path, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                time_count += data.get('duracao', 0)

    for transcription_file in os.listdir(manual_folder_path):
        if transcription_file.endswith('.txt'):
            with open(os.path.join(manual_folder_path, transcription_file), 'r', encoding='utf-8') as f:
                text = f.read()
                word_count += len(text.split())

    return {
        "file_count": file_count,
        "time_count": time_count,
        "word_count": word_count
    }


def write_statistics(statistics: dict) -> int:

    results_text = (
        "===== Informações do Dataset =====\n"
        f"Total de arquivos de áudio: {statistics.get('file_count')}\n"
        f"Tempo total (em minutos): {(statistics.get('time_count')/60):.2f}\n"
        f"Total de palavras: {statistics.get('word_count')}\n"
    )

    with open("info.txt", "w", encoding="utf-8") as output_file:
        output_file.write(results_text)

    return 0


if __name__ == "__main__":
    statistics = get_statistics('Transcriptions/json',
                                'Transcriptions/manual_transcriptions')
    write_statistics(statistics)
    print('Script rodou com sucesso')
