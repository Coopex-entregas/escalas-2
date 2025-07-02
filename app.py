import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import logging
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, session, url_for, flash
from escala_processor import process_escala

logging.basicConfig(level=logging.INFO)

# --- Criação da Aplicação (Dentro de uma função) ---
def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'uma_chave_secreta_padrao_para_testes')
    
    # --- CONFIGURAÇÃO DO BANCO DE DADOS ---
    db_uri = os.environ.get('DATABASE_URL')
    if not db_uri:
        logging.error("ERRO CRÍTICO: DATABASE_URL não foi encontrada!")
        raise ValueError("DATABASE_URL não configurada")

    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    return app

# --- Inicialização ---
app = create_app()
db = SQLAlchemy(app)

# --- MODELO DO BANCO DE DADOS ---
class Cooperado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

# --- DADOS EM MEMÓRIA ---
escala_data = []

# --- Funções Auxiliares ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

# --- Bloco para criar o banco de dados e o admin ---
with app.app_context():
    try:
        db.create_all()
        if not Cooperado.query.filter_by(email='coopexentregas.rn@gmail.com').first():
            admin_senha_hash = bcrypt.hashpw('05062721'.encode('utf-8'), bcrypt.gensalt())
            admin_user = Cooperado(nome='Administrador', email='coopexentregas.rn@gmail.com', senha_hash=admin_senha_hash, admin=True)
            db.session.add(admin_user)
            db.session.commit()
    except Exception as e:
        logging.error(f"Erro ao inicializar o banco de dados: {e}")

# --- ROTAS ---
# (As rotas @app.route(...) vêm aqui, exatamente como antes)
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Cooperado.query.filter_by(email=email).first()
        if user and bcrypt.checkpw(senha.encode('utf-8'), user.senha_hash):
            session['email'] = user.email
            session['admin'] = user.admin
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('E-mail ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    user = Cooperado.query.filter_by(email=session['email']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if user.admin:
        cooperados_list = Cooperado.query.filter_by(admin=False).order_by(Cooperado.nome).all()
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

    if Cooperado.query.filter_by(email=email).first():
        flash('Este e-mail já está cadastrado.', 'warning')
        return redirect(url_for('dashboard'))

    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    
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

