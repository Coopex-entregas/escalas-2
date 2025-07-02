import pandas as pd

def process_escala(file_path):
    df = pd.read_excel(file_path)
    escala = []
    for _, row in df.iterrows():
        escala.append({
            'data': row[0],
            'horario': row[3],
            'contrato': row[5],
            'nome': row[6]
        })
    return escala
