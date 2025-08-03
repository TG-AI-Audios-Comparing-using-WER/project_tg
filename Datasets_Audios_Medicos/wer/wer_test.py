import os
import re
import json
from typing import Dict, Union
from jiwer import wer
import pandas as pd


def normalize_transcript(file_path: str) -> str:
    """
    Lê o arquivo de texto e faz algumas normalizações básicas:
    - Converte para minúsculo
    - Remove pontuação
    - Remove espaços extras
    Retorna a string normalizada.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    # Converte para minúsculo
    text = text.lower()
    # Remove pontuação (mantendo letras, dígitos e espaços)
    text = re.sub(r'[^\w\s]', '', text)
    # Remove espaços extras
    text = ' '.join(text.split())
    return text
def wer_test(t_real: str, t_ai: str) -> float:
    """
    Retorna o valor de WER entre duas strings.
    """
    return wer(t_real, t_ai)

def wer_results(manual_transcription_folder_path: str, ai_transcription_folder_path: str) -> Dict[str, Dict[str, float]]:
    """
    Calcula o WER para todos os arquivos que possuem o mesmo prefixo antes do primeiro '_'.
    Retorna um dicionário com o prefixo como chave e o WER como valor.
    """
    manual_transcription_list = os.listdir(manual_transcription_folder_path)
    ai_transcription_list = os.listdir(ai_transcription_folder_path)
    
    results = {}

    for manual_filename in manual_transcription_list:
        manual_prefix = manual_filename.split('_')[0]

        ai_filename = next(
            (f for f in ai_transcription_list if f.split('_')[0] == manual_prefix),
            None
        )

        if ai_filename is None:
            continue  # pula se não encontrar correspondente

        manual_path = os.path.join(manual_transcription_folder_path, manual_filename)
        ai_path = os.path.join(ai_transcription_folder_path, ai_filename)

        manual_text = normalize_transcript(manual_path)
        ai_text = normalize_transcript(ai_path)
        current_wer = wer_test(manual_text, ai_text)

        results[manual_prefix] = {"wer": current_wer}

    return results

def get_time_duration(json_folder_path: str) -> Dict[str, float]:
    """
    Retorna a duração do arquivo de áudio em segundos.
    """

    times = {}
    for item in os.listdir(json_folder_path):
        if item .endswith('.json'):
            file_path = os.path.join(json_folder_path, item)
            item_name = item.split('_')[0]


            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            duration = data['duracao']

            times[item_name] = duration
        else:
            # Se não for um arquivo JSON, ignora
            continue
    return times


if __name__ == "__main__":
    manual_transcription_folder_path = 'Datasets_Audios_Medicos/Transcriptions/manual_transcriptions'
    ai_transcription_folder_path_list = [
        'Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_aws',
        'Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_azure',
        'Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gcp',
        'Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gemini',
        'Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gpt4o'
    ]
    ai_labels = ['AWS', 'Azure', 'GCP', 'Gemini', 'GPT4o']

    # Inicializa DataFrame
    final_results = {}

    for folder, label in zip(ai_transcription_folder_path_list, ai_labels):
        ai_wer = wer_results(manual_transcription_folder_path, folder)
        for audio_name, wer_value in ai_wer.items():
            if audio_name not in final_results:
                final_results[audio_name] = {}
            final_results[audio_name][label] = f"{round(wer_value['wer'] * 100, 2)}%"

    # Pega duração de cada áudio
    durations = get_time_duration('Datasets_Audios_Medicos\Transcriptions\json')

    for audio_name, duration in durations.items():
        if audio_name in final_results:
            final_results[audio_name]["Duração (s)"] = round(duration, 2)

    # Converte pra DataFrame
    df = pd.DataFrame.from_dict(final_results, orient='index')
    df.index.name = "ID Áudio"
    df = df.reset_index()

    # Mostra no terminal
    print("\n Resultados de WER por motor de IA:\n")
    print(df)

    # Exporta para Excel
    df.to_excel("resultados_wer.xlsx", index=False)
    print("\n Arquivo 'resultados_wer.xlsx' salvo com sucesso")

        # ============================
    # Cálculo de Média Ponderada
    # ============================
    ponderadas = []

    for model in ai_labels:
        soma_ponderada = 0
        soma_tempos = 0

        for _, row in df.iterrows():
            tempo = row.get("Duração (s)")
            wer_str = row.get(model)

            if pd.isna(tempo) or pd.isna(wer_str):
                continue

            try:
                wer_val = float(wer_str.replace('%', ''))
            except:
                continue

            soma_ponderada += wer_val * tempo
            soma_tempos += tempo

        media = soma_ponderada / soma_tempos if soma_tempos else None
        ponderadas.append({
            "Modelo": model,
            "Média WER Ponderada (%)": round(media, 2) if media is not None else "N/A"
        })

    df_ponderada = pd.DataFrame(ponderadas)

    # Mostra no terminal
    print("\nMédia ponderada de WER por modelo (peso = tempo de áudio):\n")
    print(df_ponderada)

    # ============================
    # Salva ambas as tabelas no Excel
    # ============================
    with pd.ExcelWriter("resultados_wer.xlsx", engine='openpyxl', mode='w') as writer:
        df.to_excel(writer, sheet_name="WER por Áudio", index=False)
        df_ponderada.to_excel(writer, sheet_name="Média Ponderada", index=False)

    print("\n✅ Arquivo 'resultados_wer.xlsx' atualizado com a aba 'Média Ponderada'.")