import pandas as pd
import logging

def process_escala(file_path):
    logging.info(f"Processando arquivo: {file_path}")
    try:
        df = pd.read_excel(file_path)
        logging.info(f"Colunas encontradas no arquivo Excel: {df.columns.tolist()}")

        # Mapeamento flexível de nomes de coluna
        mapa_colunas = {
            'data': None,
            'horario': None,
            'contrato': None,
            'nome': None,
            'turno': None
        }

        # Tenta encontrar as colunas por nomes comuns ou variações
        for col in df.columns:
            col_lower = str(col).strip().lower()
            if 'data' in col_lower:
                mapa_colunas['data'] = col
            elif 'horario' in col_lower or 'hora' in col_lower:
                mapa_colunas['horario'] = col
            elif 'contrato' in col_lower:
                mapa_colunas['contrato'] = col
            elif 'nome' in col_lower or 'cooperado' in col_lower: # Inclui 'cooperado' para flexibilidade
                mapa_colunas['nome'] = col
            elif 'turno' in col_lower:
                mapa_colunas['turno'] = col
        
        # Verifica se as colunas essenciais foram encontradas
        if not all(mapa_colunas[key] for key in ['data', 'horario', 'contrato', 'nome', 'turno']):
            missing_cols = [key for key, value in mapa_colunas.items() if value is None]
            logging.error(f"ERRO CRÍTICO: Colunas essenciais não encontradas: {missing_cols}. Colunas disponíveis no arquivo: {df.columns.tolist()}")
            raise ValueError(f"Colunas essenciais ausentes no arquivo Excel: {missing_cols}")

        escala = []
        for index, row in df.iterrows():
            # Pula linhas onde a coluna 'nome' está vazia ou é NaN
            nome_cooperado = str(row[mapa_colunas['nome']]).strip()
            if pd.isna(row[mapa_colunas['nome']]) or nome_cooperado == "":
                continue # Pula para a próxima linha se o nome estiver vazio

            escala.append({
                'data': str(row[mapa_colunas['data']]),
                'horario': str(row[mapa_colunas['horario']]),
                'contrato': str(row[mapa_colunas['contrato']]),
                'nome': nome_cooperado,
                'turno': str(row[mapa_colunas['turno']]) # Adiciona o turno
            })
        
        logging.info(f"Processamento concluído. {len(escala)} linhas válidas encontradas.")
        return escala
    except Exception as e:
        logging.error(f"Erro ao processar o arquivo Excel: {e}")
        raise # Re-lança a exceção para ser capturada no app.py
