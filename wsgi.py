# wsgi.py
from app import app

if __name__ == "__main__":
    # Este comando é para o Render iniciar a aplicação
    # O host 0.0.0.0 é necessário para ser visível externamente
    # A porta é fornecida pelo Render através da variável de ambiente PORT
    app.run(host="0.0.0.0")
