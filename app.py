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
    barbeiros = conn.execute('SELECT equipe_id, nome, imagem FROM Equipe WHERE ativo = 1').fetchall()
    conn.close()
    return render_template('index.html', servicos=servicos, barbeiros=barbeiros)


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
        barbeiros = conn.execute('SELECT equipe_id, nome, imagem FROM Equipe WHERE ativo = 1').fetchall()
        conn.close()

        return render_template('cliente_dashboard.html', servicos=servicos, barbeiros=barbeiros)
    else:
        return redirect(url_for('login'))


# Painel do Adm
@app.route('/indexadmin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    else:
        return redirect(url_for('login'))

# Função para formatar a data/hora de forma humanizada
def formatar_data_hora(data_hora):
    return data_hora.strftime('%A, %d de %B de %Y, %H:%M')







def gerar_horarios_disponiveis(data, horarios_ocupados, dia_da_semana):
    horarios_disponiveis = []
    
    # Definir o intervalo de horário com base no dia da semana
    if dia_da_semana == 6:  # Sábado
        inicio_horario = 13  # 13:00
        fim_horario = 18  # 18:00
    elif dia_da_semana == 0:  # Domingo
        return []  # Domingo fechado, sem horários disponíveis
    else:  # Segunda a sexta
        inicio_horario = 9  # 09:00
        fim_horario = 20  # 20:00

    # Gerar todos os horários possíveis em intervalos de 30 minutos
    horario_atual = datetime.combine(data, datetime.min.time()) + timedelta(hours=inicio_horario)
    fim_horario_dt = datetime.combine(data, datetime.min.time()) + timedelta(hours=fim_horario)

    while horario_atual < fim_horario_dt:
        # Formatar o horário no mesmo formato da lista `horarios_ocupados`
        horario_formatado = horario_atual.strftime('%Y-%m-%d %H:%M')
        
        # Verificar se o horário não está ocupado
        if horario_formatado not in horarios_ocupados:
            horarios_disponiveis.append(horario_atual.strftime('%H:%M'))  # Adicionar apenas a hora no formato 'HH:MM'
        
        # Incrementar o horário em 30 minutos
        horario_atual += timedelta(minutes=30)
    
    return horarios_disponiveis








# Cliente agendar
@app.route('/agendamentocliente', methods=['GET', 'POST'])
def agendamento_cliente():
    if 'user_id' not in session:
        flash('Você precisa estar logado para fazer um agendamento.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    # Obter a data atual ou a data selecionada pelo cliente
    data_selecionada = request.args.get('data', datetime.now().date().isoformat())

    # Verificar os horários já reservados para o dia selecionado
    agendamentos_do_dia = conn.execute('''
        SELECT strftime('%Y-%m-%d %H:%M', data_hora) as data_hora 
        FROM Agendamentos 
        WHERE strftime('%Y-%m-%d', data_hora) = ? AND status = 'agendado'
    ''', (data_selecionada,)).fetchall()

    horarios_ocupados = [agendamento['data_hora'] for agendamento in agendamentos_do_dia]

    # Determinar o dia da semana
    dia_da_semana = datetime.strptime(data_selecionada, '%Y-%m-%d').weekday()

    # Gerar a lista de horários disponíveis
    horarios_disponiveis = gerar_horarios_disponiveis(datetime.strptime(data_selecionada, '%Y-%m-%d'), horarios_ocupados, dia_da_semana)

    if request.method == 'POST':
        equipe_id = request.form['equipe_id']
        servicos_id = request.form['servicos_id']
        data_hora_str = request.form['data_hora']  # Obtém o valor do campo datetime-local
        
        try:
            # Agora o input está no formato correto: '%Y-%m-%dT%H:%M'
            data_hora = datetime.strptime(data_hora_str, '%Y-%m-%dT%H:%M')

            # Inserir o agendamento no banco de dados
            conn.execute('''
                INSERT INTO Agendamentos (user_id, equipe_id, servicos_id, data_hora, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, equipe_id, servicos_id, data_hora, 'agendado'))
            conn.commit()
            flash('Agendamento realizado com sucesso!')
            return redirect(url_for('meus_agendamentos'))

        except ValueError as e:
            flash(f'Erro no formato da data/hora: {e}')
        except sqlite3.Error as e:
            flash(f'Erro ao tentar realizar o agendamento: {e}')

    equipe = conn.execute('SELECT equipe_id, nome FROM Equipe WHERE ativo = 1').fetchall()
    servicos = conn.execute('SELECT servicos_id, nome FROM Servicos').fetchall()
    conn.close()

    return render_template('agendamentocliente.html', equipe=equipe, servicos=servicos, horarios_disponiveis=horarios_disponiveis, data_selecionada=data_selecionada)

















# Página para visualizar agendamentos do usuário logado
# Página para visualizar agendamentos do usuário logado
@app.route('/meus_agendamentos')
def meus_agendamentos():
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar essa página.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    agendamentos = conn.execute('''
        SELECT A.agendamento_id, A.data_hora, A.status, 
               S.nome AS servico_nome, 
               E.nome AS equipe_nome
        FROM Agendamentos A
        JOIN Servicos S ON A.servicos_id = S.servicos_id
        JOIN Equipe E ON A.equipe_id = E.equipe_id
        WHERE A.user_id = ? AND A.status = 'agendado'
    ''', (user_id,)).fetchall()

    # Formatar as datas de forma mais amigável
    agendamentos_formatados = []
    for agendamento in agendamentos:
        try:
            data_hora_formatada = formatar_data_hora(datetime.strptime(agendamento['data_hora'], '%Y-%m-%dT%H:%M'))
        except ValueError:
            data_hora_formatada = agendamento['data_hora']  # Manter formato original em caso de erro

        agendamentos_formatados.append({
            'agendamento_id': agendamento['agendamento_id'],
            'data_hora': data_hora_formatada,
            'servico_nome': agendamento['servico_nome'],
            'equipe_nome': agendamento['equipe_nome'],
            'status': agendamento['status']
        })

    conn.close()
    return render_template('meus_agendamentos.html', agendamentos=agendamentos_formatados)





# Cancelar agendamento
@app.route('/cancelar_agendamento/<int:agendamento_id>', methods=['POST'])
def cancelar_agendamento(agendamento_id):
    if 'user_id' not in session:
        flash('Você precisa estar logado para realizar essa ação.')
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Buscar informações do agendamento
    agendamento = conn.execute('SELECT data_hora, status FROM Agendamentos WHERE agendamento_id = ?', (agendamento_id,)).fetchone()
    
    if agendamento is None:
        flash('Agendamento não encontrado.')
        return redirect(url_for('meus_agendamentos'))

    data_agendamento = datetime.strptime(agendamento['data_hora'], '%Y-%m-%dT%H:%M')
    agora = datetime.now()

    # Verificar se faltam menos de 24 horas para o agendamento
    if data_agendamento - agora < timedelta(hours=24):
        flash('Não é possível cancelar o agendamento com menos de 24 horas de antecedência.')
        return redirect(url_for('meus_agendamentos'))

    # Cancelar o agendamento
    conn.execute('UPDATE Agendamentos SET status = ? WHERE agendamento_id = ?', ('cancelado', agendamento_id))
    conn.commit()
    conn.close()

    flash('Agendamento cancelado com sucesso.')
    return redirect(url_for('meus_agendamentos'))

def formatar_data_hora(data_hora):
    return data_hora.strftime('%d/%m/%Y %H:%M')









# Rota para o gerenciamento de agendamentos
@app.route('/gerenciamentoagendamento', methods=['GET', 'POST'])
def gerenciamento_agendamento():
    conn = get_db_connection()

    # Lógica de Adição e Edição de Agendamentos (POST)
    if request.method == 'POST':
        if 'adicionar' in request.form:
            # Capturar os valores do formulário
            user_id = request.form['user_id']
            equipe_id = request.form['equipe_id']
            servicos_id = request.form['servicos_id']
            data_hora = request.form['data_hora']
            status = request.form['status']
            
            # Inserir novo agendamento no banco de dados
            conn.execute('INSERT INTO Agendamentos (user_id, equipe_id, servicos_id, data_hora, status) VALUES (?, ?, ?, ?, ?)',
                         (user_id, equipe_id, servicos_id, data_hora, status))
            conn.commit()
        
        elif 'editar' in request.form:
            # Editar agendamento existente
            agendamento_id = request.form['agendamento_id']
            user_id = request.form['user_id']
            equipe_id = request.form['equipe_id']
            servicos_id = request.form['servicos_id']
            data_hora = request.form['data_hora']
            status = request.form['status']
            
            conn.execute('UPDATE Agendamentos SET user_id = ?, equipe_id = ?, servicos_id = ?, data_hora = ?, status = ? WHERE agendamento_id = ?',
                         (user_id, equipe_id, servicos_id, data_hora, status, agendamento_id))
            conn.commit()

    # Lógica de Exclusão de Agendamentos (GET)
    excluir_id = request.args.get('excluir')
    if excluir_id:
        conn.execute('DELETE FROM Agendamentos WHERE agendamento_id = ?', (excluir_id,))
        conn.commit()
        return redirect(url_for('gerenciamento_agendamento'))

    # Lógica de Pesquisa e Filtros (GET)
    search = request.args.get('search', '')
    filtro = request.args.get('filtro', '')

    if search:
        # Pesquisa por nome de usuário, nome da equipe, serviço ou status
        query = '''
        SELECT agendamentos.*, users.nome AS user_nome, equipe.nome AS equipe_nome, servicos.nome AS servico_nome 
        FROM Agendamentos 
        JOIN Users ON Agendamentos.user_id = Users.user_id 
        JOIN Equipe ON Agendamentos.equipe_id = Equipe.equipe_id 
        JOIN Servicos ON Agendamentos.servicos_id = Servicos.servicos_id
        WHERE Users.nome LIKE ? OR Equipe.nome LIKE ? OR Servicos.nome LIKE ? OR Agendamentos.status LIKE ?
        '''
        search_term = f'%{search}%'
        agendamentos = conn.execute(query, (search_term, search_term, search_term, search_term)).fetchall()
    
    elif filtro == 'hoje':
        # Filtro para agendamentos de hoje
        hoje = datetime.now().strftime('%Y-%m-%d')
        query = '''
        SELECT agendamentos.*, users.nome AS user_nome, equipe.nome AS equipe_nome, servicos.nome AS servico_nome 
        FROM Agendamentos 
        JOIN Users ON Agendamentos.user_id = Users.user_id 
        JOIN Equipe ON Agendamentos.equipe_id = Equipe.equipe_id 
        JOIN Servicos ON Agendamentos.servicos_id = Servicos.servicos_id
        WHERE DATE(agendamentos.data_hora) = ?
        '''
        agendamentos = conn.execute(query, (hoje,)).fetchall()

    elif filtro == 'semana':
        # Filtro para agendamentos desta semana
        hoje = datetime.now()
        inicio_semana = hoje - timedelta(days=hoje.weekday())  # Segunda-feira desta semana
        fim_semana = inicio_semana + timedelta(days=6)  # Domingo desta semana
        query = '''
        SELECT agendamentos.*, users.nome AS user_nome, equipe.nome AS equipe_nome, servicos.nome AS servico_nome 
        FROM Agendamentos 
        JOIN Users ON Agendamentos.user_id = Users.user_id 
        JOIN Equipe ON Agendamentos.equipe_id = Equipe.equipe_id 
        JOIN Servicos ON Agendamentos.servicos_id = Servicos.servicos_id
        WHERE DATE(agendamentos.data_hora) BETWEEN ? AND ?
        '''
        agendamentos = conn.execute(query, (inicio_semana.strftime('%Y-%m-%d'), fim_semana.strftime('%Y-%m-%d'))).fetchall()

    else:
        # Consulta padrão sem pesquisa ou filtro
        query = '''
        SELECT agendamentos.*, users.nome AS user_nome, equipe.nome AS equipe_nome, servicos.nome AS servico_nome 
        FROM Agendamentos 
        JOIN Users ON Agendamentos.user_id = Users.user_id 
        JOIN Equipe ON Agendamentos.equipe_id = Equipe.equipe_id 
        JOIN Servicos ON Agendamentos.servicos_id = Servicos.servicos_id
        '''
        agendamentos = conn.execute(query).fetchall()

    # Coletar dados para as opções de formulário (usuarios, equipe, servicos)
    usuarios = conn.execute('SELECT * FROM Users').fetchall()
    equipe = conn.execute('SELECT * FROM Equipe').fetchall()
    servicos = conn.execute('SELECT * FROM Servicos').fetchall()

    conn.close()

    # Renderizar o template com os dados
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
    conn = get_db_connection()
    
    if request.method == 'POST':
        if 'adicionar' in request.form:
            nome = request.form['nome']
            telefone = request.form['telefone']
            email = request.form['email']
            imagem = request.files.get('imagem')
            
            if imagem:
                imagem = imagem.read()
            else:
                imagem = None

            conn.execute('INSERT INTO Equipe (nome, telefone, email, imagem) VALUES (?, ?, ?, ?)',
                         (nome, telefone, email, imagem))
            conn.commit()
            flash('Membro adicionado com sucesso!')
            return redirect(url_for('gerenciar_equipe'))

        elif 'editar' in request.form:
            equipe_id = request.form['equipe_id']
            nome = request.form['nome']
            telefone = request.form['telefone']
            email = request.form['email']
            imagem = request.files.get('imagem')

            if imagem and imagem.filename:
                imagem = imagem.read()
                conn.execute('UPDATE Equipe SET nome = ?, telefone = ?, email = ?, imagem = ? WHERE equipe_id = ?',
                             (nome, telefone, email, imagem, equipe_id))
            else:
                conn.execute('UPDATE Equipe SET nome = ?, telefone = ?, email = ? WHERE equipe_id = ?',
                             (nome, telefone, email, equipe_id))

            conn.commit()
            flash('Membro atualizado com sucesso!')
            return redirect(url_for('gerenciar_equipe'))

    elif request.args.get('excluir'):
        equipe_id = request.args.get('excluir')
        conn.execute('DELETE FROM Equipe WHERE equipe_id = ?', (equipe_id,))
        conn.commit()
        flash('Membro excluído com sucesso!')
        return redirect(url_for('gerenciar_equipe'))

    equipe = conn.execute('SELECT * FROM Equipe').fetchall()
    conn.close()
    return render_template('gerenciamento_equipe.html', equipe=equipe)


# CRUD de usuários
@app.route('/gerenciamentousuarios', methods=['GET', 'POST'])
def gerenciar_usuarios():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acesso negado. Apenas administradores podem acessar essa página.')
        return redirect(url_for('login'))  # Redirecionar para a página de login ou outra página
    
    conn = get_db_connection()

    # Verifica se é uma requisição POST para adicionar ou editar usuário
    if request.method == 'POST':
        if 'adicionar' in request.form:
            # Adiciona um novo usuário
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']
            telefone = request.form['telefone']
            role = request.form['role']
            senha_hashed = generate_password_hash(senha)
            
            try:
                conn.execute('INSERT INTO Users (nome, email, senha, telefone, role) VALUES (?, ?, ?, ?, ?)',
                             (nome, email, senha_hashed, telefone, role))
                conn.commit()
                flash('Usuário adicionado com sucesso!')
            except sqlite3.IntegrityError:
                flash('Erro: Email já está em uso.')

        elif 'editar' in request.form:
            # Edita um usuário existente
            user_id = request.form['user_id']
            nome = request.form['nome']
            email = request.form['email']
            senha = request.form['senha']
            telefone = request.form['telefone']
            role = request.form['role']
            senha_hashed = generate_password_hash(senha)

            conn.execute('UPDATE Users SET nome = ?, email = ?, senha = ?, telefone = ?, role = ? WHERE user_id = ?',
                         (nome, email, senha_hashed, telefone, role, user_id))
            conn.commit()
            flash('Usuário atualizado com sucesso!')

    # Verifica se é uma requisição GET para excluir usuário
    if request.args.get('excluir'):
        user_id = request.args.get('excluir')
        conn.execute('DELETE FROM Users WHERE user_id = ?', (user_id,))
        conn.commit()
        flash('Usuário excluído com sucesso!')

    # Lógica de pesquisa de usuários
    search = request.args.get('search', '')

    if search:
        # Pesquisa por nome, email, telefone ou função (role)
        search_term = f'%{search}%'
        query = '''
            SELECT * FROM Users 
            WHERE nome LIKE ? OR email LIKE ? OR telefone LIKE ? OR role LIKE ?
        '''
        usuarios = conn.execute(query, (search_term, search_term, search_term, search_term)).fetchall()
    else:
        # Exibe todos os usuários caso não haja pesquisa
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
