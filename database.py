import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "cacon.db"


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                nome_mae TEXT,
                data_nascimento TEXT,
                protocolo TEXT NOT NULL,
                pre_override TEXT,
                qt_override_min INTEGER,
                intervalo_ciclo_dias INTEGER,
                total_ciclos INTEGER,
                is_convenio INTEGER NOT NULL DEFAULT 0,
                flexibilidade TEXT NOT NULL DEFAULT 'alta',
                municipio TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
                data_sessao TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'agendado',
                confirmado TEXT DEFAULT NULL,
                ordem_medica INTEGER NOT NULL DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agendamento_id INTEGER NOT NULL REFERENCES agendamentos(id),
                tipo TEXT NOT NULL,
                registrado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intercorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agendamento_id INTEGER NOT NULL REFERENCES agendamentos(id),
                texto TEXT NOT NULL,
                registrado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS log_auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acao TEXT NOT NULL,
                agendamento_id INTEGER,
                detalhes TEXT,
                usuario TEXT NOT NULL DEFAULT 'sistema',
                registrado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS observacoes_relatorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                parametro TEXT NOT NULL,
                texto TEXT NOT NULL,
                registrado_em TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(data, parametro)
            );
        """)

        # Migração incremental — adiciona colunas se não existirem
        _migracoes = [
            "ALTER TABLE pacientes ADD COLUMN is_convenio INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE pacientes ADD COLUMN flexibilidade TEXT NOT NULL DEFAULT 'alta'",
            "ALTER TABLE pacientes ADD COLUMN municipio TEXT",
            "ALTER TABLE agendamentos ADD COLUMN ordem_medica INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE pacientes ADD COLUMN total_ciclos INTEGER",
            "ALTER TABLE agendamentos ADD COLUMN confirmado TEXT DEFAULT NULL",
            "ALTER TABLE pacientes ADD COLUMN num_paciente TEXT",
            "ALTER TABLE pacientes ADD COLUMN num_prontuario TEXT",
            "ALTER TABLE pacientes ADD COLUMN telefone TEXT",
            "ALTER TABLE pacientes ADD COLUMN cor_qt_override TEXT",
        ]
        for sql in _migracoes:
            try:
                db.execute(sql)
            except Exception:
                pass  # coluna já existe


@contextmanager
def get_db():
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


def get_dia(data: str) -> list:
    with get_db() as db:
        rows = db.execute("""
            SELECT a.id AS ag_id, a.status, a.confirmado, a.paciente_id, a.ordem_medica,
                   p.nome, p.nome_mae, p.data_nascimento,
                   p.protocolo, p.pre_override, p.qt_override_min,
                   p.intervalo_ciclo_dias, p.total_ciclos,
                   p.is_convenio, p.flexibilidade, p.municipio,
                   p.num_prontuario, p.telefone, p.cor_qt_override
            FROM agendamentos a
            JOIN pacientes p ON p.id = a.paciente_id
            WHERE a.data_sessao = ? AND a.status != 'cancelado'
            ORDER BY a.id
        """, (data,)).fetchall()

        result = []
        for r in rows:
            ag_id = r["ag_id"]
            evs = db.execute(
                "SELECT tipo, registrado_em FROM eventos WHERE agendamento_id = ?",
                (ag_id,)
            ).fetchall()
            ints = db.execute(
                "SELECT texto FROM intercorrencias WHERE agendamento_id = ? ORDER BY id",
                (ag_id,)
            ).fetchall()
            has_proxima = db.execute(
                "SELECT COUNT(*) FROM agendamentos "
                "WHERE paciente_id = ? AND data_sessao > ? AND status != 'cancelado'",
                (r["paciente_id"], data)
            ).fetchone()[0] > 0
            result.append({
                "ag_id":                ag_id,
                "status":               r["status"],
                "confirmado":           r["confirmado"],
                "paciente_id":          r["paciente_id"],
                "ordem_medica":         r["ordem_medica"],
                "nome":                 r["nome"],
                "nome_mae":             r["nome_mae"],
                "data_nascimento":      r["data_nascimento"],
                "protocolo":            r["protocolo"],
                "pre_override":         r["pre_override"],
                "qt_override_min":      r["qt_override_min"],
                "intervalo_ciclo_dias": r["intervalo_ciclo_dias"],
                "total_ciclos":         r["total_ciclos"],
                "is_convenio":          bool(r["is_convenio"]),
                "flexibilidade":        r["flexibilidade"],
                "municipio":            r["municipio"],
                "num_prontuario":       r["num_prontuario"],
                "telefone":             r["telefone"],
                "cor_qt_override":      r["cor_qt_override"],
                "eventos":              {e["tipo"]: e["registrado_em"] for e in evs},
                "intercorrencias":      [i["texto"] for i in ints],
                "has_proxima":          has_proxima,
            })
        return result


def criar_agendamento(
    nome, nome_mae, data_nascimento, protocolo,
    pre_override, qt_override_min, intervalo_ciclo_dias, data_sessao,
    is_convenio=False, flexibilidade="alta", municipio=None, ordem_medica=0,
    total_ciclos=None, num_prontuario=None, telefone=None, cor_qt_override=None,
) -> int:
    with get_db() as db:
        existing_pac = db.execute(
            "SELECT id FROM pacientes WHERE nome = ?", (nome,)
        ).fetchone()

        if existing_pac:
            pac_id = existing_pac["id"]
            db.execute("""
                UPDATE pacientes
                SET protocolo=?, pre_override=?, qt_override_min=?,
                    intervalo_ciclo_dias=COALESCE(?, intervalo_ciclo_dias),
                    total_ciclos=COALESCE(?, total_ciclos),
                    is_convenio=?, flexibilidade=?,
                    municipio=COALESCE(?, municipio),
                    num_prontuario=COALESCE(?, num_prontuario),
                    telefone=COALESCE(?, telefone),
                    cor_qt_override=COALESCE(?, cor_qt_override)
                WHERE id=?
            """, (protocolo, pre_override, qt_override_min, intervalo_ciclo_dias,
                  total_ciclos, int(is_convenio), flexibilidade, municipio,
                  num_prontuario, telefone, cor_qt_override, pac_id))
        else:
            cur = db.execute("""
                INSERT INTO pacientes
                    (nome, nome_mae, data_nascimento, protocolo,
                     pre_override, qt_override_min, intervalo_ciclo_dias,
                     total_ciclos, is_convenio, flexibilidade, municipio,
                     num_prontuario, telefone, cor_qt_override)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome, nome_mae, data_nascimento, protocolo,
                  pre_override, qt_override_min, intervalo_ciclo_dias,
                  total_ciclos, int(is_convenio), flexibilidade, municipio,
                  num_prontuario, telefone, cor_qt_override))
            pac_id = cur.lastrowid

        existing_ag = db.execute(
            "SELECT id FROM agendamentos WHERE paciente_id=? AND data_sessao=?",
            (pac_id, data_sessao)
        ).fetchone()
        if existing_ag:
            return existing_ag["id"]

        cur = db.execute(
            "INSERT INTO agendamentos (paciente_id, data_sessao, status, ordem_medica) "
            "VALUES (?, ?, 'walk_in', ?)",
            (pac_id, data_sessao, ordem_medica)
        )
        return cur.lastrowid


