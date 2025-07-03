import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from escala_processor import process_escala
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'uma_chave_secreta_local')
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Cooperado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

class Escala(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(50))
    horario = db.Column(db.String(50))
    contrato = db.Column(db.String(100))
    nome_cooperado = db.Column(db.String(100))
    turno = db.Column(db.String(50)) # <-- COLUNA TURNO ADICIONADA AO BANCO

with app.app_context():
    try:
        db.create_all()
        if not Cooperado.query.filter_by(email='coopexentregas.rn@gmail.com').first():
            admin_senha_hash = bcrypt.hashpw('05062721'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_user = Cooperado(nome='Administrador', email='coopexentregas.rn@gmail.com', senha_hash=admin_senha_hash, admin=True)
            db.session.add(admin_user)
            db.session.commit()
    except Exception as e:
        logging.error(f"Erro ao inicializar DB: {e}")

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'email' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Cooperado.query.filter_by(email=email).first()
        if user and bcrypt.checkpw(senha.encode('utf-8'), user.senha_hash.encode('utf-8')):
            session['email'], session['admin'] = user.email, user.admin
            return redirect(url_for('dashboard'))
        else:
            flash('E-mail ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session: return redirect(url_for('login'))
    user = Cooperado.query.filter_by(email=session['email']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
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
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'): return redirect(url_for('login'))
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('Nenhum arquivo selecionado.', 'warning')
        return redirect(url_for('dashboard'))

    if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in {'xlsx'}:
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(path)
        try:
            escala_processada = process_escala(path)
            if not escala_processada:
                flash('Arquivo processado, mas nenhuma linha válida encontrada.', 'warning')
                return redirect(url_for('dashboard'))
            
            Escala.query.delete()
            for item in escala_processada:
                novo_item = Escala(
                    data=str(item.get('data', '')),
                    horario=str(item.get('horario', '')),
                    contrato=str(item.get('contrato', '')),
                    nome_cooperado=str(item.get('nome', '')),
                    turno=str(item.get('turno', '')) # <-- SALVANDO O TURNO NO BANCO
                )
                db.session.add(novo_item)
            db.session.commit()
            flash('Escala processada e salva com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar arquivo: {e}', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/add_user', methods=['POST'])
def add_user():
    if not session.get('admin'): return redirect(url_for('login'))
    nome, email, senha = request.form.get('nome'), request.form.get('email'), request.form.get('senha')
    if Cooperado.query.filter_by(email=email).first():
        flash('Este e-mail já está cadastrado.', 'warning')
    else:
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        novo_cooperado = Cooperado(nome=nome, email=email, senha_hash=senha_hash)
        db.session.add(novo_cooperado)
        db.session.commit()
        flash(f'Usuário {nome} adicionado!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/remove_user/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    if not session.get('admin'): return redirect(url_for('login'))
    user = Cooperado.query.get(user_id)
    if user and not user.admin:
        db.session.delete(user)
        db.session.commit()
        flash('Usuário removido.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
