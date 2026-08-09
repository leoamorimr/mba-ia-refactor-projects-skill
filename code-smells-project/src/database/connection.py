"""Database connection factory.

Replaces the old module-level `db_connection = None` / `global` pattern
with a small class that owns its connection state. It's still exposed
through a module-level `get_db()` accessor for convenience (models call it
the same way controllers used to), but the state itself is encapsulated in
an instance that could be swapped out (e.g. for an in-memory sqlite DB in
tests) instead of being a bare global.
"""
import sqlite3

from werkzeug.security import generate_password_hash

from config.settings import DB_PATH

SEED_PRODUCTS = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

SEED_USERS = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


class DatabaseConnection:
    """Owns a single sqlite3 connection, created lazily on first use."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._connection = None

    def get_connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._create_schema()
            self._seed_if_empty()
        return self._connection

    def _create_schema(self):
        cursor = self._connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                descricao TEXT,
                preco REAL,
                estoque INTEGER,
                categoria TEXT,
                ativo INTEGER DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                email TEXT,
                senha TEXT,
                tipo TEXT DEFAULT 'cliente',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                status TEXT DEFAULT 'pendente',
                total REAL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_pedido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                produto_id INTEGER,
                quantidade INTEGER,
                preco_unitario REAL
            )
        """)
        self._connection.commit()

    def _seed_if_empty(self):
        cursor = self._connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        if cursor.fetchone()[0] != 0:
            return

        cursor.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            SEED_PRODUCTS,
        )

        usuarios_com_hash = [
            (nome, email, generate_password_hash(senha), tipo)
            for nome, email, senha, tipo in SEED_USERS
        ]
        cursor.executemany(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            usuarios_com_hash,
        )
        self._connection.commit()


_db_instance = DatabaseConnection(DB_PATH)


def get_db():
    return _db_instance.get_connection()


def init_db():
    return _db_instance.get_connection()
