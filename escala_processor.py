import pandas as pd
import logging
from openpyxl import load_workbook

logging.basicConfig(level=logging.INFO)

def get_fill_color(cell):
    fill = cell.fill
    if fill and fill.fgColor and fill.fgColor.type == "rgb":
        return fill.fgColor.rgb  # Exemplo: 'FFFF0000' (vermelho)
    return None

def process_escala(file_path):
    try:
        # Lê o Excel com pandas (dados)
        df = pd.read_excel(file_path, header=0)
        logging.info(f"Colunas no Excel: {df.columns.tolist()}")

        # Abre a planilha com openpyxl para pegar cores
        wb = load_workbook(file_path)
        ws = wb.active

        # Mapear nomes possíveis das colunas (flexível)
        colunas_possiveis = {
            'data': ['data', 'DATA', 'Data'],
            'horario': ['horario', 'HORÁRIO', 'horário', 'HORA', 'hora'],
            'contrato': ['contrato', 'CONTRATO', 'Contrato'],
            'nome': ['nome', 'NOME', 'Nome', 'NOME DO COOPERADO', 'Cooperado', 'COOPERADO'],
            'turno': ['turno', 'TURNO', 'Turno']
        }

        def encontrar_nome_coluna(possiveis, reais):
            for n in possiveis:
                if n in reais:
                    return n
            return None

        colunas_reais = df.columns.tolist()
        col_data = encontrar_nome_coluna(colunas_possiveis['data'], colunas_reais)
        col_horario = encontrar_nome_coluna(colunas_possiveis['horario'], colunas_reais)
        col_contrato = encontrar_nome_coluna(colunas_possiveis['contrato'], colunas_reais)
        col_nome = encontrar_nome_coluna(colunas_possiveis['nome'], colunas_reais)
        col_turno = encontrar_nome_coluna(colunas_possiveis['turno'], colunas_reais)

        if not col_nome:
            logging.error("Coluna 'nome' (ou equivalente) não encontrada no arquivo!")
            return []

        escala = []
        for idx, row in df.iterrows():
            nome = row.get(col_nome, '')
            if pd.notna(nome) and str(nome).strip():
                linha_excel = idx + 2  # pandas zero-based, Excel linha 1 = header

                coluna_idx_nome = df.columns.get_loc(col_nome) + 1  # openpyxl index base 1
                cell_nome = ws.cell(row=linha_excel, column=coluna_idx_nome)
                cor_nome = get_fill_color(cell_nome)

                item = {
                    'data': str(row.get(col_data, '')) if col_data else '',
                    'horario': str(row.get(col_horario, '')) if col_horario else '',
                    'contrato': str(row.get(col_contrato, '')) if col_contrato else '',
                    'nome': str(nome),
                    'turno': str(row.get(col_turno, '')) if col_turno else '',
                    'cor_nome': cor_nome
                }
                escala.append(item)

        logging.info(f"Processadas {len(escala)} linhas com dados e cores.")
        return escala

    except Exception as e:
        logging.error(f"Erro ao processar escala: {e}", exc_info=True)
        return []
