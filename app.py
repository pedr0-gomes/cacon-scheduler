from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
import json

from config import SENHA_TRIAGEM, SESSION_SECRET

# Alocação manual (16/11): a triagem escolhe horário e poltrona; o algoritmo de
# scheduler.gerar_escala fica no repositório mas não é chamado. Do scheduler só
# se usam os tempos por protocolo, as poltronas e os parâmetros editáveis.
from scheduler import (
    Paciente, PacienteManual, Sessao,
    PROTOCOLO, QT_MIN, PRE_MIN, COR_PRIORIDADE, INTERVALO_CICLO,
    _fmt, TAXA_NAO_CONFIRMACAO, TAXA_REACAO_ADVERSA,
    capacidade_do_dia,   # só nas telas de Configuração (informativo)
)
# Parâmetros editáveis (tempos, vazão, poltronas) são lidos como scheduler.X na
# hora do uso — mudam em tempo de execução pela tela Configuração → Parâmetros.
from database import (
    init_db, get_dia, criar_agendamento,
    cancelar_agendamento, registrar_evento, desfazer_evento,
    adicionar_intercorrencia, agendar_proxima, get_horizonte,
    duracao_mediana_qt, registrar_log, get_logs,
    get_relatorio_dia, salvar_observacoes_dia, get_observacoes_dia,
    get_sessoes_concluidas,
    listar_pacientes, get_paciente, paciente_por_nome,
    cadastrar_paciente, atualizar_paciente, remover_paciente,
    get_escala_semana, salvar_profissional, remover_profissional,
    copiar_escala, restaurar_escala_padrao,
    get_parametros, salvar_parametros, alocar, definir_horario,
)
import scheduler

PRE_LABEL = {
    "Z": "Z — sem pré-med (0 min)",
    "A": "A — mínima (15 min)",
    "B": "B — padrão (35 min)",
    "C": "C — longa com hidratação (90 min)",
}

PROTOCOLO_LABEL = {
    "gencitabina_mono":     "Gencitabina monoterapia",
    "trastuzumabe_manut":   "Trastuzumabe (manutenção)",
    "pemetrexede_mono":     "Pemetrexede monoterapia",
    "vinorelbina":          "Vinorelbina IV",
    "imunoterapia":         "Imunoterapia (Nivo/Pembro)",
    "vincristina":          "Vincristina",
    "bleomicina":           "Bleomicina",
    "bortezomibe_sc":       "Bortezomibe SC",
    "bevacizumabe":         "Bevacizumabe",
    "paclitaxel_semanal":   "Paclitaxel semanal",
    "ac":                   "AC (Doxo + Ciclo)",
    "fac":                  "FAC (5-FU + Doxo + Ciclo)",
    "tc":                   "TC (Docetaxel + Ciclo)",
    "cmf":                  "CMF",
    "docetaxel_mono":       "Docetaxel monoterapia",
    "cisplatina_semanal":   "Cisplatina semanal",
    "trastuzumabe_1dose":   "Trastuzumabe 1ª dose",
    "duplo_bloqueio":       "Duplo bloqueio (Pert + Tras)",
    "carbo_pem":            "Carboplatina + Pemetrexede",
    "carbo_paclit_semanal": "Carboplatina + Paclitaxel semanal",
    "gencit_carbo":         "Gencitabina + Carboplatina",
    "folfiri_d1":           "FOLFIRI D1",
    "docetaxel_prostata":   "Docetaxel (próstata)",
    "irinotecan_mono":      "Irinotecan monoterapia",
    "paclitaxel_q3w":       "Paclitaxel q3w (3h)",
    "folfox_d1":            "FOLFOX D1",
    "xelox_d1":             "XELOX D1",
    "tac":                  "TAC (Docetaxel + Doxo + Ciclo)",
    "gencit_cis":           "Gencitabina + Cisplatina",
    "abvd":                 "ABVD",
    "bep_d1":               "BEP D1",
    "chop":                 "CHOP",
    "cisplatina_plena":     "Cisplatina plena (≥50 mg/m²)",
    "oxaliplatina_mono":    "Oxaliplatina monoterapia",
    "carbo_paclit_q3w":     "Carboplatina + Paclitaxel q3w",
    "r_chop":               "R-CHOP",
    "etop_cis_d1":          "Etoposídeo + Cisplatina D1",
    "daratumumabe_1dose":   "Daratumumabe 1ª dose",
}

COR_LABEL = {
    "verde":    "🟢 Verde",
    "azul":     "🔵 Azul",
    "amarelo":  "🟡 Amarelo",
    "vermelho": "🔴 Vermelho",
}

GRUPOS_DROPDOWN = {
    "🟢 Verde — menos de 1h": [s for s, (c, _) in PROTOCOLO.items() if c == "verde"],
    "🔵 Azul — 1h a 2h":      [s for s, (c, _) in PROTOCOLO.items() if c == "azul"],
    "🟡 Amarelo — 2h a 4h":   [s for s, (c, _) in PROTOCOLO.items() if c == "amarelo"],
    "🔴 Vermelho — mais de 4h":[s for s, (c, _) in PROTOCOLO.items() if c == "vermelho"],
}

STATUS_LABEL = {
    "aguardando_puncao":        "Punção",
    "aguardando_preqt":         "Pré-QT",
    "aguardando_qt":            "QT",
    "aguardando_retirada":      "Retirada",
    "aguardando_higienizacao":  "Higienização",
    "livre":                    "Livre",
}

EVENTOS = ["punção", "pré-QT", "QT", "retirada", "higienização"]

ROTAS_ABERTAS = {"/painel", "/registrar", "/desfazer", "/proxima", "/anotar", "/login", "/static"}


def _usuario(request: Request) -> str:
    return "triagem" if request.session.get("autenticado") else "painel"

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        aberta = any(path == r or path.startswith(r + "/") for r in ROTAS_ABERTAS)
        if not aberta and not request.session.get("autenticado"):
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)

BASE_DIR = Path(__file__).parent

app = FastAPI()
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
init_db()


def _carregar_escalas():
    """Escala do banco → scheduler. Chamar no início e após cada alteração."""
    scheduler.definir_escalas({
        dia: [scheduler.Profissional(r["funcao"], r["entrada"], r["saida"], r["alm_ini"], r["alm_fim"])
              for r in linhas]
        for dia, linhas in get_escala_semana().items()
    })


_carregar_escalas()


def _hhmm(v) -> Optional[int]:
    """'07:30' → 450 minutos; vazio ou inválido → None."""
    try:
        hh, mm = (v or "").strip().split(":")[:2]
        return int(hh) * 60 + int(mm)
    except ValueError:
        return None


def _converter_parametro(nome: str, texto) -> Optional[float]:
    """Texto (do banco ou da tela) → valor no tipo do parâmetro; None se inválido."""
    _, _, tipo, minimo, maximo = scheduler.PARAMETROS[nome]
    texto = str(texto).strip().replace(",", ".")
    try:
        if tipo == "hora":
            valor = _hhmm(texto)
        elif tipo == "int":
            valor = int(float(texto)) if float(texto).is_integer() else None
        else:
            valor = float(texto)
    except ValueError:
        return None
    if valor is None or not (minimo <= valor <= maximo):
        return None
    return valor


