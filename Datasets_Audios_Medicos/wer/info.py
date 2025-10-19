# Script com o objetivo de trazer informações sobre o dataset

import numpy
import os
from openai import project
import pandas as pd
import json
from typing import Dict, Union


def get_statistics(json_file_path: str, manual_transcription_file: str) -> Dict[str, Union[int, float, list, dict]]:

    file_count = 0
    time_count = 0
    word_count = 0
    categories = set()
    sources = set()
    category_count = {}
    source_count = {}

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
                
                # Coletar informações sobre categorias e fontes
                categoria = data.get('categoria', 'Não especificada')
                fonte = data.get('fonte', 'Não especificada')
                
                categories.add(categoria)
                sources.add(fonte)
                
                # Contar ocorrências de cada categoria e fonte
                category_count[categoria] = category_count.get(categoria, 0) + 1
                source_count[fonte] = source_count.get(fonte, 0) + 1

    for transcription_file in os.listdir(manual_folder_path):
        if transcription_file.endswith('.txt'):
            with open(os.path.join(manual_folder_path, transcription_file), 'r', encoding='utf-8') as f:
                text = f.read()
                word_count += len(text.split())

    return {
        "file_count": file_count,
        "time_count": time_count,
        "word_count": word_count,
        "categories": sorted(list(categories)),
        "sources": sorted(list(sources)),
        "category_count": category_count,
        "source_count": source_count,
        "unique_categories": len(categories),
        "unique_sources": len(sources)
    }


def write_statistics(statistics: dict) -> int:

    # Criar seção de categorias
    categories_section = "\n===== Categorias Disponíveis =====\n"
    categories_section += f"Total de categorias únicas: {statistics.get('unique_categories')}\n"
    categories_section += "Categorias encontradas:\n"
    for categoria, count in sorted(statistics.get('category_count', {}).items()):
        categories_section += f"  - {categoria}: {count} arquivo(s)\n"
    
    # Criar seção de fontes
    sources_section = "\n===== Fontes de Áudio =====\n"
    sources_section += f"Total de fontes únicas: {statistics.get('unique_sources')}\n"
    sources_section += "Fontes encontradas:\n"
    for fonte, count in sorted(statistics.get('source_count', {}).items()):
        sources_section += f"  - {fonte}: {count} arquivo(s)\n"

    results_text = (
        "===== Informações do Dataset =====\n"
        f"Total de arquivos de áudio: {statistics.get('file_count')}\n"
        f"Tempo total (em minutos): {(statistics.get('time_count')/60):.2f}\n"
        f"Total de palavras: {statistics.get('word_count')}\n"
        f"{categories_section}"
        f"{sources_section}"
    )

    with open("info.txt", "w", encoding="utf-8") as output_file:
        output_file.write(results_text)

    return 0


if __name__ == "__main__":
    statistics = get_statistics('Transcriptions/json',
                                'Transcriptions/manual_transcriptions')
    write_statistics(statistics)
    print('Script rodou com sucesso')
