import os
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename
from escala_processor import process_escala

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.secret_key = 'coopex_secret_key_muito_segura'  # Use uma chave mais segura
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Cria o diretório de uploads se ele não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- "Banco de Dados" Simulado ---
# Em um ambiente real, isso seria um banco de dados (ex: SQLite, PostgreSQL)
cooperados = {
    'coopexentregas.rn@gmail.com': {'senha': '05062721', 'nome': 'Administrador', 'admin': True}
}
escala_data = []  # Cache da escala em memória

# --- Funções Auxiliares ---
def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Rotas da Aplicação ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        user = cooperados.get(email)
        if user and user['senha'] == senha:
            session['email'] = email
            session['admin'] = user['admin']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="E-mail ou senha inválido.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    if session.get('admin'):
        # Passa a lista de cooperados para o template, exceto o próprio admin
        cooperados_list = {email: data for email, data in cooperados.items() if not data['admin']}
        return render_template('admin.html', cooperados=cooperados_list)
    else:
        nome_usuario = cooperados[session['email']]['nome']
        # Filtra a escala para o usuário logado (case-insensitive)
        escala_pessoal = [linha for linha in escala_data if nome_usuario.lower() in str(linha.get('nome', '')).lower()]
        return render_template('cooperado.html', nome=nome_usuario, escala=escala_pessoal)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect(url_for('login'))

    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        global escala_data
        try:
            escala_data = process_escala(path)
        except Exception as e:
            # Adicionar tratamento de erro se o arquivo for inválido
            print(f"Erro ao processar o arquivo: {e}")
            return redirect(url_for('dashboard')) # Redirecionar com uma mensagem de erro seria ideal
    return redirect(url_for('dashboard'))

@app.route('/add_user', methods=['POST'])
def add_user():
    if not session.get('admin'):
        return redirect(url_for('login'))
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    if email not in cooperados:
        cooperados[email] = {'senha': senha, 'nome': nome, 'admin': False}
    return redirect(url_for('dashboard'))

# Rota corrigida para receber o e-mail na URL
@app.route('/remove_user/<path:email>')
def remove_user(email):
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    # Verifica se o usuário existe e não é um admin antes de deletar
    if email in cooperados and not cooperados[email].get('admin'):
        del cooperados[email]
        
    return redirect(url_for('dashboard'))

# --- Execução da Aplicação ---
if __name__ == '__main__':
    app.run(debug=True)
