from flask import Flask, redirect, render_template, url_for, request, flash, session, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import io
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'Chave_ultraSecreta'

# conectar ao banco 
def get_db_connection():
    conn = sqlite3.connect('barbearia.db')
    conn.row_factory = sqlite3.Row  # Permite acessar os resultados como dicionário
    return conn

# Criação do banco de dados e das tabelas
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
        


# Inicializa o banco de dados (cria as tabelas se não existirem)
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            telefone TEXT,
            role TEXT NOT NULL CHECK (role IN ('admin', 'cliente')),
            data_criacao TEXT DEFAULT (datetime('now')),
            ultimo_login TEXT
)
''')
    conn.execute('''
            CREATE TABLE IF NOT EXISTS Equipe (
            equipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            email TEXT UNIQUE,
            data_admissao TEXT DEFAULT (datetime('now')),
            ativo INTEGER DEFAULT 1,
            imagem BLOB  -- Nova coluna para armazenar o caminho da imagem
        );
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Servicos (
            servicos_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            duracao INTEGER  -- duração em minutos
        );
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS Agendamentos (
            agendamento_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            equipe_id INTEGER,
            servicos_id INTEGER,
            data_hora TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (equipe_id) REFERENCES Equipe(equipe_id),
            FOREIGN KEY (servicos_id) REFERENCES Servicos(servicos_id)
        );
    ''')
    conn.commit()
    conn.close()

# Chame init_db() para garantir que as tabelas existem
init_db()

# obter o usuário pelo e-mail
def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user

# Rota de login 
@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        user = get_user_by_email(email)
        
        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('cliente_dashboard'))
        else:
            return "Credenciais inválidas"
    
    return render_template('login.html')



# Rota para INDEX
@app.route('/')
def index():
    conn = get_db_connection()
    servicos = conn.execute('SELECT nome, preco FROM Servicos').fetchall()
    conn.close()

    return render_template('index.html', servicos=servicos)


# Rota de Cadastrese
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        telefone = request.form['telefone']
        role = request.form['role']
        
        senha_hashed = generate_password_hash(senha)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO Users (nome, email, senha, telefone, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (nome, email, senha_hashed, telefone, role))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Email já cadastrado!"
        finally:
            conn.close()
    
    return render_template('register.html')

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Painel do Cliente
@app.route('/indexcliente')
def cliente_dashboard():
    if 'role' in session and session['role'] == 'cliente':
        conn = get_db_connection()
        servicos = conn.execute('SELECT nome, preco FROM Servicos').fetchall()
        conn.close()

        return render_template('cliente_dashboard.html', servicos=servicos)
    else:
        return redirect(url_for('login'))


# Painel do Adm
@app.route('/indexadmin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    else:
        return redirect(url_for('login'))

#cliente agendar
@app.route('/agendamentocliente', methods=['GET', 'POST'])
def agendamento_cliente():
    if 'user_id' not in session:
        flash('Você precisa estar logado para fazer um agendamento.')
        return redirect('/login')
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    if request.method == 'POST':
        equipe_id = request.form['equipe_id']
        servicos_id = request.form['servicos_id']
        data_hora = request.form['data_hora']
        
        # Validar horário
        try:
            data_hora_dt = datetime.datetime.fromisoformat(data_hora)
            dia_da_semana = data_hora_dt.weekday()
            hora = data_hora_dt.hour
            
            if dia_da_semana == 6:  # Sábado
                if hora < 13 or hora >= 18:
                    raise ValueError("O horário de agendamento para sábado deve estar entre 13:00 e 18:00.")
            elif dia_da_semana == 0:  # Domingo
                raise ValueError("Não é possível agendar no domingo.")
            else:  # Segunda a sexta
                if hora < 9 or hora >= 20:
                    raise ValueError("O horário de agendamento durante a semana deve estar entre 09:00 e 20:00.")
            
            status = 'pendente'  # Status inicial do agendamento
            
            conn.execute('''
                INSERT INTO Agendamentos (user_id, equipe_id, servicos_id, data_hora, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, equipe_id, servicos_id, data_hora, status))
            
            conn.commit()
            flash('Agendamento realizado com sucesso!')
        except ValueError as e:
            flash(f'Erro: {e}')
        except sqlite3.Error as e:
            flash(f'Erro ao tentar realizar o agendamento: {e}')
        
    equipe = conn.execute('SELECT equipe_id, nome FROM Equipe WHERE ativo = 1').fetchall()
    servicos = conn.execute('SELECT servicos_id, nome FROM Servicos').fetchall()
    conn.close()
    
    return render_template('agendamentocliente.html', equipe=equipe, servicos=servicos)