def _carregar_parametros():
    """Parâmetros do banco → scheduler (os não gravados ficam no padrão)."""
    valores = {}
    for nome, texto in get_parametros().items():
        if nome in scheduler.PARAMETROS:
            v = _converter_parametro(nome, texto)
            if v is not None:
                valores[nome] = v
    scheduler.aplicar_parametros(valores)


_carregar_parametros()


def _get_status(eventos: dict, t_pre: int) -> str:
    if "punção" not in eventos:
        return "aguardando_puncao"
    if t_pre > 0 and "pré-QT" not in eventos:
        return "aguardando_preqt"
    if "QT" not in eventos:
        return "aguardando_qt"
    if "retirada" not in eventos:
        return "aguardando_retirada"
    if "higienização" not in eventos:
        return "aguardando_higienizacao"
    return "livre"


def _make_paciente(ag):
    if ag["protocolo"] in PROTOCOLO:
        return Paciente(
            ag["nome"], ag["protocolo"],
            ag.get("pre_override"), ag.get("qt_override_min"),
            ag.get("flexibilidade", "alta"), bool(ag.get("is_convenio")),
        )
    cor = ag.get("cor_qt_override") or "azul"
    bucket = ag.get("pre_override") or "B"
    return PacienteManual(
        ag["nome"], ag["protocolo"], cor, bucket,
        ag.get("flexibilidade", "alta"), bool(ag.get("is_convenio")),
    )


def _min(hhmm) -> Optional[int]:
    """'07:15' → 435; None se vazio ou inválido."""
    try:
        h_, m = str(hhmm).split(":")[:2]
        return int(h_) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _eventos_min(ag: dict) -> dict:
    """Eventos do atendimento em minutos, com chaves sem caixa: 'punção', 'pré-qt', 'qt'…"""
    return {k.lower(): _min(v) for k, v in (ag.get("eventos") or {}).items()}


def _sessao_alocada(ag: dict) -> Optional[Sessao]:
    """Sessão a partir da alocação gravada pela triagem (horário + poltrona).
    Os horários de pré-QT, QT e saída são só a previsão pelo tempo do protocolo."""
    if ag.get("horario") is None or ag.get("poltrona") is None:
        return None
    pac = _make_paciente(ag)
    inicio = ag["horario"]
    inicio_qt = inicio + pac.t_pre + scheduler.GAP_PRE_QT
    return Sessao(
        paciente=pac, chegada=inicio, poltrona=ag["poltrona"],
        inicio_pre=inicio, inicio_qt=inicio_qt, saida_est=inicio_qt + pac.t_qt + scheduler.GAP_SAIDA,
    )


def _build_dia(data_str: str, ao_vivo: bool = False):
    """Agendamentos do dia + sessões montadas pela alocação manual (só os que já
    têm horário e poltrona), ordenadas por horário. Sem regra, sem teto.
    ao_vivo fica por compatibilidade com as chamadas antigas."""
    ag_list = get_dia(data_str)
    sessoes = [s for s in (_sessao_alocada(ag) for ag in ag_list) if s]
    sessoes.sort(key=lambda s: (s.chegada, s.poltrona))
    return ag_list, sessoes


def _pendentes(ag_list: list) -> list:
    """Agendamentos ainda sem horário ou sem poltrona."""
    return [ag for ag in ag_list if ag.get("horario") is None or ag.get("poltrona") is None]


def _sobreposicoes(sessoes: list) -> dict:
    """nome → nomes com quem divide a poltrona em horário sobreposto (só aviso)."""
    avisos: dict = {}
    for i, a in enumerate(sessoes):
        for b in sessoes[i + 1:]:
            if a.poltrona == b.poltrona and a.chegada < b.saida_est and b.chegada < a.saida_est:
                avisos.setdefault(a.paciente.nome, []).append(b.paciente.nome)
                avisos.setdefault(b.paciente.nome, []).append(a.paciente.nome)
    return avisos


def _montar_poltronas(ag_list: list, sessoes: list) -> list:
    """Uma entrada por poltrona, com o ocupante atual.

    A mesma poltrona atende várias sessões no dia; o ocupante é a primeira sessão
    (por horário) ainda não concluída — quem está sentado, ou o próximo a chegar.
    Poltrona sem sessão pendente aparece livre."""
    ag_by_nome = {ag["nome"]: ag for ag in ag_list}
    por_poltrona: dict = {}
    for s in sessoes:                          # sessoes já vêm ordenadas por chegada
        ag = ag_by_nome.get(s.paciente.nome, {})
        concluida = _get_status(ag.get("eventos", {}), s.paciente.t_pre) == "livre"
        if not concluida:
            por_poltrona.setdefault(s.poltrona, (s, ag))

    poltronas = []
    for num in range(1, scheduler.N_POLTRONAS + 1):
        base = {"num": num, "segmento": scheduler.segmento(num)}
        if num in por_poltrona:
            sessao, ag = por_poltrona[num]
            evs = ag.get("eventos", {})
            poltronas.append({
                **base,
                "num_prontuario":    ag.get("num_prontuario") or "",
                "telefone":          ag.get("telefone") or "",
                "sessao":            sessao,
                "ag":                ag,
                "evs":               evs,
                "status":            _get_status(evs, sessao.paciente.t_pre),
                "evs_json":          json.dumps(evs),
                "inter_str":         " · ".join(ag.get("intercorrencias", [])),
                "intervalo_default": ag.get("intervalo_ciclo_dias") or INTERVALO_CICLO.get(ag.get("protocolo", ""), 21),
                "has_proxima":       ag.get("has_proxima", False),
                "duracao_mediana":   duracao_mediana_qt(ag["paciente_id"]),
            })
        else:
            poltronas.append({
                **base,
                "num_prontuario": "", "telefone": "", "sessao": None, "ag": {}, "evs": {},
                "status": "livre", "evs_json": "{}", "inter_str": "",
                "intervalo_default": 21, "has_proxima": False,
            })
    return poltronas


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if request.session.get("autenticado"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"erro": False})

@app.post("/login")
async def login_post(request: Request, senha: str = Form(...)):
    if senha == SENHA_TRIAGEM:
        request.session["autenticado"] = True
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"erro": True})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/painel", status_code=303)


# ---------------------------------------------------------------------------
# Agenda (Triagem)
# ---------------------------------------------------------------------------
def _faixa_convenio_txt() -> str:
    f = scheduler.faixa_convenio()
    return f"poltronas {f.start + 1}–{f.stop}" if f else "sem poltrona exclusiva"


def _opcoes_poltrona() -> list:
    return [(n, scheduler.segmento(n)) for n in range(1, scheduler.N_POLTRONAS + 1)]


