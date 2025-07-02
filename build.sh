#!/bin/bash

# Instala as dependências
pip install -r requirements.txt

# Executa o comando para criar as tabelas no banco de dados
flask db init
flask db migrate -m "Initial migration."
flask db upgrade
