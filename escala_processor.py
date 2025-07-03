import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

def process_escala(file_path):
    try:
        df = pd.read_excel(file_path, header=0)
        logging.info(f"DEBUG: Colunas encontradas no arquivo Excel -> {df.columns.tolist()}")

        colunas_possiveis = {
            'data': ['data', 'DATA'],
            # ADICIONAMOS O TURNO AQUI
            'turno': ['turno', 'TURNO'],
            'horario': ['horario', 'HORÁRIO', 'HORA'],
            'contrato': ['contrato', 'CONTRATO', 'CONTRATANTE'],
            'nome': ['nome', 'NOME', 'SÓCIO COOPERADOS', 'COOPERADO']
        }

        def encontrar_nome_coluna(nomes_possiveis, colunas_reais):
            for nome in nomes_possiveis:
                if nome in colunas_reais:
                    return nome
            return None

        colunas_reais = df.columns.tolist()
        coluna_data_real = encontrar_nome_coluna(colunas_possiveis['data'], colunas_reais)
        # ADICIONAMOS O TURNO AQUI
        coluna_turno_real = encontrar_nome_coluna(colunas_possiveis['turno'], colunas_reais)
        coluna_horario_real = encontrar_nome_coluna(colunas_possiveis['horario'], colunas_reais)
        coluna_contrato_real = encontrar_nome_coluna(colunas_possiveis['contrato'], colunas_reais)
        coluna_nome_real = encontrar_nome_coluna(colunas_possiveis['nome'], colunas_reais)

        if not coluna_nome_real:
            logging.error("ERRO CRÍTICO: Nenhuma coluna de nome foi encontrada. Verifique o cabeçalho do Excel.")
            return []

        escala = []
        for index, row in df.iterrows():
            nome = row.get(coluna_nome_real, '')
            
            if pd.notna(nome) and str(nome).strip():
                item = {
                    'data': str(row.get(coluna_data_real, '')) if coluna_data_real else '',
                    # ADICIONAMOS O TURNO AQUI
                    'turno': str(row.get(coluna_turno_real, '')) if coluna_turno_real else '',
                    'horario': str(row.get(coluna_horario_real, '')) if coluna_horario_real else '',
                    'contrato': str(row.get(coluna_contrato_real, '')) if coluna_contrato_real else '',
                    'nome': str(nome)
                }
                escala.append(item)
        
        logging.info(f"PROCESSAMENTO CONCLUÍDO: {len(escala)} linhas válidas foram encontradas.")
        return escala

    except Exception as e:
        logging.error(f"FALHA AO PROCESSAR O ARQUIVO EXCEL: {e}", exc_info=True)
        return []
