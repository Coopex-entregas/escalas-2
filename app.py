import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from escala_processor import process_escala
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Nova importação
import bcrypt

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.secret_key = 'coopex_secret_key_muito_segura'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
db_uri = os.environ.get('DATABASE_URL')
if db_uri and db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db) # Inicializa o Flask-Migrate

# --- MODELO DO BANCO DE DADOS ---
class Cooperado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Cooperado {self.email}>'

# --- DADOS EM MEMÓRIA ---
escala_data = []

# --- Funções Auxiliares ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

# --- ROTAS DA APLICAÇÃO ---
# (Todas as suas rotas @app.route(...) permanecem exatamente as mesmas de antes)
# ... (login, dashboard, logout, upload, add_user, remove_user) ...

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
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    user = Cooperado.query.filter_by(email=session['email']).first()
    if not user:
        session.clear()
        flash('Sua sessão expirou. Por favor, faça login novamente.', 'warning')
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

# O bloco que criava o admin foi removido daqui

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
