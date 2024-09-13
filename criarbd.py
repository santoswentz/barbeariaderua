import sqlite3

# Conecta ao banco de dados (ou cria um novo se não existir)
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Criação da tabela Usuários
cursor.execute('''
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

# Criação da tabela Equipe
cursor.execute('''
CREATE TABLE IF NOT EXISTS Equipe (
    equipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT,
    email TEXT UNIQUE,
    data_admissao TEXT DEFAULT (datetime('now')),
    ativo INTEGER DEFAULT 1
    imagem_url BLOB  -- Nova coluna para armazenar o caminho da imagem
)
''')

# Criação da tabela Serviços
cursor.execute('''
CREATE TABLE IF NOT EXISTS Servicos (
    servicos_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    duracao INTEGER  -- duração em minutos
)
''')

# Criação da tabela Agendamentos
cursor.execute('''
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
)
''')

# Criação da tabela Login
cursor.execute('''
CREATE TABLE IF NOT EXISTS Login (
    login_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    data_hora_login TEXT DEFAULT (datetime('now')),
    data_hora_logout TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
)
''')

# Criação da tabela Cadastro
cursor.execute('''
CREATE TABLE IF NOT EXISTS Cadastro (
    cadastro_id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    data_cadastro TEXT DEFAULT (datetime('now'))
)
''')

# Salva as mudanças e fecha a conexão
conn.commit()
conn.close()

print("Banco de dados e tabelas criados com sucesso.")
