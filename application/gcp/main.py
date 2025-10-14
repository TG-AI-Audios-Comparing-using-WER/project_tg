import os
import json
import time
from datetime import datetime
from pathlib import Path

from google.auth.crypt import base
from settings.audio_settings import *
from settings.procces_size_audio import process_large_audio
from json_scanner import read_json_files, get_filename

def load_models_config():
    """Carrega as configurações do models_api.json uma única vez."""
    config_path = Path(__file__).parent.parent / "model" / "models_api.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_audio_files(audio_dir, models_config):
    """Obtém lista de todos os arquivos de áudio no diretório."""
    audio_extensions = models_config.get("gcp", {}).get("audio_input_format", [])

    audio_files = []
    for file in os.listdir(audio_dir):
        if any(file.lower().endswith(ext) for ext in audio_extensions):
            audio_files.append(os.path.join(audio_dir, file))
    return sorted(audio_files)

def save_transcription_json(audio_file, transcription, output_dir):
    """
    Salva a string JSON de resposta COMPLETA da API em um arquivo.
    'transcription_string' deve ser a string retornada por MessageToJson.
    """
    file_name = os.path.splitext(os.path.basename(audio_file))[0]
    json_file = os.path.join(output_dir, f"{file_name}.json")
    
    # Escreve a string recebida diretamente no arquivo.
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(transcription, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Transcrição detalhada salva em: {json_file}")
    return json_file

def process_transcriptions_from_json(json_dir, txt_output_dir, models_config):
    """Processa transcrições JSON existentes e converte para TXT usando a lógica do json_scanner.py"""
    gcp_config = models_config.get("gcp", {})
    txt_extension = gcp_config.get("audio_extension_file", "_google_stt.txt")
    
    processed_files = []
    
    # Usar a lógica do json_scanner.py para obter arquivos de saída
    output_files = get_filename(txt_output_dir)
    
    # Listar todos os arquivos JSON
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    
    # Processar cada arquivo JSON usando a lógica do json_scanner.py
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        
        # Nome base do arquivo (sem extensão)
        base_name = os.path.splitext(json_file)[0]
        txt_file = os.path.join(txt_output_dir, f"{base_name}{txt_extension}")
        
        # Verificar se o arquivo de transcrição já existe (lógica do json_scanner.py)
        if os.path.exists(txt_file):
            print(f"O arquivo: {txt_file} já existe para a transcrição: {json_path}")
            continue
        
        try:
            # Usar a função do json_scanner.py para ler o JSON
            transcription = read_json_files(json_path)
            with open(txt_file, 'w', encoding='utf-8') as file:
                file.write(transcription)
            print(f"O arquivo: {txt_file} foi gerado para a transcrição: {json_path}")
            processed_files.append(txt_file)
                
        except Exception as e:
            print(f"Erro ao processar {json_file}: {e}")
    
    return processed_files

def transcribe_single_file(audio_file, json_output_dir, txt_output_dir, models_config):
    """Transcreve um único arquivo de áudio."""
    file_name = os.path.basename(audio_file)
    print(f"\nProcessando: {file_name}")
    
    # Verificar se já existe transcrição JSON
    base_name = os.path.splitext(file_name)[0]
    json_file = os.path.join(json_output_dir, f"{base_name}.json")
    
    if os.path.exists(json_file):
        print(f"Arquivo JSON já existe para {file_name}, processando para TXT...")
        # Usar a lógica do json_scanner.py para converter JSON para TXT
        try:
            transcription = read_json_files(json_file)
            if transcription and transcription.strip():
                # Usar configuração do models_api.json para extensão
                gcp_config = models_config.get("gcp", {})
                txt_extension = gcp_config.get("audio_extension_file", "_google_stt.txt")
                
                txt_file = os.path.join(txt_output_dir, f"{base_name}{txt_extension}")
                
                if not os.path.exists(txt_file):
                    with open(txt_file, 'w', encoding='utf-8') as file:
                        file.write(transcription)
                    print(f"✓ Arquivo TXT gerado: {txt_file}")
                else:
                    print(f"Arquivo TXT já existe: {txt_file}")
                return True
            else:
                print(f"✗ JSON vazio ou inválido para {file_name}")
                return False
        except Exception as e:
            print(f"✗ Erro ao processar JSON existente {file_name}: {e}")
            return False
    
    try:
        # Obter duração do arquivo
        duration = get_audio_duration(audio_file)
        print(f"Duração: {duration:.2f} segundos")
        
        # Processar arquivo de audio
        print("Processando arquivo de audio...")
        print(audio_file)
        transcription = process_audio(audio_file, txt_output_dir)
        
        if transcription and transcription.strip():
            # Salvar apenas em formato JSON (o TXT será gerado depois)
            save_transcription_json(audio_file, transcription, json_output_dir)
            print(f"✓ Transcrição JSON salva com sucesso!")
            return True
        else:
            print(f"✗ Falha na transcrição - resultado vazio")
            return False
            
    except Exception as e:
        print(f"✗ Erro ao processar {file_name}: {e}")
        return False

def main():
    """Função principal para transcrição automática do dataset."""
    print("=== Sistema de Transcrição Automática GCP ===")
    print(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Carregar configurações uma única vez
    print("Carregando configurações...")
    models_config = load_models_config()
    
    # Definir caminhos
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    audio_dir = os.path.join(project_root, 'project_tg/Datasets_Audios_Medicos/Audios')
    json_output_dir = os.path.join(project_root, 'project_tg/application/gcp/json')
    txt_output_dir = os.path.join(project_root, 'project_tg/Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gcp')
    
    # Criar diretórios de saída se não existirem
    os.makedirs(json_output_dir, exist_ok=True)
    os.makedirs(txt_output_dir, exist_ok=True)
    
    print(f"Diretório de áudios: {audio_dir}")
    print(f"Diretório JSON de saída: {json_output_dir}")
    print(f"Diretório TXT de saída: {txt_output_dir}")
    # Verificar se o diretório de áudios existe
    if not os.path.exists(audio_dir):
        print(f"❌ Diretório de áudios não encontrado: {audio_dir}")
        return
    
    # Obter lista de arquivos de áudio
    audio_files = get_audio_files(audio_dir, models_config)
    if not audio_files:
        print("❌ Nenhum arquivo de áudio encontrado!")
        return
    
    print(f"\nEncontrados {len(audio_files)} arquivos de áudio:")
    for file in audio_files:
        print(f"  - {os.path.basename(file)}")
    
    # Processar cada arquivo de áudio
    successful = 0
    failed = 0
    
    print(f"\n=== PROCESSANDO ARQUIVOS DE ÁUDIO ===")
    # for i, audio_file in enumerate(audio_files, 1):
    #     print(f"\n[{i}/{len(audio_files)}] Processando arquivo...")
        
    #     if transcribe_single_file(audio_file, json_output_dir, txt_output_dir, models_config):
    #         successful += 1
    #     else:
    #         failed += 1

    #     # Pequena pausa entre processamentos para evitar rate limiting
    #     if i < len(audio_files):
    #         time.sleep(1)
    
    # Processar arquivos JSON existentes para gerar TXT
    print(f"\n=== PROCESSANDO ARQUIVOS JSON EXISTENTES ===")
    processed_txt_files = process_transcriptions_from_json(json_output_dir, txt_output_dir, models_config)
    
    # Resumo final
    print(f"\n=== RESUMO FINAL ===")
    print(f"Total de arquivos de áudio: {len(audio_files)}")
    print(f"Transcrições bem-sucedidas: {successful}")
    print(f"Transcrições falharam: {failed}")
    print(f"Arquivos TXT processados: {len(processed_txt_files)}")
    print(f"Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
