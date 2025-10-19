#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Adicionar o diretório atual ao path para importar o módulo
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from info import get_statistics, write_statistics

if __name__ == "__main__":
    try:
        statistics = get_statistics('Transcriptions/json',
                                    'Transcriptions/manual_transcriptions')
        write_statistics(statistics)
        print('Script rodou com sucesso')
        print(f"Estatísticas coletadas: {statistics}")
    except Exception as e:
        print(f"Erro ao executar o script: {e}")
        import traceback
        traceback.print_exc()
