import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from escala_processor import process_escala
# --- NOVAS IMPORTAÇÕES PARA O BANCO DE DADOS ---
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import bcrypt # Para senhas seguras

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.secret_key = 'coopex_secret_key_muito_segura'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# Pega a URL do banco de dados da variável de ambiente que o Render cria
db_uri = os.environ.get('DATABASE_URL')
# O Render usa 'postgres://' mas SQLAlchemy espera 'postgresql://'
if db_uri and db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELO DO BANCO DE DADOS (TABELA DE USUÁRIOS) ---
class Cooperado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Cooperado {self.email}>'

# --- DADOS EM MEMÓRIA (A ESCALA AINDA PODE FICAR AQUI POR ENQUANTO) ---
escala_data = []

# --- Funções Auxiliares ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

# --- ROTAS DA APLICAÇÃO (MODIFICADAS) ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        # Procura o usuário no banco de dados
        user = Cooperado.query.filter_by(email=email).first()
        # Verifica se o usuário existe e se a senha está correta
        if user and bcrypt.checkpw(senha.encode('utf-8'), user.senha_hash):
            session['email'] = user.email
            session['admin'] = user.admin
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('E-mail ou senha inválidos.', 'danger')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    user = Cooperado.query.filter_by(email=session['email']).first()
    if not user:
        return redirect(url_for('logout'))

    if user.admin:
        # Pega todos os cooperados do banco, exceto o admin
        cooperados_list = Cooperado.query.filter_by(admin=False).all()
        return render_template('admin.html', cooperados=cooperados_list, escala=escala_data)
    else:
        escala_pessoal = [linha for linha in escala_data if user.nome.lower() in str(linha.get('nome', '')).lower()]
        return render_template('cooperado.html', nome=user.nome, escala=escala_pessoal)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'):
        return redirect(url_for('login'))
    # ... (o resto da função de upload continua igual)
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
    
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')

    # Verifica se o usuário já existe no banco
    if Cooperado.query.filter_by(email=email).first():
        flash('Este e-mail já está cadastrado.', 'warning')
        return redirect(url_for('dashboard'))

    # Cria um hash seguro da senha
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    
    # Cria o novo usuário e salva no banco
    novo_cooperado = Cooperado(nome=nome, email=email, senha_hash=senha_hash, admin=False)
    db.session.add(novo_cooperado)
    db.session.commit()
    
    flash(f'Usuário {nome} adicionado com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/remove_user/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    user_para_remover = Cooperado.query.get(user_id)
    if user_para_remover and not user_para_remover.admin:
        db.session.delete(user_para_remover)
        db.session.commit()
        flash('Usuário removido com sucesso!', 'success')
        
    return redirect(url_for('dashboard'))

# --- COMANDO PARA INICIAR O BANCO DE DADOS ---
with app.app_context():
    db.create_all()
    # Cria o usuário admin se ele não existir
    if not Cooperado.query.filter_by(email='coopexentregas.rn@gmail.com').first():
        admin_senha_hash = bcrypt.hashpw('05062721'.encode('utf-8'), bcrypt.gensalt())
        admin_user = Cooperado(
            nome='Administrador',
            email='coopexentregas.rn@gmail.com',
            senha_hash=admin_senha_hash,
            admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
