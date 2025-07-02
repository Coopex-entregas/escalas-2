from flask import Flask, render_template, request, redirect, session, url_for
import pandas as pd
import os
from werkzeug.utils import secure_filename
from escala_processor import process_escala

app = Flask(__name__)
app.secret_key = 'coopex_secret'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Mock: banco de dados de cooperados
cooperados = {
    'coopexentregas.rn@gmail.com': {'senha': '05062721', 'nome': 'Administrador', 'admin': True},
    # Exemplo: 'joao@gmail.com': {'senha': '123', 'nome': 'João da Silva', 'admin': False}
}

escala_data = []  # Cache da escala processada

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        if email in cooperados and cooperados[email]['senha'] == senha:
            session['email'] = email
            session['admin'] = cooperados[email]['admin']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Login inválido.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    if session['admin']:
        return render_template('admin.html', cooperados=cooperados)
    else:
        nome = cooperados[session['email']]['nome']
        escala_pessoal = [linha for linha in escala_data if nome.lower() in linha['nome'].lower()]
        return render_template('cooperado.html', nome=nome, escala=escala_pessoal)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'email' not in session or not session.get('admin'):
        return redirect(url_for('login'))
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        global escala_data
        escala_data = process_escala(path)
    return redirect(url_for('dashboard'))

@app.route('/add_user', methods=['POST'])
def add_user():
    if 'email' not in session or not session.get('admin'):
        return redirect(url_for('login'))
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    cooperados[email] = {'senha': senha, 'nome': nome, 'admin': False}
    return redirect(url_for('dashboard'))

@app.route('/remove_user/<email>')
def remove_user(email):
    if 'email' not in session or not session.get('admin'):
        return redirect(url_for('login'))
    if email in cooperados and not cooperados[email]['admin']:
        del cooperados[email]
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