def cancelar_agendamento(ag_id: int):
    with get_db() as db:
        db.execute("UPDATE agendamentos SET status='cancelado' WHERE id=?", (ag_id,))


def registrar_evento(ag_id: int, tipo: str, hora: str):
    with get_db() as db:
        exists = db.execute(
            "SELECT id FROM eventos WHERE agendamento_id=? AND tipo=?", (ag_id, tipo)
        ).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO eventos (agendamento_id, tipo, registrado_em) VALUES (?,?,?)",
                (ag_id, tipo, hora)
            )


def desfazer_evento(ag_id: int, tipo: str):
    with get_db() as db:
        db.execute("DELETE FROM eventos WHERE agendamento_id=? AND tipo=?", (ag_id, tipo))


def adicionar_intercorrencia(ag_id: int, texto: str):
    with get_db() as db:
        db.execute(
            "INSERT INTO intercorrencias (agendamento_id, texto) VALUES (?,?)",
            (ag_id, texto)
        )


def ciclo_atual(paciente_id: int) -> int:
    """Conta sessões concluídas (retirada registrada) do paciente."""
    with get_db() as db:
        return db.execute("""
            SELECT COUNT(DISTINCT a.id)
            FROM agendamentos a
            JOIN eventos e ON e.agendamento_id = a.id
            WHERE a.paciente_id = ? AND e.tipo = 'retirada'
              AND a.status != 'cancelado'
        """, (paciente_id,)).fetchone()[0]


