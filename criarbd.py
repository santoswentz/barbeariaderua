import sqlite3

# Conecta ao banco de dados (ou cria um novo se não existir)
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Criação da tabela Usuários
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
    );
''')
    
conn.execute('''
    CREATE TABLE IF NOT EXISTS Equipe (
        equipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT,
        email TEXT,
        data_admissao TEXT DEFAULT (datetime('now')),
        ativo INTEGER DEFAULT 1,
        imagem BLOB,
        horario_inicial TEXT NOT NULL,  -- Horário de trabalho inicial (formato HH:MM)
        horario_final TEXT NOT NULL     -- Horário de trabalho final (formato HH:MM)
    );
''')
    
conn.execute('''
    CREATE TABLE IF NOT EXISTS Servicos (
        servicos_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        preco REAL NOT NULL,
        duracao INTEGER,  -- duração em minutos
        duracaosimplificada INTEGER --Duração com 0 até 10 *exemplo*
    );
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS Agendamentos (
        agendamento_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        equipe_id INTEGER,
        servicos_id INTEGER,
        dia TEXT NOT NULL,
        horainicial TEXT NOT NULL,
        horafinal TEXT NOT NULL,
        status TEXT NOT NULL,
        data_cancelamento DATETIME,
        FOREIGN KEY (equipe_id) REFERENCES Equipe(equipe_id),
        FOREIGN KEY (servicos_id) REFERENCES Servicos(servicos_id),
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    );
''')


    # Criando a tabela Horarios
#conn.execute('''
#    CREATE TABLE IF NOT EXISTS Horarios (
 #       horario_id INTEGER PRIMARY KEY AUTOINCREMENT,
  #      horario TEXT NOT NULL
#    );
#''')
#Inserindo horários de 15 em 15 minutos na tabela Horarios
horarios = []
for hour in range(24):
    for minute in range(0, 60, 15):
        horarios.append(f"{hour:02d}:{minute:02d}")

for horario in horarios:
    conn.execute('INSERT INTO Horarios (horario) VALUES (?)', (horario,))

# Inserindo o usuário administrador com nome "adm" e senha "adm"
#conn.execute('''
#    INSERT INTO Users (nome, email, senha, role)
#   VALUES ('adm', 'adm@gmail.com', 'adm', 'admin')
#''')

# Salva as mudanças e fecha a conexão
conn.commit()
conn.close()

print("Banco de dados e tabelas criados com sucesso.")