# Rota para gerenciamento de agendamentos
@app.route('/gerenciamentoagendamento', methods=['GET', 'POST'])
def gerenciar_agendamentos():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acesso negado. Apenas administradores podem acessar essa página.')
        return redirect(url_for('login'))  # Redirecionar para a página de login ou outra página
    conn = get_db_connection()

    if request.method == 'POST':
        if 'adicionar' in request.form:
            user_id = request.form['user_id']
            equipe_id = request.form['equipe_id']
            servicos_id = request.form['servicos_id']
            data_hora = request.form['data_hora']
            status = request.form['status']
            print(f"Adicionando agendamento: user_id={user_id}, equipe_id={equipe_id}, servicos_id={servicos_id}, data_hora={data_hora}, status={status}")  # Debug

            conn.execute('INSERT INTO Agendamentos (user_id, equipe_id, servicos_id, data_hora, status) VALUES (?, ?, ?, ?, ?)',
                         (user_id, equipe_id, servicos_id, data_hora, status))
            conn.commit()
            flash('Agendamento adicionado com sucesso!')

        elif 'editar' in request.form:
            agendamento_id = request.form['agendamento_id']
            user_id = request.form['user_id']
            equipe_id = request.form['equipe_id']
            servicos_id = request.form['servicos_id']
            data_hora = request.form['data_hora']
            status = request.form['status']
            print(f"Editando agendamento agendamento_id={agendamento_id}, user_id={user_id}, equipe_id={equipe_id}, servicos_id={servicos_id}, data_hora={data_hora}, status={status}")  # Debug
            
            conn.execute('UPDATE Agendamentos SET user_id = ?, equipe_id = ?, servicos_id = ?, data_hora = ?, status = ? WHERE agendamento_id = ?',
                         (user_id, equipe_id, servicos_id, data_hora, status, agendamento_id))
            conn.commit()
            flash('Agendamento atualizado com sucesso!')

    if request.args.get('excluir'):
        agendamento_id = request.args.get('excluir')
        print(f"Excluindo agendamento agendamento_id={agendamento_id}")  # Debug
        conn.execute('DELETE FROM Agendamentos WHERE agendamento_id = ?', (agendamento_id,))
        conn.commit()
        flash('Agendamento excluído com sucesso!')

    # Obter lista de agendamentos e outras informações necessárias
    agendamentos = conn.execute('SELECT * FROM Agendamentos').fetchall()
    usuarios = conn.execute('SELECT user_id, nome FROM Users').fetchall()
    equipe = conn.execute('SELECT equipe_id, nome FROM Equipe').fetchall()
    servicos = conn.execute('SELECT servicos_id, nome FROM Servicos').fetchall()
    conn.close()

    return render_template('gerenciamento_agendamentos.html', agendamentos=agendamentos, usuarios=usuarios, equipe=equipe, servicos=servicos)

# Rota para exibir a imagem do membro da equipe
@app.route('/imagem/<int:equipe_id>')
def imagem(equipe_id):
    conn = get_db_connection()
    equipe = conn.execute('SELECT imagem FROM Equipe WHERE equipe_id = ?', (equipe_id,)).fetchone()
    conn.close()

    if equipe and equipe['imagem']:
        return send_file(io.BytesIO(equipe['imagem']), mimetype='image/jpeg')
    return 'Imagem não encontrada', 404

#testar atualização da img
@app.route('/verificar_imagem/<int:equipe_id>')
def verificar_imagem(equipe_id):
    with get_db_connection() as conn:
        membro = conn.execute('SELECT imagem FROM Equipe WHERE equipe_id = ?', (equipe_id,)).fetchone()
        if membro:
            imagem_blob = membro['imagem']
            if imagem_blob:
                return send_file(io.BytesIO(imagem_blob), mimetype='image/jpeg')
        return 'Imagem não encontrada', 404

# gerenciamento de equipe com CRUD completo
@app.route('/gerenciamentoequipe', methods=['GET', 'POST'])
def gerenciar_equipe():
    with get_db_connection() as conn:
        if request.method == 'POST':
            if 'adicionar' in request.form:
                nome = request.form['nome']
                telefone = request.form['telefone']
                email = request.form['email']
                imagem = request.files.get('imagem')
                imagem_blob = imagem.read() if imagem else None
                print(f"Imagem adicionada: {imagem_blob}")

                conn.execute('INSERT INTO Equipe (nome, telefone, email, imagem) VALUES (?, ?, ?, ?)',
                             (nome, telefone, email, imagem_blob))
                conn.commit()
                flash('Membro da equipe adicionado com sucesso!')

            elif 'editar' in request.form:
                equipe_id = request.form['equipe_id']
                nome = request.form['nome']
                telefone = request.form['telefone']
                email = request.form['email']
                ativo = 1 if 'ativo' in request.form else 0
                imagem = request.files.get('imagem')
                imagem_blob = imagem.read() if imagem else None
                print(f"Imagem editada: {imagem_blob}")

                conn.execute('UPDATE Equipe SET nome = ?, telefone = ?, email = ?, ativo = ?, imagem = ? WHERE equipe_id = ?',
                             (nome, telefone, email, ativo, imagem_blob, equipe_id))
                conn.commit()
                flash('Membro da equipe atualizado com sucesso!')

        if request.args.get('excluir'):
            equipe_id = request.args.get('excluir')
            conn.execute('DELETE FROM Equipe WHERE equipe_id = ?', (equipe_id,))
            conn.commit()
            flash('Membro da equipe excluído com sucesso!')

        equipe = conn.execute('SELECT * FROM Equipe').fetchall()
    
    return render_template('gerenciamento_equipe.html', equipe=equipe)

