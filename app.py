from flask import Flask, render_template, redirect, url_for, request, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('barbearia.db')
    conn.row_factory = sqlite3.Row  # Permite acessar os resultados como dicionário
    return conn

# Criação do banco de dados e das tabelas
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de Usuários
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
    
    conn.commit()
    conn.close()

# Função para obter o usuário pelo e-mail
def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user

# Rota de registro de usuário
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

# Rota de login de usuário
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

# Painel do Administrador
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin_dashboard.html')
    else:
        return redirect(url_for('login'))

# Painel do Cliente
@app.route('/cliente_dashboard')
def cliente_dashboard():
    if 'role' in session and session['role'] == 'cliente':
        return render_template('cliente_dashboard.html')
    else:
        return redirect(url_for('login'))

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    create_tables()  # Criação das tabelas na inicialização
    app.run(debug=True)
