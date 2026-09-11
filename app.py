from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, date
from typing import Optional
import json

from config import SENHA_TRIAGEM, SESSION_SECRET

from scheduler import (
    gerar_escala, Paciente, PacienteManual,
    PROTOCOLO, QT_MIN, PRE_MIN, COR_PRIORIDADE, INTERVALO_CICLO,
    curva_do_dia, capacidade_por_janela, capacidade_do_dia, staff_agora,
    CARGA_POR_PAPEL, STAFF_REFERENCIA,
    staff_em, _fmt,
    DIA_INI, OFFSET_CHEGADA_HOSPITAL,
    T_PUNCAO, T_2A_OFFSET, T_2A_DUR, T_MONTAGEM, T_HIGIENIZACAO,
    T_ENF_INICIO_QT, GAP_PRE_QT, GAP_SAIDA,
    PUNCOES_POR_TECNICO_HORA, TAXA_NAO_CONFIRMACAO, TAXA_REACAO_ADVERSA, RAZAO_WALK_IN,
)
from database import (
    init_db, get_dia, criar_agendamento,
    cancelar_agendamento, registrar_evento, desfazer_evento,
    adicionar_intercorrencia, agendar_proxima, get_horizonte,
    duracao_mediana_qt, registrar_log, get_logs,
    get_relatorio_dia, salvar_observacoes_dia, get_observacoes_dia,
)

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

SEGMENTO = {num: ("SUS" if num <= 25 else "Conv" if num <= 30 else "Hemato") for num in range(1, 35)}
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

app = FastAPI()
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
init_db()


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