# CRUD de usuários
@app.route('/gerenciamentousuarios', methods=['GET', 'POST'])

def gerenciar_usuarios():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acesso negado. Apenas administradores podem acessar essa página.')
        return redirect(url_for('login'))  # Redirecionar para a página de login ou outra página
    conn = get_db_connection()

    if request.method == 'POST':
        # Verifica se é para adicionar ou editar usuário
        if 'adicionar' in request.form:
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']
            telefone = request.form['telefone']
            role = request.form['role']
            print(f"Adicionando usuário: {nome}, {email}, {senha}, {telefone}, {role}")  # Debug

            # Adicionar um novo usuário 
            try:
                senha_hashed = generate_password_hash(senha)
                conn.execute('INSERT INTO Users (nome, email, senha, telefone, role) VALUES (?, ?, ?, ?, ?)',
                             (nome, email, senha_hashed, telefone, role))
                conn.commit()
                flash('Usuário adicionado com sucesso!')
            except sqlite3.IntegrityError as e:
                print(f"Erro ao adicionar: {e}")  # Debug
                flash('Erro: Email já está em uso.')

        elif 'editar' in request.form:
            # Editar um usuário existente 
            user_id = request.form['user_id']
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']
            telefone = request.form['telefone']
            role = request.form['role']
            senha_hashed = generate_password_hash(senha)
            print(f"Editando usuário user_id: {user_id}, Nome: {nome}, Email: {email}, Senha: {senha}, Telefone: {telefone}, Função: {role}")  # Debug
            senha_hashed = generate_password_hash(senha)
            
            conn.execute('UPDATE Users SET nome = ?, email = ?, senha = ?, telefone = ?, role = ? WHERE user_id = ?',
                         (nome, email, senha_hashed, telefone, role, user_id))
            conn.commit()
            flash('Usuário atualizado com sucesso!')

    # Excluir usuário (usando query params)
    if request.args.get('excluir'):
        user_id = request.args.get('excluir')
        print(f"Excluindo usuário user_id: {user_id}")  # Debug
        conn.execute('DELETE FROM Users WHERE user_id = ?', (user_id,))
        conn.commit()
        flash('Usuário excluído com sucesso!')

    # Obter a lista de usuários 'Users'
    usuarios = conn.execute('SELECT * FROM Users').fetchall()
    conn.close()

    return render_template('gerenciamento_usuarios.html', usuarios=usuarios)


# CRUD serviços

@app.route('/gerenciamentoservicos', methods=['GET', 'POST'])
def gerenciar_servicos():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acesso negado. Apenas administradores podem acessar essa página.')
        return redirect(url_for('login'))  # Redirecionar para a página de login ou outra página
    conn = get_db_connection()

    if request.method == 'POST':
        if 'adicionar' in request.form:
            nome = request.form['nome']
            descricao = request.form['descricao']
            preco = request.form['preco']
            duracao = request.form['duracao']
            print(f"Adicionando serviço: nome={nome}, descricao={descricao}, preco={preco}, duracao={duracao}")  # Debug

            try:
                conn.execute('INSERT INTO Servicos (nome, descricao, preco, duracao) VALUES (?, ?, ?, ?)',
                             (nome, descricao, preco, duracao))
                conn.commit()
                flash('Serviço adicionado com sucesso!')
            except sqlite3.IntegrityError as e:
                print(f"Erro ao adicionar: {e}")  # Debug
                flash('Erro ao adicionar o serviço.')

        elif 'editar' in request.form:
            servicos_id = request.form['servicos_id']
            nome = request.form['nome']
            descricao = request.form['descricao']
            preco = request.form['preco']
            duracao = request.form['duracao']
            print(f"Editando serviço servicos_id={servicos_id}, nome={nome}, descricao={descricao}, preco={preco}, duracao={duracao}")  # Debug
            
            conn.execute('UPDATE Servicos SET nome = ?, descricao = ?, preco = ?, duracao = ? WHERE servicos_id = ?',
                         (nome, descricao, preco, duracao, servicos_id))
            conn.commit()
            flash('Serviço atualizado com sucesso!')

    if request.args.get('excluir'):
        servicos_id = request.args.get('excluir')
        print(f"Excluindo serviço servicos_id={servicos_id}")  # Debug
        conn.execute('DELETE FROM Servicos WHERE servicos_id = ?', (servicos_id,))
        conn.commit()
        flash('Serviço excluído com sucesso!')

    servicos = conn.execute('SELECT * FROM Servicos').fetchall()
    conn.close()

    return render_template('gerenciamento_servicos.html', servicos=servicos)

if __name__ == '__main__':
    create_tables()  # Criação das tabelas na inicialização
    app.run(debug=True)