def reagendar(ag_id: int, nova_data: str):
    """Move agendamento para nova data preservando histórico de ciclo."""
    with get_db() as db:
        db.execute(
            "UPDATE agendamentos SET data_sessao=?, status='reagendado' WHERE id=?",
            (nova_data, ag_id)
        )


def get_historico_paciente(paciente_id: int) -> dict:
    with get_db() as db:
        pac = db.execute(
            "SELECT * FROM pacientes WHERE id=?", (paciente_id,)
        ).fetchone()
        if not pac:
            return None

        ags = db.execute("""
            SELECT id, data_sessao, status, confirmado
            FROM agendamentos
            WHERE paciente_id=? AND status != 'cancelado'
            ORDER BY data_sessao
        """, (paciente_id,)).fetchall()

        sessoes = []
        for i, a in enumerate(ags, 1):
            evs = db.execute(
                "SELECT tipo, registrado_em FROM eventos WHERE agendamento_id=?",
                (a["id"],)
            ).fetchall()
            ints = db.execute(
                "SELECT texto FROM intercorrencias WHERE agendamento_id=? ORDER BY id",
                (a["id"],)
            ).fetchall()

            ev_dict = {e["tipo"]: e["registrado_em"] for e in evs}

            # duração real
            duracao = None
            if "punção" in ev_dict and "retirada" in ev_dict:
                from datetime import datetime
                fmt = "%H:%M"
                try:
                    t0 = datetime.strptime(ev_dict["punção"], fmt)
                    t1 = datetime.strptime(ev_dict["retirada"], fmt)
                    duracao = int((t1 - t0).total_seconds() / 60)
                except Exception:
                    pass

            sessoes.append({
                "ag_id":           a["id"],
                "data_sessao":     a["data_sessao"],
                "status":          a["status"],
                "confirmado":      a["confirmado"],
                "numero_ciclo":    i,
                "eventos":         ev_dict,
                "intercorrencias": [x["texto"] for x in ints],
                "duracao_real_min": duracao,
            })

        return {
            "paciente_id":  pac["id"],
            "nome":         pac["nome"],
            "protocolo":    pac["protocolo"],
            "total_ciclos": pac["total_ciclos"],
            "ciclo_atual":  ciclo_atual(paciente_id),
            "sessoes":      sessoes,
        }


N_AGENDADO = 20


def proxima_data_com_vaga(paciente_id: int, a_partir: str, intervalo_dias: int) -> str | None:
    """
    Retorna a primeira data >= a_partir com vaga no pool agendado.
    Retorna None se não encontrar em 60 dias.
    """
    from datetime import date, timedelta
    inicio = date.fromisoformat(a_partir)
    candidata = inicio
    for _ in range(60):
        data_str = candidata.isoformat()
        with get_db() as db:
            ocupadas = db.execute("""
                SELECT COUNT(*) FROM agendamentos
                WHERE data_sessao=? AND status NOT IN ('cancelado')
            """, (data_str,)).fetchone()[0]
        if ocupadas < N_AGENDADO:
            return data_str
        candidata += timedelta(days=1)
    return None


