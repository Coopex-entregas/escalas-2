import pandas as pd

def process_escala(file_path):
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        escala = []
        # Itera sobre as linhas do DataFrame para extrair os dados
        for _, row in df.iterrows():
            # Adiciona verificação para garantir que a coluna 6 (nome) não está vazia
            if pd.notna(row[6]) and str(row[6]).strip() != "":
                escala.append({
                    'data': row[0],
                    'horario': row[3],
                    'contrato': row[5],
                    'nome': str(row[6]).strip()
                })
        return escala
    except Exception as e:
        print(f"Erro ao processar o arquivo Excel: {e}")
        return []
