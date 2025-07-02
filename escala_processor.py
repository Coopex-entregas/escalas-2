import pandas as pd

def process_escala(file_path):
    """
    Processa um arquivo Excel de escala e retorna uma lista de dicionários.
    Assume que os dados relevantes estão nas colunas A, D, F, G.
    """
    try:
        # Tenta ler a planilha, especificando os nomes das colunas para evitar problemas
        # com cabeçalhos ausentes ou em linhas erradas.
        df = pd.read_excel(file_path, header=None, names=['data', 'colB', 'colC', 'horario', 'colE', 'contrato', 'nome'])
        
        escala = []
        for index, row in df.iterrows():
            # Pula linhas onde o nome do cooperado está vazio (NaN)
            if pd.isna(row['nome']):
                continue

            escala.append({
                'data': row['data'],
                'horario': row['horario'],
                'contrato': row['contrato'],
                'nome': row['nome']
            })
        return escala
    except Exception as e:
        print(f"Ocorreu um erro ao ler o arquivo Excel: {e}")
        return [] # Retorna uma lista vazia em caso de erro