def get_horizonte(dias: int = 30) -> list:
    """Pacientes com ciclo ativo, ordenados por data esperada de retorno."""
    from datetime import date, timedelta
    hoje = date.today().isoformat()

    with get_db() as db:
        rows = db.execute("""
            SELECT
                p.id AS paciente_id, p.nome, p.protocolo,
                p.total_ciclos, p.intervalo_ciclo_dias,
                MAX(a.data_sessao) AS ultima_sessao
            FROM pacientes p
            JOIN agendamentos a ON a.paciente_id = p.id
            WHERE a.status != 'cancelado'
            GROUP BY p.id
            HAVING ultima_sessao IS NOT NULL AND p.intervalo_ciclo_dias IS NOT NULL
        """).fetchall()

        result = []
        for r in rows:
            try:
                ultima = date.fromisoformat(r["ultima_sessao"])
                proxima = ultima + timedelta(days=r["intervalo_ciclo_dias"])
            except Exception:
                continue

            ja_ag = db.execute("""
                SELECT data_sessao FROM agendamentos
                WHERE paciente_id=? AND data_sessao > ? AND status != 'cancelado'
                ORDER BY data_sessao LIMIT 1
            """, (r["paciente_id"], r["ultima_sessao"])).fetchone()

            dias_restantes = (proxima - date.today()).days

            result.append({
                "paciente_id":      r["paciente_id"],
                "nome":             r["nome"],
                "protocolo":        r["protocolo"],
                "total_ciclos":     r["total_ciclos"],
                "ciclo_atual":      ciclo_atual(r["paciente_id"]),
                "intervalo_dias":   r["intervalo_ciclo_dias"],
                "ultima_sessao":    r["ultima_sessao"],
                "proxima_esperada": proxima.isoformat(),
                "dias_restantes":   dias_restantes,
                "ja_agendado":      ja_ag["data_sessao"] if ja_ag else None,
                "situacao":         "agendado" if ja_ag else "aguardando",
                "duracao_mediana":  duracao_mediana_qt(r["paciente_id"]),
            })

        result.sort(key=lambda x: x["proxima_esperada"])
        limite = (date.today() + timedelta(days=dias)).isoformat()
        return [r for r in result if r["proxima_esperada"] <= limite]


def duracao_mediana_qt(paciente_id: int) -> int | None:
    """
    Retorna a mediana da duração real do QT (retirada - QT) em minutos
    para o paciente, calculada a partir do histórico de sessões.
    Retorna None se menos de 2 sessões com dados válidos.
    """
    from datetime import datetime
    fmt = "%H:%M"

    with get_db() as db:
        rows = db.execute("""
            SELECT
                qt_ev.registrado_em  AS qt_time,
                ret_ev.registrado_em AS ret_time
            FROM agendamentos a
            JOIN eventos qt_ev  ON qt_ev.agendamento_id  = a.id AND qt_ev.tipo  = 'QT'
            JOIN eventos ret_ev ON ret_ev.agendamento_id = a.id AND ret_ev.tipo = 'retirada'
            WHERE a.paciente_id = ? AND a.status != 'cancelado'
        """, (paciente_id,)).fetchall()

    duracoes = []
    for r in rows:
        try:
            t_qt  = datetime.strptime(r["qt_time"],  fmt)
            t_ret = datetime.strptime(r["ret_time"], fmt)
            d = int((t_ret - t_qt).total_seconds() / 60)
            if 10 <= d <= 600:
                duracoes.append(d)
        except Exception:
            pass

    if len(duracoes) < 2:
        return None

    duracoes.sort()
    n = len(duracoes)
    mid = n // 2
    if n % 2 == 1:
        return duracoes[mid]
    return int((duracoes[mid - 1] + duracoes[mid]) / 2)


