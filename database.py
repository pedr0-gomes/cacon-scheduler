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

            -- Escala da equipe por dia da semana (0=seg … 6=dom), horários em minutos
            CREATE TABLE IF NOT EXISTS escala (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_semana INTEGER NOT NULL,
                funcao TEXT NOT NULL,
                entrada INTEGER NOT NULL,
                saida INTEGER NOT NULL,
                alm_ini INTEGER NOT NULL,
                alm_fim INTEGER NOT NULL
            );

            -- Ajustes editados pela tela Configuração (chave → valor)
            CREATE TABLE IF NOT EXISTS configuracao (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            );
        """)

        # Primeira execução: semeia a escala com o padrão do scheduler
        if not db.execute("SELECT 1 FROM configuracao WHERE chave='escala_inicializada'").fetchone():
            from scheduler import ESCALA_PADRAO
            for dia, profissionais in ESCALA_PADRAO.items():
                _inserir_escala(db, dia, profissionais)
            db.execute("INSERT INTO configuracao (chave, valor) VALUES ('escala_inicializada', '1')")

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
            # Sessões feitas antes de o paciente entrar no sistema (carga inicial)
            "ALTER TABLE pacientes ADD COLUMN ciclos_previos INTEGER NOT NULL DEFAULT 0",
            # Poltrona em que o paciente foi puncionado — fixa a partir daí
            "ALTER TABLE agendamentos ADD COLUMN poltrona INTEGER",
        ]
        for sql in _migracoes:
            try:
                db.execute(sql)
            except Exception:
                pass  # coluna já existe


def _inserir_escala(db, dia: int, profissionais):
    db.executemany(
        "INSERT INTO escala (dia_semana, funcao, entrada, saida, alm_ini, alm_fim) VALUES (?,?,?,?,?,?)",
        [(dia, p.funcao, p.entrada, p.saida, p.alm_ini, p.alm_fim) for p in profissionais],
    )


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
            SELECT a.id AS ag_id, a.status, a.confirmado, a.paciente_id, a.ordem_medica, a.poltrona,
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
                "poltrona":             r["poltrona"],
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
    ciclos_previos=0,
) -> int:
    """ciclos_previos só vale para paciente novo: num cadastro existente a contagem
    já vem do cadastro + das retiradas registradas (corrigir em Configuração)."""
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
                     num_prontuario, telefone, cor_qt_override, ciclos_previos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome, nome_mae, data_nascimento, protocolo,
                  pre_override, qt_override_min, intervalo_ciclo_dias,
                  total_ciclos, int(is_convenio), flexibilidade, municipio,
                  num_prontuario, telefone, cor_qt_override, ciclos_previos or 0))
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


def fixar_poltrona(ag_id: int, poltrona: int | None):
    """Grava (ou limpa) a poltrona em que o paciente foi puncionado."""
    with get_db() as db:
        db.execute("UPDATE agendamentos SET poltrona=? WHERE id=?", (poltrona, ag_id))


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
    """Conta sessões concluídas: as feitas antes do sistema (ciclos_previos)
    + as registradas aqui (retirada registrada)."""
    with get_db() as db:
        previos = db.execute(
            "SELECT COALESCE(ciclos_previos, 0) FROM pacientes WHERE id = ?", (paciente_id,)
        ).fetchone()
        no_sistema = db.execute("""
            SELECT COUNT(DISTINCT a.id)
            FROM agendamentos a
            JOIN eventos e ON e.agendamento_id = a.id
            WHERE a.paciente_id = ? AND e.tipo = 'retirada'
              AND a.status != 'cancelado'
        """, (paciente_id,)).fetchone()[0]
        return (previos[0] if previos else 0) + no_sistema


# ---------------------------------------------------------------------------
# Cadastro de pacientes (tela Configuração → Pacientes)
# ---------------------------------------------------------------------------

CAMPOS_PACIENTE = (
    "nome", "nome_mae", "data_nascimento", "protocolo", "pre_override",
    "qt_override_min", "intervalo_ciclo_dias", "total_ciclos", "ciclos_previos",
    "is_convenio", "flexibilidade", "num_prontuario", "telefone", "cor_qt_override",
)


def paciente_por_nome(nome: str) -> int | None:
    with get_db() as db:
        r = db.execute("SELECT id FROM pacientes WHERE nome = ?", (nome,)).fetchone()
        return r["id"] if r else None


def _proximo_agendamento(db, paciente_id: int):
    """Próxima sessão (hoje ou depois) ainda não iniciada — a que o cadastro edita."""
    from datetime import date
    return db.execute("""
        SELECT a.id, a.data_sessao FROM agendamentos a
        WHERE a.paciente_id = ? AND a.data_sessao >= ? AND a.status != 'cancelado'
          AND NOT EXISTS (SELECT 1 FROM eventos e WHERE e.agendamento_id = a.id)
        ORDER BY a.data_sessao LIMIT 1
    """, (paciente_id, date.today().isoformat())).fetchone()


def listar_pacientes() -> list:
    with get_db() as db:
        rows = db.execute("SELECT * FROM pacientes ORDER BY nome").fetchall()
        result = []
        for r in rows:
            prox = _proximo_agendamento(db, r["id"])
            result.append({
                **dict(r),
                "proxima_sessao": prox["data_sessao"] if prox else None,
            })
    for p in result:
        p["ciclo_atual"] = ciclo_atual(p["id"])
    return result


def get_paciente(paciente_id: int) -> dict | None:
    with get_db() as db:
        r = db.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
        if not r:
            return None
        prox = _proximo_agendamento(db, paciente_id)
        return {**dict(r), "proxima_sessao": prox["data_sessao"] if prox else None}


def cadastrar_paciente(dados: dict, data_proxima: str) -> int:
    """Carga inicial: cria o paciente e a próxima sessão já como 'agendado'."""
    valores = {c: dados.get(c) for c in CAMPOS_PACIENTE}
    with get_db() as db:
        cols = ", ".join(valores)
        marcas = ", ".join("?" for _ in valores)
        cur = db.execute(f"INSERT INTO pacientes ({cols}) VALUES ({marcas})", tuple(valores.values()))
        pac_id = cur.lastrowid
        db.execute(
            "INSERT INTO agendamentos (paciente_id, data_sessao, status) VALUES (?, ?, 'agendado')",
            (pac_id, data_proxima),
        )
        return pac_id


def atualizar_paciente(paciente_id: int, dados: dict, data_proxima: str):
    """Corrige o cadastro e move (ou cria) a próxima sessão ainda não iniciada."""
    valores = {c: dados.get(c) for c in CAMPOS_PACIENTE}
    with get_db() as db:
        sets = ", ".join(f"{c}=?" for c in valores)
        db.execute(f"UPDATE pacientes SET {sets} WHERE id=?", (*valores.values(), paciente_id))
        prox = _proximo_agendamento(db, paciente_id)
        if prox:
            db.execute("UPDATE agendamentos SET data_sessao=? WHERE id=?", (data_proxima, prox["id"]))
        else:
            db.execute(
                "INSERT INTO agendamentos (paciente_id, data_sessao, status) VALUES (?, ?, 'agendado')",
                (paciente_id, data_proxima),
            )


def remover_paciente(paciente_id: int) -> bool:
    """Apaga um cadastro feito por engano. Recusa (False) se o paciente já tem
    sessão registrada no painel — esse histórico não se apaga."""
    with get_db() as db:
        tem_historico = db.execute("""
            SELECT 1 FROM eventos e JOIN agendamentos a ON a.id = e.agendamento_id
            WHERE a.paciente_id = ? LIMIT 1
        """, (paciente_id,)).fetchone()
        if tem_historico:
            return False
        db.execute("""DELETE FROM intercorrencias WHERE agendamento_id IN
                      (SELECT id FROM agendamentos WHERE paciente_id = ?)""", (paciente_id,))
        db.execute("DELETE FROM agendamentos WHERE paciente_id = ?", (paciente_id,))
        db.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
        return True


# ---------------------------------------------------------------------------
# Escala da equipe (tela Configuração → Escala)
# ---------------------------------------------------------------------------

def get_escala_semana() -> dict:
    """{dia_semana: [linha, ...]} com as 7 chaves, ordenado por função e entrada."""
    semana = {d: [] for d in range(7)}
    with get_db() as db:
        for r in db.execute("SELECT * FROM escala ORDER BY dia_semana, funcao, entrada, id"):
            semana[r["dia_semana"]].append(dict(r))
    return semana


def salvar_profissional(prof_id: int | None, dia: int, funcao: str,
                        entrada: int, saida: int, alm_ini: int, alm_fim: int):
    with get_db() as db:
        if prof_id:
            db.execute(
                "UPDATE escala SET funcao=?, entrada=?, saida=?, alm_ini=?, alm_fim=? WHERE id=?",
                (funcao, entrada, saida, alm_ini, alm_fim, prof_id),
            )
        else:
            db.execute(
                "INSERT INTO escala (dia_semana, funcao, entrada, saida, alm_ini, alm_fim) VALUES (?,?,?,?,?,?)",
                (dia, funcao, entrada, saida, alm_ini, alm_fim),
            )


def remover_profissional(prof_id: int):
    with get_db() as db:
        db.execute("DELETE FROM escala WHERE id=?", (prof_id,))


def copiar_escala(origem: int, destinos: list):
    """Substitui a escala de cada dia em destinos pela do dia origem."""
    with get_db() as db:
        linhas = db.execute(
            "SELECT funcao, entrada, saida, alm_ini, alm_fim FROM escala WHERE dia_semana=?", (origem,)
        ).fetchall()
        for d in destinos:
            if d == origem:
                continue
            db.execute("DELETE FROM escala WHERE dia_semana=?", (d,))
            db.executemany(
                "INSERT INTO escala (dia_semana, funcao, entrada, saida, alm_ini, alm_fim) VALUES (?,?,?,?,?,?)",
                [(d, *tuple(l)) for l in linhas],
            )


def restaurar_escala_padrao(dia: int):
    from scheduler import ESCALA_PADRAO
    with get_db() as db:
        db.execute("DELETE FROM escala WHERE dia_semana=?", (dia,))
        _inserir_escala(db, dia, ESCALA_PADRAO[dia])


# ---------------------------------------------------------------------------
# Parâmetros editáveis (tela Configuração → Parâmetros)
# ---------------------------------------------------------------------------

def get_parametros() -> dict:
    """{nome: valor em texto} só dos parâmetros alterados pela tela."""
    with get_db() as db:
        rows = db.execute("SELECT chave, valor FROM configuracao WHERE chave LIKE 'param:%'").fetchall()
    return {r["chave"][6:]: r["valor"] for r in rows}


def salvar_parametros(valores: dict):
    """Grava {nome: valor}; None apaga (volta ao padrão)."""
    with get_db() as db:
        for nome, valor in valores.items():
            if valor is None:
                db.execute("DELETE FROM configuracao WHERE chave=?", (f"param:{nome}",))
            else:
                db.execute(
                    "INSERT INTO configuracao (chave, valor) VALUES (?, ?) "
                    "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
                    (f"param:{nome}", str(valor)),
                )


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


def proxima_data_com_vaga(paciente_id: int, a_partir: str, intervalo_dias: int) -> str | None:
    """
    Retorna a primeira data >= a_partir com vaga no pool agendado do dia
    (derivado da escala — dia sem equipe não tem vaga).
    Retorna None se não encontrar em 60 dias.
    """
    from datetime import date, timedelta
    from scheduler import capacidade_do_dia
    inicio = date.fromisoformat(a_partir)
    candidata = inicio
    for _ in range(60):
        data_str = candidata.isoformat()
        with get_db() as db:
            ocupadas = db.execute("""
                SELECT COUNT(*) FROM agendamentos
                WHERE data_sessao=? AND status NOT IN ('cancelado')
            """, (data_str,)).fetchone()[0]
        if ocupadas < capacidade_do_dia(dia_semana=candidata.weekday())["n_agendado"]:
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


def get_sessoes_concluidas() -> list:
    """Todas as sessões com retirada registrada: campos que definem o tempo planejado
    + eventos (tipo → 'HH:MM'). Base do relatório planejado × real por protocolo."""
    with get_db() as db:
        rows = db.execute("""
            SELECT a.id AS ag_id, p.nome, p.protocolo, p.pre_override,
                   p.qt_override_min, p.cor_qt_override, p.flexibilidade, p.is_convenio
            FROM agendamentos a
            JOIN pacientes p ON p.id = a.paciente_id
            WHERE a.status != 'cancelado'
              AND EXISTS (SELECT 1 FROM eventos e WHERE e.agendamento_id = a.id AND e.tipo = 'retirada')
        """).fetchall()
        result = []
        for r in rows:
            evs = db.execute(
                "SELECT tipo, registrado_em FROM eventos WHERE agendamento_id = ? ORDER BY id",
                (r["ag_id"],)
            ).fetchall()
            result.append({**dict(r), "eventos": {e["tipo"]: e["registrado_em"] for e in evs}})
        return result


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