def _build_dia(data_str: str):
    ag_list = get_dia(data_str)
    if not ag_list:
        return ag_list, []
    pacs = [_make_paciente(ag) for ag in ag_list]
    dia_semana = date.fromisoformat(data_str).weekday()
    return ag_list, gerar_escala(pacs, dia_semana=dia_semana)


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
@app.get("/", response_class=HTMLResponse)
async def agenda_get(request: Request):
    data = str(date.today())
    hoje = data
    ag_list, sessoes = _build_dia(data)
    bandas  = capacidade_por_janela(curva_do_dia(date.today().weekday()))
    cap_dia = capacidade_do_dia(dia_semana=date.today().weekday())
    return templates.TemplateResponse(request, "agenda.html", {
        "pacientes":         ag_list,
        "sessoes":           sessoes,
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
        "bandas":            bandas,
        "cap_dia":           cap_dia,
        "staff_curve_json":  json.dumps(bandas),
        "sessoes_json":      json.dumps([{"chegada": s.chegada} for s in sessoes]),
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
    intervalo_ciclo_dias: Optional[int] = Form(None),
    flexibilidade:        Optional[str] = Form("alta"),
    is_convenio:          Optional[str] = Form(None),
    ordem_medica:         Optional[str] = Form(None),
    num_prontuario:       Optional[str] = Form(None),
    telefone:             Optional[str] = Form(None),
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
            flexibilidade=flexibilidade or "alta",
            is_convenio=1 if is_convenio else 0,
            ordem_medica=1 if ordem_medica else 0,
            num_prontuario=num_prontuario.strip() if num_prontuario and num_prontuario.strip() else None,
            telefone=telefone.strip() if telefone and telefone.strip() else None,
            cor_qt_override=cor_qt_override,
        )
        registrar_log("walk_in:cadastro", _usuario(request), agendamento_id=ag_id, detalhes=nome)
    return RedirectResponse(f"/?data={data_sessao}", status_code=303)


@app.post("/remover/{ag_id}")
async def remover(request: Request, ag_id: int, data_sessao: str = Form(...)):
    cancelar_agendamento(ag_id)
    registrar_log("cancelar", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse(f"/?data={data_sessao}", status_code=303)


@app.post("/limpar")
async def limpar(data_sessao: str = Form(...)):
    for ag in get_dia(data_sessao):
        cancelar_agendamento(ag["ag_id"])
    return RedirectResponse(f"/?data={data_sessao}", status_code=303)


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

    ag_by_nome = {ag["nome"]: ag for ag in ag_list}
    pol_sessao = {s.poltrona: s for s in sessoes}

    poltronas = []
    for num in range(1, 35):
        sessao = pol_sessao.get(num)
        if sessao:
            ag = ag_by_nome.get(sessao.paciente.nome, {})
            evs = ag.get("eventos", {})
            status = _get_status(evs, sessao.paciente.t_pre)
            intervalo_default = ag.get("intervalo_ciclo_dias") or INTERVALO_CICLO.get(ag.get("protocolo", ""), 21)
            poltronas.append({
                "num_prontuario":    ag.get("num_prontuario") or "",
                "telefone":          ag.get("telefone") or "",
                "num":               num,
                "sessao":            sessao,
                "ag":                ag,
                "evs":               evs,
                "status":            status,
                "segmento":          SEGMENTO[num],
                "evs_json":          json.dumps(evs),
                "inter_str":         " · ".join(ag.get("intercorrencias", [])),
                "intervalo_default": intervalo_default,
                "has_proxima":       ag.get("has_proxima", False),
                "duracao_mediana":   duracao_mediana_qt(ag["paciente_id"]),
            })
        else:
            poltronas.append({
                "num_prontuario":    "",
                "telefone":          "",
                "num":               num,
                "sessao":            None,
                "ag":                {},
                "evs":               {},
                "status":            "livre",
                "segmento":          SEGMENTO[num],
                "evs_json":          "{}",
                "inter_str":         "",
                "intervalo_default": 21,
                "has_proxima":       False,
            })

    # Carga por papel (técnico / enfermeiro / limpeza)
    cargas = {"tecnico": 0.0, "enfermeiro": 0.0, "limpeza": 0.0}
    for p in poltronas:
        pesos = CARGA_POR_PAPEL.get(p["status"], CARGA_POR_PAPEL["livre"])
        for papel in cargas:
            cargas[papel] += pesos[papel]

    now_min   = datetime.now().hour * 60 + datetime.now().minute
    staff_now = staff_agora(now_min, dia_semana=date.today().weekday())
    carga_ctx = {
        papel: {
            "total": round(cargas[papel], 1),
            "max":   max(staff_now[papel], 1),
            "pct":   min(100, round(cargas[papel] / max(staff_now[papel], 1) * 100)),
        }
        for papel in cargas
    }

    return templates.TemplateResponse(request, "painel.html", {
        "poltronas":      poltronas,
        "labels":         PROTOCOLO_LABEL,
        "status_label":   STATUS_LABEL,
        "data":           hoje,
        "hoje":           hoje,
        "fmt":            _fmt,
        "carga_ctx":      carga_ctx,
        "carga_por_papel": CARGA_POR_PAPEL,
    })


@app.post("/registrar/{ag_id}/{evento}")
async def registrar(request: Request, ag_id: int, evento: str, next: str = Form("/painel")):
    registrar_evento(ag_id, evento, datetime.now().strftime("%H:%M"))
    registrar_log(f"evento:{evento}", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse(next, status_code=303)


@app.post("/desfazer/{ag_id}/{evento}")
async def desfazer(request: Request, ag_id: int, evento: str, next: str = Form("/registro")):
    desfazer_evento(ag_id, evento)
    registrar_log(f"desfazer:{evento}", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse(next, status_code=303)


@app.post("/proxima/{ag_id}")
async def proxima_sessao(
    request: Request,
    ag_id: int,
    paciente_id: int = Form(...),
    intervalo_dias: int = Form(...),
    data_proxima: str = Form(...),
):
    resultado = agendar_proxima(paciente_id, data_proxima, intervalo_dias)
    registrar_log(
        f"agendar_proxima:{resultado['status']}", _usuario(request),
        agendamento_id=ag_id, detalhes=resultado.get("data"),
    )
    return RedirectResponse("/painel", status_code=303)


# ---------------------------------------------------------------------------
# Confirmação de presença (D-1)
# ---------------------------------------------------------------------------
@app.get("/confirmacao", response_class=HTMLResponse)
async def confirmacao_get(request: Request):
    from datetime import timedelta
    data = str(date.today() + timedelta(days=1))
    ag_list, sessoes = _build_dia(data)
    sessao_por_nome = {s.paciente.nome: s for s in sessoes}
    return templates.TemplateResponse(request, "confirmacao.html", {
        "pacientes":   ag_list,
        "sessoes_map": sessao_por_nome,
        "data":        data,
        "hoje":        str(date.today()),
        "fmt":         _fmt,
        "labels":      PROTOCOLO_LABEL,
    })


@app.post("/confirmar/{ag_id}")
async def confirmar(request: Request, ag_id: int, valor: str = Form(...), data_sessao: str = Form(...)):
    from database import get_db
    with get_db() as db:
        db.execute("UPDATE agendamentos SET confirmado=? WHERE id=?", (valor, ag_id))
    registrar_log(f"confirmar:{valor}", _usuario(request), agendamento_id=ag_id)
    return RedirectResponse(f"/confirmacao?data={data_sessao}", status_code=303)


# ---------------------------------------------------------------------------
# Agendamento direto pelo horizonte (triagem)
# ---------------------------------------------------------------------------
@app.post("/agendar/{paciente_id}")
async def agendar_pelo_horizonte(
    request: Request,
    paciente_id: int,
    data_proxima: str = Form(...),
    intervalo_dias: int = Form(...),
    qt_override_min: Optional[int] = Form(None),
    dias: int = Form(default=30),
):
    if qt_override_min:
        from database import get_db
        with get_db() as db:
            db.execute(
                "UPDATE pacientes SET qt_override_min=? WHERE id=?",
                (qt_override_min, paciente_id)
            )
    resultado = agendar_proxima(paciente_id, data_proxima, intervalo_dias)
    registrar_log(
        f"agendar_horizonte:{resultado['status']}", _usuario(request),
        detalhes=f"pac:{paciente_id} data:{resultado.get('data')}",
    )
    return RedirectResponse(f"/horizonte?dias={dias}", status_code=303)


# ---------------------------------------------------------------------------
# Horizonte de retornos
# ---------------------------------------------------------------------------
@app.get("/horizonte", response_class=HTMLResponse)
async def horizonte_get(request: Request, dias: int = Query(default=30)):
    pacientes = get_horizonte(dias)
    return templates.TemplateResponse(request, "horizonte.html", {
        "pacientes": pacientes,
        "dias":      dias,
        "labels":    PROTOCOLO_LABEL,
    })


# ---------------------------------------------------------------------------
# Lista para o profissional do agendamento
# ---------------------------------------------------------------------------
@app.get("/lista", response_class=HTMLResponse)
async def lista_get(request: Request, dias: int = Query(default=7)):
    from datetime import date, timedelta
    hoje = date.today()
    registros = []
    for d in range(dias):
        data = hoje + timedelta(days=d)
        data_str = data.isoformat()
        ag_list, sessoes = _build_dia(data_str)
        sessao_por_nome = {s.paciente.nome: s for s in sessoes}
        for ag in ag_list:
            sessao = sessao_por_nome.get(ag["nome"])
            if sessao:
                chegada_h = max(DIA_INI, sessao.chegada - OFFSET_CHEGADA_HOSPITAL)
                horario_chegada = _fmt(chegada_h)
            else:
                horario_chegada = "—"
            registros.append({
                "nome":            ag["nome"],
                "num_prontuario":  ag.get("num_prontuario") or "",
                "telefone":        ag.get("telefone") or "",
                "data_iso":        data_str,
                "data_fmt":        data.strftime("%d/%m/%Y"),
                "horario_chegada": horario_chegada,
            })
    return templates.TemplateResponse(request, "lista.html", {
        "registros":  registros,
        "dias":       dias,
        "offset_h":   OFFSET_CHEGADA_HOSPITAL // 60,
        "hoje":       str(hoje),
    })


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
        data_str = data.isoformat()
        ag_list, sessoes = _build_dia(data_str)
        sessao_por_nome = {s.paciente.nome: s for s in sessoes}
        for ag in ag_list:
            sessao = sessao_por_nome.get(ag["nome"])
            if sessao:
                chegada_h = max(DIA_INI, sessao.chegada - OFFSET_CHEGADA_HOSPITAL)
                horario_chegada = _fmt(chegada_h)
            else:
                horario_chegada = ""
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
    return [
        ("T_PUNCAO",                "Duração da punção",                    T_PUNCAO,                "min"),
        ("T_2A_OFFSET",             "Offset 2ª interação do técnico",        T_2A_OFFSET,             "min"),
        ("T_2A_DUR",                "Duração 2ª interação",                  T_2A_DUR,                "min"),
        ("T_MONTAGEM",              "Montagem da droga",                     T_MONTAGEM,              "min"),
        ("T_HIGIENIZACAO",          "Higienização da poltrona",              T_HIGIENIZACAO,          "min"),
        ("T_ENF_INICIO_QT",         "Enfermeiro inicia QT",                  T_ENF_INICIO_QT,         "min"),
        ("GAP_PRE_QT",              "Gap pré-QT → QT",                       GAP_PRE_QT,              "min"),
        ("GAP_SAIDA",               "Gap retirada → poltrona livre",         GAP_SAIDA,               "min"),
        ("OFFSET_CHEGADA_HOSPITAL", "Antecedência informada ao paciente",    OFFSET_CHEGADA_HOSPITAL, "min"),
        ("PUNCOES_POR_TECNICO_HORA","Vazão por técnico",                     PUNCOES_POR_TECNICO_HORA,"punções/h"),
        ("TAXA_NAO_CONFIRMACAO",    "Taxa de não-confirmação D-1",           round(TAXA_NAO_CONFIRMACAO * 100, 1), "%"),
        ("TAXA_REACAO_ADVERSA",     "Taxa de reação adversa",                round(TAXA_REACAO_ADVERSA  * 100, 1), "%"),
        ("RAZAO_WALK_IN",           "Fração walk-in sobre a capacidade",     round(RAZAO_WALK_IN        * 100, 1), "%"),
    ]


@app.get("/relatorio", response_class=HTMLResponse)
async def relatorio_get(request: Request, data: str = Query(default=None)):
    if not data:
        data = str(date.today())
    cap_dia = capacidade_do_dia(dia_semana=date.fromisoformat(data).weekday())
    stats   = get_relatorio_dia(data)
    obs     = get_observacoes_dia(data)
    return templates.TemplateResponse(request, "relatorio.html", {
        "parametros":    _parametros_list(),
        "cap_dia":       cap_dia,
        "stats":         stats,
        "obs":           obs,
        "data":          data,
        "hoje":          str(date.today()),
        "RAZAO_WALK_IN": RAZAO_WALK_IN,
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
    if not data:
        data = str(date.today())
    stats   = get_relatorio_dia(data)
    obs     = get_observacoes_dia(data)
    cap_dia = capacidade_do_dia(dia_semana=date.fromisoformat(data).weekday())
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
    w.writerow(["CAPACIDADE CALCULADA"])
    w.writerow(["Técnico-horas de punção", cap_dia["tecnico_horas"]])
    w.writerow(["Teto do dia",             cap_dia["teto"]])
    w.writerow(["Pool agendado",           cap_dia["n_agendado"]])
    w.writerow(["Pool walk-in",            cap_dia["n_walk_in"]])
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
    ag_list, sessoes = _build_dia(data)
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