def agendar_proxima(paciente_id: int, data_proxima: str, intervalo_dias: int) -> dict:
    """
    Retorna dict com:
      - 'status': 'agendado' | 'concluido' | 'sem_vaga'
      - 'data': data agendada (se status='agendado')
    """
    from datetime import date, timedelta
    from scheduler import CICLO_MULTIAPP

    with get_db() as db:
        pac = db.execute(
            "SELECT total_ciclos, protocolo FROM pacientes WHERE id=?", (paciente_id,)
        ).fetchone()
        total    = pac["total_ciclos"] if pac else None
        protocolo = pac["protocolo"]   if pac else None

    atual = ciclo_atual(paciente_id)
    if total is not None and atual >= total:
        return {"status": "concluido", "data": None}

    # Para protocolos multi-aplicação, recalcula intervalo e data-alvo
    # a partir da última sessão concluída, ignorando o valor passado pela UI.
    if protocolo in CICLO_MULTIAPP and atual >= 1:
        intervalos = CICLO_MULTIAPP[protocolo]
        intervalo_dias = intervalos[(atual - 1) % len(intervalos)]
        with get_db() as db:
            ultima = db.execute("""
                SELECT MAX(a.data_sessao)
                FROM agendamentos a
                JOIN eventos e ON e.agendamento_id = a.id AND e.tipo = 'retirada'
                WHERE a.paciente_id = ? AND a.status != 'cancelado'
            """, (paciente_id,)).fetchone()[0]
        if ultima:
            data_proxima = str(date.fromisoformat(ultima) + timedelta(days=intervalo_dias))

    data_disponivel = proxima_data_com_vaga(paciente_id, data_proxima, intervalo_dias)
    if not data_disponivel:
        return {"status": "sem_vaga", "data": None}

    with get_db() as db:
        db.execute(
            "UPDATE pacientes SET intervalo_ciclo_dias=? WHERE id=?",
            (intervalo_dias, paciente_id)
        )
        exists = db.execute(
            "SELECT id FROM agendamentos WHERE paciente_id=? AND data_sessao=?",
            (paciente_id, data_disponivel)
        ).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO agendamentos (paciente_id, data_sessao, status) VALUES (?,?,'agendado')",
                (paciente_id, data_disponivel)
            )
    return {"status": "agendado", "data": data_disponivel}


def registrar_log(acao: str, usuario: str, agendamento_id: int = None, detalhes: str = None):
    with get_db() as db:
        db.execute(
            "INSERT INTO log_auditoria (acao, agendamento_id, detalhes, usuario) VALUES (?,?,?,?)",
            (acao, agendamento_id, detalhes, usuario),
        )


def get_logs(limit: int = 200) -> list:
    with get_db() as db:
        rows = db.execute("""
            SELECT l.id, l.acao, l.agendamento_id, l.detalhes, l.usuario, l.registrado_em,
                   p.nome AS paciente_nome
            FROM log_auditoria l
            LEFT JOIN agendamentos a ON a.id = l.agendamento_id
            LEFT JOIN pacientes p ON p.id = a.paciente_id
            ORDER BY l.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def salvar_observacoes_dia(data: str, obs: dict):
    """obs = {parametro: texto}. Upsert por (data, parametro)."""
    with get_db() as db:
        for parametro, texto in obs.items():
            if texto:
                db.execute("""
                    INSERT INTO observacoes_relatorio (data, parametro, texto)
                    VALUES (?, ?, ?)
                    ON CONFLICT(data, parametro) DO UPDATE SET texto=excluded.texto,
                        registrado_em=datetime('now', 'localtime')
                """, (data, parametro, texto))
            else:
                db.execute(
                    "DELETE FROM observacoes_relatorio WHERE data=? AND parametro=?",
                    (data, parametro)
                )


def get_observacoes_dia(data: str) -> dict:
    with get_db() as db:
        rows = db.execute(
            "SELECT parametro, texto FROM observacoes_relatorio WHERE data=?", (data,)
        ).fetchall()
    return {r["parametro"]: r["texto"] for r in rows}


def get_relatorio_dia(data: str) -> dict:
    with get_db() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM agendamentos WHERE data_sessao=? AND status != 'cancelado'",
            (data,)
        ).fetchone()[0]

        concluidos = db.execute("""
            SELECT COUNT(DISTINCT a.id)
            FROM agendamentos a
            JOIN eventos e ON e.agendamento_id = a.id AND e.tipo = 'retirada'
            WHERE a.data_sessao = ? AND a.status != 'cancelado'
        """, (data,)).fetchone()[0]

        walk_ins = db.execute(
            "SELECT COUNT(*) FROM agendamentos WHERE data_sessao=? AND status='walk_in'",
            (data,)
        ).fetchone()[0]

        intercorrencias = db.execute("""
            SELECT i.texto, p.nome
            FROM intercorrencias i
            JOIN agendamentos a ON a.id = i.agendamento_id
            JOIN pacientes p ON p.id = a.paciente_id
            WHERE a.data_sessao = ?
            ORDER BY i.id
        """, (data,)).fetchall()

        return {
            "total":          total,
            "concluidos":     concluidos,
            "walk_ins":       walk_ins,
            "agendados":      total - walk_ins,
            "intercorrencias": [{"nome": r["nome"], "texto": r["texto"]} for r in intercorrencias],
        }
