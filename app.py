import os
import logging
import bcrypt
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_ # Importar 'or_' para consultas complexas
from escala_processor import process_escala

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
    turno = db.Column(db.String(50))

class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conteudo = db.Column(db.Text, nullable=False)
    cooperado_id = db.Column(db.Integer, db.ForeignKey('cooperado.id'), nullable=True)
    data_envio = db.Column(db.DateTime, default=db.func.current_timestamp())

class Recado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(10), default='nao', nullable=False) 
    cooperado_id = db.Column(db.Integer, db.ForeignKey('cooperado.id'), nullable=True)
    data_criacao = db.Column(db.DateTime, default=db.func.current_timestamp())

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
    
    mensagens = []
    recados = []
    
    if user.admin:
        mensagens = Mensagem.query.order_by(Mensagem.data_envio.desc()).all()
        recados = Recado.query.order_by(Recado.data_criacao.desc()).all()
        cooperados_list = Cooperado.query.filter_by(admin=False).order_by(Cooperado.nome).all()
        return render_template('admin.html', cooperados=cooperados_list, escala=escala_atual, mensagens=mensagens, recados=recados)
    else:
        mensagens = Mensagem.query.filter(
            or_(Mensagem.cooperado_id == None, Mensagem.cooperado_id == user.id)
        ).order_by(Mensagem.data_envio.desc()).all()
        
        recados = Recado.query.filter(
            or_(Recado.cooperado_id == None, Recado.cooperado_id == user.id)
        ).order_by(Recado.data_criacao.desc()).all()

        escala_pessoal = [item for item in escala_atual if user.nome.lower() in item.nome_cooperado.lower()]
        return render_template('cooperado.html', nome=user.nome, escala=escala_pessoal, mensagens=mensagens, recados=recados)

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
                    turno=str(item.get('turno', ''))
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

@app.route('/send_message', methods=['POST'])
def send_message():
    if not session.get('admin'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))
    
    conteudo = request.form.get('conteudo')
    destinatario_id = request.form.get('destinatario')
    
    if not conteudo:
        flash('A mensagem não pode ser vazia.', 'warning')
        return redirect(url_for('dashboard'))
    
    if destinatario_id == 'all':
        nova_mensagem = Mensagem(conteudo=conteudo, cooperado_id=None)
        flash('Mensagem enviada para todos os cooperados!', 'success')
    else:
        try:
            destinatario_id = int(destinatario_id)
            destinatario = Cooperado.query.get(destinatario_id)
            if destinatario and not destinatario.admin:
                nova_mensagem = Mensagem(conteudo=conteudo, cooperado_id=destinatario_id)
                flash(f'Mensagem enviada para {destinatario.nome}!', 'success')
            else:
                flash('Destinatário inválido.', 'danger')
                return redirect(url_for('dashboard'))
        except ValueError:
            flash('Destinatário inválido.', 'danger')
            return redirect(url_for('dashboard'))
            
    db.session.add(nova_mensagem)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_message/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if not session.get('admin'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))
    
    mensagem = Mensagem.query.get(message_id)
    if mensagem:
        db.session.delete(mensagem)
        db.session.commit()
        flash('Mensagem excluída com sucesso!', 'success')
    else:
        flash('Mensagem não encontrada.', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/add_recado', methods=['POST'])
def add_recado():
    if not session.get('admin'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))
    
    titulo = request.form.get('titulo')
    destinatario_id = request.form.get('destinatario_recado')
    
    if not titulo:
        flash('O título do recado não pode ser vazio.', 'warning')
        return redirect(url_for('dashboard'))
    
    if destinatario_id == 'all':
        novo_recado = Recado(titulo=titulo, cooperado_id=None, status='nao')
        flash('Recado criado para todos os cooperados!', 'success')
    else:
        try:
            destinatario_id = int(destinatario_id)
            destinatario = Cooperado.query.get(destinatario_id)
            if destinatario and not destinatario.admin:
                novo_recado = Recado(titulo=titulo, cooperado_id=destinatario_id, status='nao')
                flash(f'Recado criado para {destinatario.nome}!', 'success')
            else:
                flash('Destinatário inválido.', 'danger')
                return redirect(url_for('dashboard'))
        except ValueError:
            flash('Destinatário inválido.', 'danger')
            return redirect(url_for('dashboard'))
            
    db.session.add(novo_recado)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/update_recado_status/<int:recado_id>', methods=['POST'])
def update_recado_status(recado_id):
    if not session.get('admin'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))
    
    recado = Recado.query.get(recado_id)
    if recado:
        recado.status = request.form.get('status')
        db.session.commit()
        flash('Status do recado atualizado!', 'success')
    else:
        flash('Recado não encontrado.', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/delete_recado/<int:recado_id>', methods=['POST'])
def delete_recado(recado_id):
    if not session.get('admin'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))
    
    recado = Recado.query.get(recado_id)
    if recado:
        db.session.delete(recado)
        db.session.commit()
        flash('Recado excluído com sucesso!', 'success')
    else:
        flash('Recado não encontrada.', 'warning')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
