import os
import base64
import json
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess
import tempfile
from openai import AzureOpenAI
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class RobustAudioTranscriber:
    def __init__(self):
        self.endpoint = os.getenv("ENDPOINT_URL")
        self.deployment = os.getenv("DEPLOYMENT_NAME")
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Carregar configuração dos modelos
        self.models_config = self._load_models_config()
        self.gpt_config = self.models_config.get("gpt", {})
        self.model_name = self.gpt_config.get("model_name", "gpt-4o-audio-preview")
        self.audio_extension_file = self.gpt_config.get("audio_extension_file", "_gpt4o.txt")
        self.audio_input_formats = self.gpt_config.get("audio_input_format", ["wav", "mp3", "flac", "opus", "pcm16"])
        
        # Configurações de tamanho de arquivo
        self.max_file_size_mb = 25  # Limite do GPT-4o-audio-preview
        self.chunk_duration_seconds = 300  # 5 minutos por chunk
        
        # Inicializar cliente OpenAI
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version="2025-01-01-preview",
        )
        
        # Definir caminhos
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(self.current_dir)))
        self.datasets_path = os.path.join(self.project_root, 'project_tg/Datasets_Audios_Medicos/Audios')
        self.output_path = os.path.join(self.project_root, 'project_tg/Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gpt4o')
        
        # Criar diretório de saída se não existir
        os.makedirs(self.output_path, exist_ok=True)

    def _load_models_config(self) -> Dict[str, Any]:
        """Carrega a configuração dos modelos do arquivo JSON."""
        config_path = Path(__file__).parent.parent / "model" / "models_api.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Arquivo de configuração não encontrado: {config_path}")
            return {}

    def _validate_audio_file(self, file_path: str) -> bool:
        """Valida se o arquivo de áudio é válido e pode ser processado."""
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(file_path):
                logger.error(f"Arquivo não encontrado: {file_path}")
                return False
            
            # Verificar tamanho do arquivo
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # Verificar extensão
            file_extension = os.path.splitext(file_path)[1].lstrip('.').lower()
            if file_extension not in self.audio_input_formats:
                logger.warning(f"Formato não suportado ({file_extension}): {file_path}")
                return False
            
            # Verificar se o arquivo não está corrompido (tentativa básica)
            try:
                with open(file_path, 'rb') as f:
                    f.read(1024)  # Ler primeiros 1KB
            except Exception as e:
                logger.error(f"Erro ao ler arquivo: {file_path} - {e}")
                return False
            
            # Log do tamanho do arquivo (mas não rejeitar por ser grande)
            if file_size_mb > self.max_file_size_mb:
                logger.info(f"Arquivo grande ({file_size_mb:.2f}MB) - será dividido em chunks: {file_path}")
            else:
                logger.info(f"Arquivo válido: {file_path} ({file_size_mb:.2f}MB)")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação do arquivo {file_path}: {e}")
            return False

    def _convert_audio_format(self, input_path: str, output_path: str, target_format: str = "wav") -> bool:
        """Converte arquivo de áudio para formato compatível usando ffmpeg."""
        try:
            # Verificar se ffmpeg está disponível
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            
            # Comando ffmpeg para conversão
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-acodec", "pcm_s16le",  # Codec compatível
                "-ar", "16000",  # Taxa de amostragem padrão
                "-ac", "1",  # Mono
                "-y",  # Sobrescrever arquivo de saída
                output_path
            ]
            
            logger.info(f"Convertendo {input_path} para {output_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Conversão bem-sucedida: {output_path}")
                return True
            else:
                logger.error(f"Erro na conversão: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError:
            logger.error("ffmpeg não encontrado. Instale ffmpeg para conversão de áudio.")
            return False
        except Exception as e:
            logger.error(f"Erro na conversão de áudio: {e}")
            return False

    def _split_audio_file(self, input_path: str, chunk_duration: int = 300) -> List[str]:
        """Divide arquivo de áudio em chunks menores."""
        try:
            # Verificar se ffmpeg está disponível
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            
            chunk_files = []
            temp_dir = tempfile.mkdtemp()
            
            # Obter duração total do áudio
            cmd_duration = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                input_path
            ]
            
            result = subprocess.run(cmd_duration, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Erro ao obter duração do áudio: {result.stderr}")
                return []
            
            total_duration = float(result.stdout.strip())
            logger.info(f"Duração total do áudio: {total_duration:.2f} segundos")
            
            # Dividir em chunks
            chunk_count = int(total_duration / chunk_duration) + 1
            
            for i in range(chunk_count):
                start_time = i * chunk_duration
                chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.wav")
                
                cmd_split = [
                    "ffmpeg",
                    "-i", input_path,
                    "-ss", str(start_time),
                    "-t", str(chunk_duration),
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    "-y",
                    chunk_path
                ]
                
                result = subprocess.run(cmd_split, capture_output=True, text=True)
                if result.returncode == 0:
                    chunk_files.append(chunk_path)
                    logger.info(f"Chunk {i+1}/{chunk_count} criado: {chunk_path}")
                else:
                    logger.error(f"Erro ao criar chunk {i+1}: {result.stderr}")
            
            return chunk_files
            
        except Exception as e:
            logger.error(f"Erro na divisão do áudio: {e}")
            return []

    def _transcribe_audio_chunk(self, audio_data: bytes, file_extension: str, chunk_index: int = 0) -> Optional[str]:
        """Transcreve um chunk de áudio usando GPT-4o-audio-preview."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Tentativa {attempt + 1}/{max_retries} para transcrever chunk {chunk_index}")
                
                # Prompt melhorado para transcrição
                prompt_text = f"""Por favor, transcreva o conteúdo completo do áudio que será enviado a seguir.

INSTRUÇÕES IMPORTANTES:
1. Transcreva EXATAMENTE o que você ouve, palavra por palavra
2. Preserve pontuação, ortografia e expressões tal como foram ditas
3. Se houver pausas longas, indique com [...]
4. Mantenha a estrutura das frases originais
5. NÃO adicione interpretações ou explicações
6. NÃO resuma o conteúdo
7. Se este é um chunk de um arquivo maior (chunk {chunk_index + 1}), mantenha o contexto

FORMATO DE SAÍDA:
- Uma transcrição limpa e precisa
- Sem mensagens introdutórias ou explicativas
- Apenas o texto transcrito

Transcreva agora:"""

                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    audio={
                        "voice": "alloy",
                        "format": file_extension
                    },
                    modalities=["text", "audio"],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt_text
                                },
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": audio_data,
                                        "format": file_extension
                                    }
                                }
                            ]
                        }
                    ]
                )
                
                transcription = completion.choices[0].message.audio.transcript
                
                if transcription and len(transcription.strip()) > 0:
                    logger.info(f"Transcrição bem-sucedida para chunk {chunk_index}")
                    return transcription
                else:
                    logger.warning(f"Transcrição vazia para chunk {chunk_index}")
                    return None
                    
            except Exception as e:
                logger.error(f"Erro na transcrição do chunk {chunk_index} (tentativa {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Aguardando {retry_delay} segundos antes da próxima tentativa...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponencial
                else:
                    logger.error(f"Falha definitiva na transcrição do chunk {chunk_index}")
                    return None
        
        return None

    def transcribe_file(self, audio_file_path: str) -> bool:
        """Transcreve um arquivo de áudio completo."""
        try:
            logger.info(f"Iniciando transcrição de: {audio_file_path}")
            
            # Validar arquivo
            if not self._validate_audio_file(audio_file_path):
                return False
            
            # Definir caminho de saída
            base_name = os.path.basename(audio_file_path)
            name_without_ext = os.path.splitext(base_name)[0]
            output_file_path = os.path.join(self.output_path, f"{name_without_ext}{self.audio_extension_file}")
            
            # Verificar se já existe transcrição
            if os.path.exists(output_file_path):
                logger.info(f"Transcrição já existe: {output_file_path}")
                return True
            
            # Verificar tamanho do arquivo
            file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
            file_extension = os.path.splitext(audio_file_path)[1].lstrip('.').lower()
            
            transcriptions = []
            
            if file_size_mb <= self.max_file_size_mb:
                # Arquivo pequeno - transcrever diretamente
                logger.info("Arquivo pequeno - transcrevendo diretamente")
                
                with open(audio_file_path, 'rb') as audio_reader:
                    audio_data = base64.b64encode(audio_reader.read()).decode('utf-8')
                
                transcription = self._transcribe_audio_chunk(audio_data, file_extension)
                if transcription:
                    transcriptions.append(transcription)
                    
            else:
                # Arquivo grande - dividir em chunks
                logger.info("Arquivo grande - tentando dividir em chunks")
                
                # Converter para formato compatível se necessário
                temp_file = audio_file_path
                if file_extension not in ["wav", "mp3"]:
                    temp_file = tempfile.mktemp(suffix=".wav")
                    if not self._convert_audio_format(audio_file_path, temp_file):
                        logger.error("Falha na conversão do arquivo")
                        return False
                
                # Dividir em chunks
                chunk_files = self._split_audio_file(temp_file, self.chunk_duration_seconds)
                
                if not chunk_files:
                    logger.error("Falha ao dividir arquivo em chunks - FFmpeg pode não estar instalado")
                    logger.info("Para processar arquivos grandes, instale FFmpeg:")
                    logger.info("Windows: choco install ffmpeg")
                    logger.info("Ubuntu: sudo apt install ffmpeg")
                    logger.info("macOS: brew install ffmpeg")
                    
                    # Tentar transcrever o arquivo inteiro mesmo sendo grande (pode falhar)
                    logger.warning("Tentando transcrever arquivo grande sem divisão (pode falhar)...")
                    try:
                        with open(audio_file_path, 'rb') as audio_reader:
                            audio_data = base64.b64encode(audio_reader.read()).decode('utf-8')
                        
                        transcription = self._transcribe_audio_chunk(audio_data, file_extension)
                        if transcription:
                            transcriptions.append(transcription)
                        else:
                            logger.error("Falha na transcrição do arquivo grande")
                            return False
                    except Exception as e:
                        logger.error(f"Erro ao tentar transcrever arquivo grande: {e}")
                        return False
                else:
                    # Transcrever cada chunk
                    for i, chunk_file in enumerate(chunk_files):
                        logger.info(f"Transcrevendo chunk {i+1}/{len(chunk_files)}")
                        
                        with open(chunk_file, 'rb') as chunk_reader:
                            chunk_data = base64.b64encode(chunk_reader.read()).decode('utf-8')
                        
                        chunk_transcription = self._transcribe_audio_chunk(chunk_data, "wav", i)
                        if chunk_transcription:
                            transcriptions.append(f"[Chunk {i+1}] {chunk_transcription}")
                        
                        # Limpar arquivo temporário do chunk
                        try:
                            os.remove(chunk_file)
                        except:
                            pass
                
                # Limpar arquivo temporário se foi criado
                if temp_file != audio_file_path:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            # Salvar transcrição final
            if transcriptions:
                final_transcription = "\n\n".join(transcriptions)
                
                with open(output_file_path, 'w', encoding='utf-8') as file:
                    file.write(final_transcription)
                
                logger.info(f"Transcrição salva em: {output_file_path}")
                return True
            else:
                logger.error("Nenhuma transcrição foi gerada")
                return False
                
        except Exception as e:
            logger.error(f"Erro na transcrição do arquivo {audio_file_path}: {e}")
            return False

    def transcribe_all_files(self) -> Dict[str, bool]:
        """Transcreve todos os arquivos de áudio no diretório."""
        results = {}
        
        logger.info(f"Procurando arquivos de áudio em: {self.datasets_path}")
        
        if not os.path.exists(self.datasets_path):
            logger.error(f"Diretório não encontrado: {self.datasets_path}")
            return results
        
        # Encontrar todos os arquivos de áudio
        audio_files = []
        for file_name in os.listdir(self.datasets_path):
            file_path = os.path.join(self.datasets_path, file_name)
            
            if os.path.isfile(file_path):
                file_extension = os.path.splitext(file_name)[1].lstrip('.').lower()
                if file_extension in self.audio_input_formats:
                    audio_files.append(file_path)
        
        logger.info(f"Encontrados {len(audio_files)} arquivos de áudio")
        
        # Transcrever cada arquivo
        for i, audio_file in enumerate(audio_files):
            logger.info(f"Processando arquivo {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")
            
            success = self.transcribe_file(audio_file)
            results[audio_file] = success
            
            if success:
                logger.info(f"✓ Sucesso: {os.path.basename(audio_file)}")
            else:
                logger.error(f"✗ Falha: {os.path.basename(audio_file)}")
        
        # Resumo final
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"\n=== RESUMO FINAL ===")
        logger.info(f"Total de arquivos: {total}")
        logger.info(f"Sucessos: {successful}")
        logger.info(f"Falhas: {total - successful}")
        logger.info(f"Taxa de sucesso: {(successful/total)*100:.1f}%")
        
        return results


def main():
    """Função principal para executar a transcrição."""
    transcriber = RobustAudioTranscriber()
    results = transcriber.transcribe_all_files()
    
    # Salvar log de resultados
    log_file = os.path.join(transcriber.output_path, "transcription_log.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Log de resultados salvo em: {log_file}")


if __name__ == "__main__":
    main()