def _data_valida(data: Optional[str]) -> str:
    try:
        return str(date.fromisoformat(data)) if data else str(date.today())
    except ValueError:
        return str(date.today())


@app.get("/", response_class=HTMLResponse)
async def agenda_get(request: Request):
    # Triagem é só do dia de hoje; outros dias se agendam pela Lista/Horizonte
    data = hoje = str(date.today())
    ag_list, sessoes = _build_dia(data)
    return templates.TemplateResponse(request, "agenda.html", {
        "pacientes":         ag_list,
        "sessoes":           sessoes,
        "pendentes":         sorted(_pendentes(ag_list), key=lambda a: (a.get("horario") is None, a.get("horario") or 0, a["nome"])),
        "sobreposicoes":     _sobreposicoes(sessoes),
        "opcoes_poltrona":   _opcoes_poltrona(),
        "grupos":            GRUPOS_DROPDOWN,
        "labels":            PROTOCOLO_LABEL,
        "cor_label":         COR_LABEL,
        "pre_label":         PRE_LABEL,
        "fmt":               _fmt,
        "data":              data,
        "hoje":              hoje,
        "protocolo_json":    json.dumps({k: v[1] for k, v in PROTOCOLO.items()}),
        "protocolo_bucket":  {k: v[1] for k, v in PROTOCOLO.items()},
        "qt_json":           json.dumps({k: QT_MIN[v[0]] for k, v in PROTOCOLO.items()}),
        "intervalo_json":    json.dumps(INTERVALO_CICLO),
        "faixa_convenio":    _faixa_convenio_txt(),
        "poltronas":         _montar_poltronas(ag_list, sessoes),
        "status_label":      STATUS_LABEL,
        "agora_txt":         datetime.now().strftime("%H:%M"),
    })


@app.post("/adicionar")
async def adicionar(
    request:              Request,
    nome:                 str           = Form(...),
    protocolo:            str           = Form(...),
    protocolo_custom:     Optional[str] = Form(None),
    cor_qt_override:      Optional[str] = Form(None),
    pre_override:         Optional[str] = Form(None),
    qt_override_min:      Optional[int] = Form(None),
    nome_mae:             Optional[str] = Form(None),
    data_nascimento:      Optional[str] = Form(None),
    data_sessao:          str           = Form(...),
    total_ciclos:         Optional[int] = Form(None),
    ciclos_previos:       Optional[int] = Form(None),
    intervalo_ciclo_dias: Optional[int] = Form(None),
    flexibilidade:        Optional[str] = Form("alta"),
    is_convenio:          Optional[str] = Form(None),
    ordem_medica:         Optional[str] = Form(None),
    num_prontuario:       Optional[str] = Form(None),
    telefone:             Optional[str] = Form(None),
    horario:              Optional[str] = Form(None),
    poltrona:             Optional[str] = Form(None),
):
    nome = nome.strip().title()

    if protocolo == "outro" and protocolo_custom and protocolo_custom.strip():
        protocolo = protocolo_custom.strip()
        is_valid = bool(cor_qt_override and cor_qt_override in QT_MIN)
    else:
        is_valid = protocolo in PROTOCOLO
        cor_qt_override = None

    override = pre_override if (pre_override and pre_override in PRE_LABEL) else None
    intervalo = intervalo_ciclo_dias or INTERVALO_CICLO.get(protocolo)

    if nome and is_valid:
        ag_id = criar_agendamento(
            nome=nome,
            nome_mae=nome_mae.strip().title() if nome_mae and nome_mae.strip() else None,
            data_nascimento=data_nascimento.strip() if data_nascimento and data_nascimento.strip() else None,
            protocolo=protocolo,
            pre_override=override,
            qt_override_min=qt_override_min,
            intervalo_ciclo_dias=intervalo,
            data_sessao=data_sessao,
            total_ciclos=total_ciclos,
            ciclos_previos=max(ciclos_previos or 0, 0),
            flexibilidade=flexibilidade or "alta",
            is_convenio=1 if is_convenio else 0,
            ordem_medica=1 if ordem_medica else 0,
            num_prontuario=num_prontuario.strip() if num_prontuario and num_prontuario.strip() else None,
            telefone=telefone.strip() if telefone and telefone.strip() else None,
            cor_qt_override=cor_qt_override,
            horario=_hhmm(horario),
            poltrona=_poltrona(poltrona),
        )
        registrar_log("walk_in:cadastro", _usuario(request), agendamento_id=ag_id, detalhes=nome)
    return RedirectResponse("/", status_code=303)


def _poltrona(v) -> Optional[int]:
    v = (v or "").strip()
    return int(v) if v.isdigit() and int(v) >= 1 else None


@app.post("/alocar/{ag_id}")
async def alocar_post(
    request: Request, ag_id: int,
    data_sessao: str = Form(...),
    horario: Optional[str] = Form(None),
    poltrona: Optional[str] = Form(None),
):
    h_min, pol = _hhmm(horario), _poltrona(poltrona)
    alocar(ag_id, h_min, pol)
    registrar_log("alocar", _usuario(request), agendamento_id=ag_id,
                  detalhes=f"{_fmt(h_min) if h_min is not None else '—'} · poltrona {pol or '—'}")
    return RedirectResponse("/", status_code=303)


