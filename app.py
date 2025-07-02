import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from escala_processor import process_escala
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import logging

# Configura o logging para ver mensagens no Render
logging.basicConfig(level=logging.INFO)

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'uma_chave_secreta_padrao_para_testes')
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS DO BANCO DE DADOS ---
class Cooperado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

# NOVA TABELA PARA A ESCALA
class Escala(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(50))
    horario = db.Column(db.String(50))
    contrato = db.Column(db.String(100))
    nome_cooperado = db.Column(db.String(100))


# --- Funções Auxiliares ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}

# --- Bloco para criar o banco de dados e o admin ---
with app.app_context():
    try:
        db.create_all()
        logging.info("Tabelas do banco de dados verificadas/criadas.")
        if not Cooperado.query.filter_by(email='coopexentregas.rn@gmail.com').first():
            logging.info("Usuário admin não encontrado, criando...")
            admin_senha_hash = bcrypt.hashpw('05062721'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_user = Cooperado(nome='Administrador', email='coopexentregas.rn@gmail.com', senha_hash=admin_senha_hash, admin=True)
            db.session.add(admin_user)
            db.session.commit()
            logging.info("Usuário admin criado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao inicializar o banco de dados: {e}")


# --- ROTAS DA APLICAÇÃO ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Cooperado.query.filter_by(email=email).first()
        if user and bcrypt.checkpw(senha.encode('utf-8'), user.senha_hash.encode('utf-8')):
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

    # Carrega a escala do banco de dados
    escala_atual = Escala.query.all()

    if user.admin:
        cooperados_list = Cooperado.query.filter_by(admin=False).order_by(Cooperado.nome).all()
        return render_template('admin.html', cooperados=cooperados_list, escala=escala_atual)
    else:
        escala_pessoal = [item for item in escala_atual if user.nome.lower() in item.nome_cooperado.lower()]
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
        
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        try:
            # Processa o arquivo Excel
            escala_processada = process_escala(path)
            
            # Apaga a escala antiga do banco de dados
            Escala.query.delete()
            
            # Adiciona a nova escala ao banco de dados
            for item in escala_processada:
                novo_item_escala = Escala(
                    data=str(item.get('data', '')),
                    horario=str(item.get('horario', '')),
                    contrato=str(item.get('contrato', '')),
                    nome_cooperado=str(item.get('nome', ''))
                )
                db.session.add(novo_item_escala)
            
            db.session.commit()
            flash('Escala processada e salva no banco de dados com sucesso!', 'success')

        except Exception as e:
            db.session.rollback() # Desfaz as alterações em caso de erro
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

    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
