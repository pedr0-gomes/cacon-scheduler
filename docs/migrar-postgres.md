# Migração SQLite → PostgreSQL

Fazer quando o hospital tiver servidor dedicado (TI confirmar).

## Quando migrar

- Servidor Linux acessível pela rede interna do CACON
- Mais de um computador escrevendo simultaneamente (risco de lock no SQLite mesmo com WAL)
- Volume de dados justifica: > 5.000 agendamentos ou > 50 usuários simultâneos

## Passos

### 1. Instalar PostgreSQL no servidor

```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl enable --now postgresql
sudo -u postgres createuser cacon
sudo -u postgres createdb cacon_db -O cacon
sudo -u postgres psql -c "ALTER USER cacon PASSWORD 'senha-forte';"
```

### 2. Exportar SQLite para SQL

```bash
# Instalar pgloader
sudo apt install pgloader

# Migrar direto
pgloader cacon.db postgresql://cacon:senha-forte@localhost/cacon_db
```

pgloader traduz automaticamente tipos SQLite → PostgreSQL e copia os dados.

### 3. Adaptar o código

Três mudanças em `database.py`:

**a) Dependência**
```toml
# pyproject.toml
dependencies = [..., "psycopg2-binary>=2.9"]
```

**b) Conexão**
```python
import os, psycopg2, psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")  # postgresql://cacon:senha@host/cacon_db

@contextmanager
def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        # psycopg2 usa autocommit=False por padrão
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**c) Placeholders**: substituir `?` por `%s` em todas as queries (ou usar SQLAlchemy).

### 4. Variável de ambiente

```bash
# No servidor
export DATABASE_URL="postgresql://cacon:senha-forte@localhost/cacon_db"
```

### 5. Backup com PostgreSQL

```bash
# Substituir backup.py por:
pg_dump postgresql://cacon:senha@localhost/cacon_db > backups/cacon_$(date +%Y-%m-%d).sql
```

## WAL mode (SQLite — ativo agora)

Enquanto PostgreSQL não está disponível, WAL mode está habilitado em `get_db()`.
Reduz locks em leitura concorrente (painel tablet + triagem computador simultâneos).
