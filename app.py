import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from escala_processor import process_escala

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.secret_key = 'coopex_secret_key_muito_segura'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Garante que a pasta de uploads exista
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- "Banco de Dados" Simulado ---
cooperados = {
    'coopexentregas.rn@gmail.com': {'senha': '05062721', 'nome': 'Administrador', 'admin': True}
}
escala_data = []

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
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = cooperados.get(email)
        if user and user['senha'] == senha:
            session['email'] = email
            session['admin'] = user.get('admin', False)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('E-mail ou senha inválidos.', 'danger')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        flash('Você precisa fazer login para acessar esta página.', 'warning')
        return redirect(url_for('login'))
    if session.get('admin'):
        cooperados_list = {email: data for email, data in cooperados.items() if not data['admin']}
        return render_template('admin.html', cooperados=cooperados_list, escala=escala_data)
    else:
        nome_usuario = cooperados[session['email']]['nome']
        escala_pessoal = [linha for linha in escala_data if nome_usuario.lower() in str(linha.get('nome', '')).lower()]
        return render_template('cooperado.html', nome=nome_usuario, escala=escala_pessoal)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect(url_for('login'))
    if 'file' not in request.files or request.files['file'].filename == '':
        flash('Nenhum arquivo selecionado.', 'warning')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        global escala_data
        try:
            escala_data = process_escala(path)
            flash('Escala processada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao processar o arquivo: {e}', 'danger')
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
        flash(f'Usuário {nome} adicionado!', 'success')
    else:
        flash('Este e-mail já está cadastrado.', 'warning')
    return redirect(url_for('dashboard'))

# Bloco de código corrigido
@app.route('/remove_user/<path:email>')
def remove_user(email):
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    # A linha do 'if'
    if email in cooperados and not cooperados[email].get('admin'):
        # A linha seguinte com 4 espaços de recuo
        del cooperados[email]
        # Esta linha também com 4 espaços de recuo
        flash('Usuário removido com sucesso!', 'success')
        
    return redirect(url_for('dashboard'))

# --- Execução da Aplicação (para servidor online) ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)