@app.post("/remover/{ag_id}")
async def remover(request: Request, ag_id: int, data_sessao: str = Form(...)):
    cancelar_agendamento(ag_id)
    registrar_log("cancelar", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse("/", status_code=303)


@app.post("/limpar")
async def limpar(data_sessao: str = Form(...)):
    for ag in get_dia(data_sessao):
        cancelar_agendamento(ag["ag_id"])
    return RedirectResponse("/", status_code=303)


@app.post("/anotar/{ag_id}")
async def anotar(ag_id: int, texto: str = Form(...), next: str = Form("/painel")):
    texto = texto.strip()
    if texto:
        adicionar_intercorrencia(ag_id, texto)
    return RedirectResponse(next, status_code=303)


# ---------------------------------------------------------------------------
# Painel de Poltronas
# ---------------------------------------------------------------------------
@app.get("/painel", response_class=HTMLResponse)
async def painel_get(request: Request):
    hoje = str(date.today())
    ag_list, sessoes = _build_dia(hoje)
    poltronas = _montar_poltronas(ag_list, sessoes)

    return templates.TemplateResponse(request, "painel.html", {
        "poltronas":      poltronas,
        "n_sem_poltrona": len(_pendentes(ag_list)),
        "labels":         PROTOCOLO_LABEL,
        "status_label":   STATUS_LABEL,
        "data":           hoje,
        "hoje":           hoje,
        "fmt":            _fmt,
    })


@app.post("/registrar/{ag_id}/{evento}")
async def registrar(request: Request, ag_id: int, evento: str, next: str = Form("/painel")):
    # A poltrona já vem da alocação manual — registrar a etapa não muda o lugar
    registrar_evento(ag_id, evento, datetime.now().strftime("%H:%M"))
    registrar_log(f"evento:{evento}", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse(next, status_code=303)


@app.post("/desfazer/{ag_id}/{evento}")
async def desfazer(request: Request, ag_id: int, evento: str, next: str = Form("/registro")):
    desfazer_evento(ag_id, evento)   # não mexe na alocação (horário e poltrona ficam)
    registrar_log(f"desfazer:{evento}", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse(next, status_code=303)


@app.post("/proxima/{ag_id}")
async def proxima_sessao(
    request: Request,
    ag_id: int,
    paciente_id: int = Form(...),
    intervalo_dias: int = Form(...),
    data_proxima: str = Form(...),
    horario: Optional[str] = Form(None),
):
    resultado = agendar_proxima(paciente_id, data_proxima, intervalo_dias, _hhmm(horario))
    registrar_log(
        f"agendar_proxima:{resultado['status']}", _usuario(request),
        agendamento_id=ag_id, detalhes=resultado.get("data"),
    )
    return RedirectResponse("/painel", status_code=303)


# ---------------------------------------------------------------------------
# Confirmação de presença (D-1)
# ---------------------------------------------------------------------------
@app.get("/confirmacao")
async def confirmacao_get():
    # A confirmação de presença agora é feita na própria Agenda
    return RedirectResponse("/lista", status_code=303)


@app.post("/confirmar/{ag_id}")
async def confirmar(request: Request, ag_id: int, valor: Optional[str] = Form(None), dias: int = Form(7)):
    from database import get_db
    valor = valor if valor in ("sim", "nao") else None   # vazio = volta para pendente
    with get_db() as db:
        db.execute("UPDATE agendamentos SET confirmado=? WHERE id=?", (valor, ag_id))
    registrar_log(f"confirmar:{valor or 'pendente'}", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse(f"/lista?dias={dias}#ag-{ag_id}", status_code=303)


# ---------------------------------------------------------------------------
# Agendar quem está esperando (quadro no topo da Agenda)
# ---------------------------------------------------------------------------
@app.post("/agendar/{paciente_id}")
async def agendar_pelo_horizonte(
    request: Request,
    paciente_id: int,
    data_proxima: str = Form(...),
    intervalo_dias: int = Form(...),
    dias: int = Form(default=7),
    horario: Optional[str] = Form(None),
):
    resultado = agendar_proxima(paciente_id, data_proxima, intervalo_dias, _hhmm(horario))
    registrar_log(
        f"agendar_horizonte:{resultado['status']}", _usuario(request),
        detalhes=f"pac:{paciente_id} data:{resultado.get('data')}",
    )
    return RedirectResponse(f"/lista?dias={dias}", status_code=303)


# ---------------------------------------------------------------------------
# Horizonte de retornos (absorvido pela Agenda)
# ---------------------------------------------------------------------------
@app.get("/horizonte")
async def horizonte_get():
    # Quem espera agendamento agora aparece no topo da Agenda
    return RedirectResponse("/lista", status_code=303)


# ---------------------------------------------------------------------------
# Lista para o profissional do agendamento
# ---------------------------------------------------------------------------
def _ordem_horario(ag: dict):
    return (ag.get("horario") is None, ag.get("horario") or 0, ag["nome"])


def _dias_agendados(dias: int) -> list:
    """Próximos dias com seus agendamentos em ordem de horário (sem horário no fim)
    e a contagem de pacientes por hora — só informativa, nada é limitado."""
    from datetime import timedelta
    _DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    saida = []
    for d in range(dias):
        data = date.today() + timedelta(days=d)
        ags = sorted(get_dia(data.isoformat()), key=_ordem_horario)
        if not ags:
            continue
        por_hora: dict = {}
        for ag in ags:
            if ag.get("horario") is not None:
                hh = ag["horario"] // 60
                por_hora[hh] = por_hora.get(hh, 0) + 1
        saida.append({
            "data_iso":  data.isoformat(),
            "data_fmt":  f"{_DIAS[data.weekday()]}, {data.strftime('%d/%m/%Y')}",
            "agendamentos": ags,
            "por_hora":  sorted(por_hora.items()),
            "sem_horario": sum(1 for a in ags if a.get("horario") is None),
        })
    return saida


@app.get("/lista", response_class=HTMLResponse)
async def lista_get(request: Request, dias: int = Query(default=7)):
    return templates.TemplateResponse(request, "lista.html", {
        "dias_lista": _dias_agendados(dias),
        "aguardando": [p for p in get_horizonte(30) if p["situacao"] == "aguardando"],
        "labels":     PROTOCOLO_LABEL,
        "dias":       dias,
        "hoje":       str(date.today()),
        "fmt":        _fmt,
    })


@app.post("/lista/horario/{ag_id}")
async def lista_horario(request: Request, ag_id: int, horario: Optional[str] = Form(None), dias: int = Form(7)):
    h_min = _hhmm(horario)
    definir_horario(ag_id, h_min)
    registrar_log("agendar_horario", _usuario(request), agendamento_id=ag_id,
                  detalhes=_fmt(h_min) if h_min is not None else "—")
    return RedirectResponse(f"/lista?dias={dias}#ag-{ag_id}", status_code=303)


@app.get("/lista.csv")
async def lista_csv(request: Request, dias: int = Query(default=7)):
    import csv, io
    from datetime import date, timedelta
    hoje = date.today()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nome", "Prontuário", "Data", "Horário de chegada", "Telefone"])
    for d in range(dias):
        data = hoje + timedelta(days=d)
        for ag in sorted(get_dia(data.isoformat()), key=_ordem_horario):
            horario_chegada = _fmt(ag["horario"]) if ag.get("horario") is not None else ""
            writer.writerow([
                ag["nome"],
                ag.get("num_prontuario") or "",
                data.strftime("%d/%m/%Y"),
                horario_chegada,
                ag.get("telefone") or "",
            ])
    output.seek(0)
    filename = f"agendamentos-{hoje}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Registros
# ---------------------------------------------------------------------------
def _parametros_list():
    s = scheduler
    return [
        ("T_PUNCAO",                "Duração da punção",                    s.T_PUNCAO,                "min"),
        ("T_2A_OFFSET",             "Offset 2ª interação do técnico",        s.T_2A_OFFSET,             "min"),
        ("T_2A_DUR",                "Duração 2ª interação",                  s.T_2A_DUR,                "min"),
        ("T_MONTAGEM",              "Montagem da droga",                     s.T_MONTAGEM,              "min"),
        ("T_HIGIENIZACAO",          "Higienização da poltrona",              s.T_HIGIENIZACAO,          "min"),
        ("T_ENF_INICIO_QT",         "Enfermeiro inicia QT",                  s.T_ENF_INICIO_QT,         "min"),
        ("GAP_PRE_QT",              "Gap pré-QT → QT",                       s.GAP_PRE_QT,              "min"),
        ("GAP_SAIDA",               "Gap retirada → poltrona livre",         s.GAP_SAIDA,               "min"),
        ("OFFSET_CHEGADA_HOSPITAL", "Antecedência informada ao paciente",    s.OFFSET_CHEGADA_HOSPITAL, "min"),
        ("PUNCOES_POR_TECNICO_HORA","Vazão por técnico",                     s.PUNCOES_POR_TECNICO_HORA,"punções/h"),
        ("TAXA_NAO_CONFIRMACAO",    "Taxa de não-confirmação D-1",           round(TAXA_NAO_CONFIRMACAO * 100, 1), "%"),
        ("TAXA_REACAO_ADVERSA",     "Taxa de reação adversa",                round(TAXA_REACAO_ADVERSA  * 100, 1), "%"),
        ("RAZAO_WALK_IN",           "Fração walk-in sobre a capacidade",     round(s.RAZAO_WALK_IN      * 100, 1), "%"),
    ]


MIN_AMOSTRA_TEMPOS = 5   # abaixo disso o relatório avisa "poucos dados"


def _duracao(ev: dict, ini: str, fim: str) -> Optional[int]:
    """Minutos entre dois eventos; None se faltar um ou o intervalo não fizer sentido
    (esquecimento de registro gera zero, negativo ou horas)."""
    a, b = _min(ev.get(ini)), _min(ev.get(fim))
    if a is None or b is None:
        return None
    d = b - a
    return d if 0 < d <= 600 else None


def _mediana(valores: list) -> Optional[int]:
    if not valores:
        return None
    v = sorted(valores)
    meio = len(v) // 2
    return v[meio] if len(v) % 2 else round((v[meio - 1] + v[meio]) / 2)


def _planejado_x_real() -> list:
    """Por protocolo, em todo o histórico: pré-QT e QT planejados × a mediana do que
    foi registrado no painel (pré-QT → QT, QT → retirada). Só leitura: não altera
    nenhum parâmetro nem o scheduler."""
    por_prot: dict = {}
    for s in get_sessoes_concluidas():
        try:
            pac = _make_paciente(s)
        except ValueError:
            continue
        ev = s["eventos"]
        g = por_prot.setdefault(s["protocolo"], {"pre_p": [], "pre_r": [], "qt_p": [], "qt_r": []})
        pre = _duracao(ev, "pré-QT", "QT")
        qt  = _duracao(ev, "QT", "retirada")
        if pre is not None:
            g["pre_p"].append(pac.t_pre); g["pre_r"].append(pre)
        if qt is not None:
            g["qt_p"].append(pac.t_qt);   g["qt_r"].append(qt)

    linhas = []
    for prot, g in por_prot.items():
        n_pre, n_qt = len(g["pre_r"]), len(g["qt_r"])
        if not (n_pre or n_qt):
            continue
        linha = {"protocolo": prot, "label": PROTOCOLO_LABEL.get(prot, prot), "n_pre": n_pre, "n_qt": n_qt}
        for k in ("pre", "qt"):
            plan, real = _mediana(g[f"{k}_p"]), _mediana(g[f"{k}_r"])
            linha[f"{k}_plan"], linha[f"{k}_real"] = plan, real
            linha[f"{k}_dif"] = (real - plan) if (plan is not None and real is not None) else None
        linha["poucos"] = min(n for n in (n_pre, n_qt) if n) < MIN_AMOSTRA_TEMPOS
        linhas.append(linha)
    return sorted(linhas, key=lambda l: -max(l["n_pre"], l["n_qt"]))


def _vazio(v):
    return "" if v is None else v


def _dif(prev: Optional[int], real: Optional[int]) -> Optional[int]:
    return (real - prev) if (prev is not None and real is not None) else None


def _previsto_x_real_dia(data: str) -> list:
    """Uma linha por atendimento do dia: o previsto (horário alocado + tempos do
    protocolo do paciente) contra o que a equipe marcou no painel.
    Pré-QT real = pré-QT → QT; QT real = QT → retirada; total = punção → retirada."""
    linhas = []
    for ag in get_dia(data):
        pac = _make_paciente(ag)
        ev  = ag.get("eventos") or {}
        pre_p, qt_p = pac.t_pre, pac.t_qt
        tot_p = pac.t_pre + scheduler.GAP_PRE_QT + pac.t_qt   # mesma régua do real: punção → retirada
        pre_r = _duracao(ev, "pré-QT", "QT")
        qt_r  = _duracao(ev, "QT", "retirada")
        tot_r = _duracao(ev, "punção", "retirada")
        puncao = _min(ev.get("punção"))
        linhas.append({
            "nome":     ag["nome"],
            "protocolo": PROTOCOLO_LABEL.get(ag["protocolo"], ag["protocolo"]),
            "poltrona": ag.get("poltrona"),
            "inicio_prev": _fmt(ag["horario"]) if ag.get("horario") is not None else None,
            "puncao_real": ev.get("punção"),
            "atraso":   _dif(ag.get("horario"), puncao),
            "pre_p": pre_p, "pre_r": pre_r, "pre_d": _dif(pre_p, pre_r),
            "qt_p":  qt_p,  "qt_r":  qt_r,  "qt_d":  _dif(qt_p, qt_r),
            "tot_p": tot_p, "tot_r": tot_r, "tot_d": _dif(tot_p, tot_r),
        })
    return sorted(linhas, key=lambda l: (l["inicio_prev"] or "99", l["nome"]))


@app.get("/relatorio", response_class=HTMLResponse)
async def relatorio_get(request: Request, data: str = Query(default=None)):
    data = _data_valida(data)
    stats   = get_relatorio_dia(data)
    obs     = get_observacoes_dia(data)
    return templates.TemplateResponse(request, "relatorio.html", {
        "atendimentos":  _previsto_x_real_dia(data),
        "tempos":        _planejado_x_real(),
        "min_amostra":   MIN_AMOSTRA_TEMPOS,
        "parametros":    _parametros_list(),
        "stats":         stats,
        "obs":           obs,
        "data":          data,
        "hoje":          str(date.today()),
        "fmt":           _fmt,
    })


@app.post("/relatorio/observacoes")
async def salvar_obs(request: Request, data: str = Form(...)):
    form = await request.form()
    obs = {k[4:]: str(v).strip() for k, v in form.items() if k.startswith("obs_")}
    salvar_observacoes_dia(data, obs)
    return RedirectResponse(f"/relatorio?data={data}&saved=1", status_code=303)


@app.get("/relatorio/csv")
async def relatorio_csv(request: Request, data: str = Query(default=None)):
    import csv, io
    data = _data_valida(data)
    stats   = get_relatorio_dia(data)
    obs     = get_observacoes_dia(data)
    params  = _parametros_list()

    output = io.StringIO()
    w = csv.writer(output)

    w.writerow(["RELATÓRIO DE FIM DE DIA — CACON"])
    w.writerow(["Data", data])
    w.writerow([])
    w.writerow(["RESUMO DO DIA"])
    w.writerow(["Total no dia", stats["total"]])
    w.writerow(["Agendados",    stats["agendados"]])
    w.writerow(["Walk-ins",     stats["walk_ins"]])
    w.writerow(["Concluídos",   stats["concluidos"]])
    w.writerow(["Intercorrências", len(stats["intercorrencias"])])
    w.writerow([])
    w.writerow(["ATENDIMENTOS DO DIA — PREVISTO × REAL (min; diferença positiva = demorou mais)"])
    w.writerow(["Paciente", "Protocolo", "Poltrona", "Início previsto", "Punção real", "Atraso no início",
                "Pré-QT previsto", "Pré-QT real", "Pré-QT dif.",
                "QT previsto", "QT real", "QT dif.",
                "Total previsto", "Total real", "Total dif."])
    for a in _previsto_x_real_dia(data):
        w.writerow([a["nome"], a["protocolo"], a["poltrona"] or "", a["inicio_prev"] or "", a["puncao_real"] or "",
                    _vazio(a["atraso"]),
                    a["pre_p"], _vazio(a["pre_r"]), _vazio(a["pre_d"]),
                    a["qt_p"],  _vazio(a["qt_r"]),  _vazio(a["qt_d"]),
                    a["tot_p"], _vazio(a["tot_r"]), _vazio(a["tot_d"])])
    w.writerow([])
    w.writerow(["TEMPOS POR PROTOCOLO — PLANEJADO × REAL (todo o histórico, mediana em min)"])
    w.writerow(["Protocolo", "Pré-QT planejado", "Pré-QT real", "Pré-QT n", "QT planejado", "QT real", "QT n"])
    for t in _planejado_x_real():
        w.writerow([t["label"], t["pre_plan"], t["pre_real"], t["n_pre"], t["qt_plan"], t["qt_real"], t["n_qt"]])
    w.writerow([])
    w.writerow(["PARÂMETROS OPERACIONAIS"])
    w.writerow(["Variável", "Descrição", "Valor atual", "Unidade", "Observação do dia"])
    for nome_var, descricao, valor, unidade in params:
        w.writerow([nome_var, descricao, valor, unidade, obs.get(nome_var, "")])
    if stats["intercorrencias"]:
        w.writerow([])
        w.writerow(["INTERCORRÊNCIAS"])
        w.writerow(["Paciente", "Observação"])
        for ic in stats["intercorrencias"]:
            w.writerow([ic["nome"], ic["texto"]])

    output.seek(0)
    filename = f"relatorio-cacon-{data}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/auditoria", response_class=HTMLResponse)
async def auditoria_get(request: Request):
    logs = get_logs(limit=200)
    return templates.TemplateResponse(request, "auditoria.html", {"logs": logs})


@app.get("/registro", response_class=HTMLResponse)
async def registro_get(request: Request, data: str = Query(default=None)):
    if not data:
        data = str(date.today())
    ag_list, sessoes = _build_dia(data, ao_vivo=True)
    ag_by_nome = {ag["nome"]: ag for ag in ag_list}
    return templates.TemplateResponse(request, "registro.html", {
        "sessoes":    sessoes,
        "ag_by_nome": ag_by_nome,
        "labels":     PROTOCOLO_LABEL,
        "cor_label":  COR_LABEL,
        "fmt":        _fmt,
        "eventos":    EVENTOS,
        "data":       data,
    })


# ---------------------------------------------------------------------------
# Configuração — cadastro de pacientes (carga inicial a partir das fichas)
# ---------------------------------------------------------------------------
def _int_ou_none(v) -> Optional[int]:
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def _dados_paciente(form) -> tuple[dict, str, Optional[str]]:
    """Lê o formulário de cadastro → (dados, data_proxima, erro)."""
    g = lambda k: (form.get(k) or "").strip()
    dados = {
        "nome":            g("nome").title(),
        "nome_mae":        g("nome_mae").title() or None,
        "data_nascimento": g("data_nascimento") or None,
        "num_prontuario":  g("num_prontuario") or None,
        "telefone":        g("telefone") or None,
        "total_ciclos":    _int_ou_none(form.get("total_ciclos")),
        "ciclos_previos":  _int_ou_none(form.get("ciclos_previos")) or 0,
        "is_convenio":     1 if form.get("is_convenio") else 0,
        "flexibilidade":   "baixa" if g("flexibilidade") == "baixa" else "alta",
    }
    data_proxima = g("data_proxima")

    protocolo = g("protocolo")
    pre = g("pre_override")
    qt  = _int_ou_none(form.get("qt_override_min"))
    if protocolo == "outro":
        dados["protocolo"]       = g("protocolo_custom")
        dados["cor_qt_override"] = g("cor_qt_override") if g("cor_qt_override") in QT_MIN else None
        dados["pre_override"]    = pre if pre in PRE_LABEL else "B"
        dados["qt_override_min"] = qt
    else:
        dados["protocolo"]       = protocolo
        dados["cor_qt_override"] = None
        padrao = PROTOCOLO.get(protocolo)
        # Só guarda o que difere do padrão do protocolo — cadastro limpo
        dados["pre_override"]    = pre if (padrao and pre in PRE_LABEL and pre != padrao[1]) else None
        dados["qt_override_min"] = qt if (padrao and qt and qt != QT_MIN[padrao[0]]) else None
    dados["intervalo_ciclo_dias"] = (
        _int_ou_none(form.get("intervalo_ciclo_dias")) or INTERVALO_CICLO.get(dados["protocolo"]) or 21
    )

    erro = None
    if not dados["nome"]:
        erro = "Informe o nome do paciente."
    elif protocolo == "outro" and not dados["protocolo"]:
        erro = "Informe o nome do protocolo."
    elif protocolo == "outro" and not dados["cor_qt_override"]:
        erro = "Escolha a cor / duração do protocolo."
    elif protocolo != "outro" and protocolo not in PROTOCOLO:
        erro = "Escolha o protocolo."
    elif not data_proxima:
        erro = "Informe a data da próxima sessão."
    elif dados["total_ciclos"] and dados["ciclos_previos"] >= dados["total_ciclos"]:
        erro = "As sessões já feitas completam o total prescrito — o paciente não tem sessão a agendar."
    else:
        try:
            date.fromisoformat(data_proxima)
        except ValueError:
            erro = "Data da próxima sessão inválida."
    return dados, data_proxima, erro


def _render_pacientes(request: Request, *, form: Optional[dict] = None, editar: Optional[dict] = None,
                      erro: Optional[str] = None, ok: Optional[str] = None, status_code: int = 200):
    return templates.TemplateResponse(request, "config_pacientes.html", {
        "pacientes":       listar_pacientes(),
        "form":            form or {},
        "editar":          editar,
        "erro":            erro,
        "ok":              ok,
        "grupos":          GRUPOS_DROPDOWN,
        "labels":          PROTOCOLO_LABEL,
        "pre_label":       PRE_LABEL,
        "protocolo_json":  json.dumps({k: v[1] for k, v in PROTOCOLO.items()}),
        "qt_json":         json.dumps({k: QT_MIN[v[0]] for k, v in PROTOCOLO.items()}),
        "intervalo_json":  json.dumps(INTERVALO_CICLO),
        "protocolos":      PROTOCOLO,
        "hoje":            str(date.today()),
    }, status_code=status_code)


def _form_de_paciente(p: dict) -> dict:
    """Paciente do banco → valores do formulário de edição."""
    conhecido = p["protocolo"] in PROTOCOLO
    form = {k: ("" if v is None else v) for k, v in p.items()}
    form["protocolo"]        = p["protocolo"] if conhecido else "outro"
    form["protocolo_custom"] = "" if conhecido else p["protocolo"]
    form["data_proxima"]     = p.get("proxima_sessao") or ""
    form["horario_proxima"]  = _fmt(p["proxima_horario"]) if p.get("proxima_horario") is not None else ""
    if conhecido:
        cor, bucket = PROTOCOLO[p["protocolo"]]
        form["pre_override"]    = p["pre_override"] or bucket
        form["qt_override_min"] = p["qt_override_min"] or QT_MIN[cor]
    return form


@app.get("/configuracao")
async def configuracao_get():
    return RedirectResponse("/configuracao/pacientes", status_code=303)


@app.get("/configuracao/pacientes", response_class=HTMLResponse)
async def config_pacientes_get(request: Request, editar: Optional[int] = Query(default=None),
                               ok: Optional[str] = Query(default=None), erro: Optional[str] = Query(default=None)):
    p = get_paciente(editar) if editar else None
    return _render_pacientes(request, form=_form_de_paciente(p) if p else None, editar=p, ok=ok, erro=erro)


@app.post("/configuracao/pacientes")
async def config_pacientes_criar(request: Request):
    form = dict(await request.form())
    dados, data_proxima, erro = _dados_paciente(form)
    if not erro and paciente_por_nome(dados["nome"]):
        erro = f"Já existe um paciente chamado {dados['nome']}. Para corrigir, use Editar na lista abaixo."
    if erro:
        return _render_pacientes(request, form=form, erro=erro, status_code=422)
    pac_id = cadastrar_paciente(dados, data_proxima, _hhmm(form.get("horario_proxima")))
    registrar_log("cadastro:paciente", _usuario(request), detalhes=f"pac:{pac_id} {dados['nome']}")
    return RedirectResponse("/configuracao/pacientes?" + urlencode({"ok": dados["nome"]}), status_code=303)


@app.post("/configuracao/pacientes/{paciente_id}")
async def config_pacientes_atualizar(request: Request, paciente_id: int):
    p = get_paciente(paciente_id)
    if not p:
        return RedirectResponse("/configuracao/pacientes", status_code=303)
    form = dict(await request.form())
    dados, data_proxima, erro = _dados_paciente(form)
    outro = paciente_por_nome(dados["nome"]) if not erro else None
    if outro and outro != paciente_id:
        erro = f"Já existe outro paciente chamado {dados['nome']}."
    if erro:
        return _render_pacientes(request, form=form, editar=p, erro=erro, status_code=422)
    atualizar_paciente(paciente_id, dados, data_proxima, _hhmm(form.get("horario_proxima")))
    registrar_log("cadastro:edicao", _usuario(request), detalhes=f"pac:{paciente_id} {dados['nome']}")
    return RedirectResponse("/configuracao/pacientes?" + urlencode({"ok": dados["nome"]}), status_code=303)


@app.post("/configuracao/pacientes/{paciente_id}/remover")
async def config_pacientes_remover(request: Request, paciente_id: int):
    p = get_paciente(paciente_id)
    if p and remover_paciente(paciente_id):
        registrar_log("cadastro:remocao", _usuario(request), detalhes=f"pac:{paciente_id} {p['nome']}")
        return RedirectResponse("/configuracao/pacientes", status_code=303)
    erro = "Este paciente já tem sessão registrada no painel — o histórico não pode ser apagado." if p else None
    return RedirectResponse("/configuracao/pacientes?" + urlencode({"erro": erro or ""}), status_code=303)


# ---------------------------------------------------------------------------
# Configuração — escala da equipe (a capacidade do dia sai daqui)
# ---------------------------------------------------------------------------
def _render_escala(request: Request, dia: int, erro: Optional[str] = None, ok: Optional[str] = None,
                   status_code: int = 200):
    semana = get_escala_semana()
    escala_dia = scheduler._escala_do_dia(dia)
    por_hora = [
        {
            "hora":       _fmt(hh * 60),
            "tecnico":    scheduler.capacidade_puncao(hh * 60, escala_dia),
            "enfermeiro": scheduler.capacidade_qt(hh * 60, escala_dia),
            "limpeza":    scheduler._presentes(escala_dia, "limpeza", hh * 60),
        }
        for hh in range(scheduler.DIA_INI // 60, scheduler.DIA_FIM // 60)
    ]
    return templates.TemplateResponse(request, "config_escala.html", {
        "dia":        dia,
        "dias":       scheduler.DIAS_SEMANA,
        "tetos":      [capacidade_do_dia(dia_semana=d)["teto"] for d in range(7)],
        "linhas":     semana[dia],
        "funcoes":    scheduler.FUNCOES,
        "cap_dia":    capacidade_do_dia(dia_semana=dia),
        "por_hora":   por_hora,
        "fmt":        _fmt,
        "erro":       erro,
        "ok":         ok,
    }, status_code=status_code)


def _ler_profissional(form) -> tuple[Optional[tuple], Optional[str]]:
    funcao  = form.get("funcao")
    entrada = _hhmm(form.get("entrada"))
    saida   = _hhmm(form.get("saida"))
    alm_ini = _hhmm(form.get("alm_ini"))
    alm_fim = _hhmm(form.get("alm_fim"))
    if funcao not in scheduler.FUNCOES:
        return None, "Escolha a função."
    if entrada is None or saida is None:
        return None, "Informe o horário de entrada e de saída."
    if saida <= entrada:
        return None, "A saída precisa ser depois da entrada."
    if (alm_ini is None) != (alm_fim is None):
        return None, "Informe o início e o fim do intervalo (ou deixe os dois em branco)."
    if alm_ini is None:
        alm_ini = alm_fim = entrada          # sem intervalo
    elif not (entrada <= alm_ini < alm_fim <= saida):
        return None, "O intervalo precisa estar dentro do turno, com o fim depois do início."
    return (funcao, entrada, saida, alm_ini, alm_fim), None


def _dia_valido(dia) -> int:
    try:
        d = int(dia)
    except (TypeError, ValueError):
        return 0
    return d if 0 <= d <= 6 else 0


def _volta_escala(dia: int, ok: str):
    return RedirectResponse(f"/configuracao/escala?dia={dia}&" + urlencode({"ok": ok}), status_code=303)


@app.get("/configuracao/escala", response_class=HTMLResponse)
async def config_escala_get(request: Request, dia: Optional[str] = Query(default=None),
                            ok: Optional[str] = Query(default=None)):
    return _render_escala(request, _dia_valido(dia if dia is not None else date.today().weekday()), ok=ok)


@app.post("/configuracao/escala/{dia}/profissional")
async def config_escala_adicionar(request: Request, dia: int):
    dia = _dia_valido(dia)
    valores, erro = _ler_profissional(await request.form())
    if erro:
        return _render_escala(request, dia, erro=erro, status_code=422)
    salvar_profissional(None, dia, *valores)
    _carregar_escalas()
    registrar_log("escala:adicionar", _usuario(request), detalhes=f"dia:{dia} {valores}")
    return _volta_escala(dia, "Profissional adicionado.")


@app.post("/configuracao/escala/profissional/{prof_id}")
async def config_escala_editar(request: Request, prof_id: int):
    form = await request.form()
    dia = _dia_valido(form.get("dia"))
    valores, erro = _ler_profissional(form)
    if erro:
        return _render_escala(request, dia, erro=erro, status_code=422)
    salvar_profissional(prof_id, dia, *valores)
    _carregar_escalas()
    registrar_log("escala:editar", _usuario(request), detalhes=f"id:{prof_id} dia:{dia} {valores}")
    return _volta_escala(dia, "Alteração salva.")


@app.post("/configuracao/escala/profissional/{prof_id}/remover")
async def config_escala_remover(request: Request, prof_id: int, dia: str = Form("0")):
    dia = _dia_valido(dia)
    remover_profissional(prof_id)
    _carregar_escalas()
    registrar_log("escala:remover", _usuario(request), detalhes=f"id:{prof_id} dia:{dia}")
    return _volta_escala(dia, "Profissional removido.")


@app.post("/configuracao/escala/{dia}/copiar")
async def config_escala_copiar(request: Request, dia: int):
    dia = _dia_valido(dia)
    form = await request.form()
    destinos = sorted({_dia_valido(d) for d in form.getlist("destinos")} - {dia})
    if not destinos:
        return _render_escala(request, dia, erro="Marque pelo menos um dia para receber a cópia.", status_code=422)
    copiar_escala(dia, destinos)
    _carregar_escalas()
    registrar_log("escala:copiar", _usuario(request), detalhes=f"de:{dia} para:{destinos}")
    nomes = ", ".join(scheduler.DIAS_SEMANA[d] for d in destinos)
    return _volta_escala(dia, f"Escala copiada para: {nomes}.")


@app.post("/configuracao/escala/{dia}/restaurar")
async def config_escala_restaurar(request: Request, dia: int):
    dia = _dia_valido(dia)
    restaurar_escala_padrao(dia)
    _carregar_escalas()
    registrar_log("escala:restaurar", _usuario(request), detalhes=f"dia:{dia}")
    return _volta_escala(dia, "Escala padrão restaurada.")


# ---------------------------------------------------------------------------
# Configuração — parâmetros do algoritmo e poltronas
# ---------------------------------------------------------------------------
def _valor_exibido(nome: str, valor) -> str:
    tipo = scheduler.PARAMETROS[nome][2]
    if tipo == "pct":
        return f"{valor * 100:g}"
    if tipo == "hora":
        return _fmt(valor)
    return f"{valor:g}"


def _render_parametros(request: Request, erro: Optional[str] = None, ok: Optional[str] = None,
                       digitado: Optional[dict] = None, status_code: int = 200):
    atuais = scheduler.parametros_atuais()
    grupos: dict = {}
    for nome, (grupo, rotulo, tipo, minimo, maximo) in scheduler.PARAMETROS.items():
        grupos.setdefault(grupo, []).append({
            "nome":     nome,
            "rotulo":   rotulo,
            "tipo":     tipo,
            "valor":    (digitado or {}).get(nome, _valor_exibido(nome, atuais[nome])),
            "padrao":   _valor_exibido(nome, scheduler.PARAMETROS_PADRAO[nome]),
            "alterado": atuais[nome] != scheduler.PARAMETROS_PADRAO[nome],
        })
    return templates.TemplateResponse(request, "config_parametros.html", {
        "grupos":      grupos,
        "dias":        scheduler.DIAS_SEMANA,
        "caps":        [capacidade_do_dia(dia_semana=d) for d in range(7)],
        "n_poltronas": scheduler.N_POLTRONAS,
        "faixa_conv":  _faixa_convenio_txt(),
        "erro":        erro,
        "ok":          ok,
    }, status_code=status_code)


@app.get("/configuracao/parametros", response_class=HTMLResponse)
async def config_parametros_get(request: Request, ok: Optional[str] = Query(default=None)):
    return _render_parametros(request, ok=ok)


@app.post("/configuracao/parametros")
async def config_parametros_salvar(request: Request):
    form = await request.form()
    digitado = {nome: str(form.get(nome, "")).strip() for nome in scheduler.PARAMETROS}
    valores, invalidos = {}, []
    for nome, texto in digitado.items():
        if scheduler.PARAMETROS[nome][2] == "pct":   # tela em %, guardado como fração
            try:
                texto = str(float(texto.replace(",", ".")) / 100)
            except ValueError:
                texto = ""
        v = _converter_parametro(nome, texto)
        if v is None:
            invalidos.append(scheduler.PARAMETROS[nome][1])
        else:
            valores[nome] = v
    total = sum(valores.get(k, 0) for k in ("N_POLTRONAS_SUS", "N_POLTRONAS_CONVENIO", "N_POLTRONAS_HEMATO"))
    if invalidos:
        erro = "Valor inválido ou fora do limite em: " + "; ".join(invalidos) + "."
    elif total < 1:
        erro = "O setor precisa ter pelo menos uma poltrona."
    else:
        erro = None
    if erro:
        return _render_parametros(request, erro=erro, digitado=digitado, status_code=422)
    # Grava só o que difere do padrão: o resto continua acompanhando o padrão do código
    salvar_parametros({
        nome: (None if v == scheduler.PARAMETROS_PADRAO[nome]
               else _fmt(v) if scheduler.PARAMETROS[nome][2] == "hora" else v)
        for nome, v in valores.items()
    })
    _carregar_parametros()
    alterados = {k: v for k, v in valores.items() if v != scheduler.PARAMETROS_PADRAO[k]}
    registrar_log("parametros:salvar", _usuario(request), detalhes=json.dumps(alterados))
    return RedirectResponse("/configuracao/parametros?" + urlencode({"ok": "Parâmetros salvos."}), status_code=303)


@app.post("/configuracao/parametros/restaurar")
async def config_parametros_restaurar(request: Request):
    salvar_parametros({nome: None for nome in scheduler.PARAMETROS})
    _carregar_parametros()
    registrar_log("parametros:restaurar", _usuario(request))
    return RedirectResponse("/configuracao/parametros?" + urlencode({"ok": "Parâmetros padrão restaurados."}),
                            status_code=303)
