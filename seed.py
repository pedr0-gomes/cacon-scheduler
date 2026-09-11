"""
Seed de demonstração — popula o banco com pacientes e sessões realistas.
Roda uma única vez; seguro re-rodar (ignora duplicatas por nome+data).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from database import criar_agendamento, registrar_evento, get_db

TODAY     = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW  = TODAY + timedelta(days=1)
D7        = TODAY + timedelta(days=7)
D14       = TODAY + timedelta(days=14)


def ag(nome, protocolo, data_sessao, *, status="agendado", municipio,
       nome_mae=None, nasc=None, total_ciclos=6,
       intervalo=None, is_convenio=False, flexibilidade="baixa", ordem_medica=False):
    from scheduler import INTERVALO_CICLO
    iv = intervalo or INTERVALO_CICLO.get(protocolo, 21)
    ag_id = criar_agendamento(
        nome=nome, nome_mae=nome_mae, data_nascimento=nasc,
        protocolo=protocolo, pre_override=None, qt_override_min=None,
        intervalo_ciclo_dias=iv, data_sessao=str(data_sessao),
        is_convenio=is_convenio, flexibilidade=flexibilidade,
        municipio=municipio, ordem_medica=int(ordem_medica),
        total_ciclos=total_ciclos,
    )
    if status == "agendado":
        with get_db() as db:
            db.execute("UPDATE agendamentos SET status='agendado' WHERE id=?", (ag_id,))
    return ag_id


def ev(ag_id, *tipos):
    horas = {"punção": "07:15", "pré-qt": "07:45", "qt": "08:10",
             "retirada": "10:30", "higienização": "10:50"}
    for t in tipos:
        registrar_evento(ag_id, t, horas.get(t, "09:00"))


# ── Sessões de ontem (históricas, concluídas) ───────────────────────────────
id1 = ag("Maria das Graças Silva", "gencitabina_mono",  YESTERDAY, municipio="Cidade A",    nome_mae="Francisca Silva",   nasc="12/04/1958", total_ciclos=8)
id2 = ag("Antônia Lima Rodrigues",  "trastuzumabe_manut", YESTERDAY, municipio="Cidade B", nome_mae="Raimunda Lima", nasc="03/09/1965", total_ciclos=6)
id3 = ag("Francisco Alves Neto",    "folfox_d1",          YESTERDAY, municipio="Cidade C",         nome_mae="Ana Alves",         nasc="22/11/1952", total_ciclos=12)

for i in [id1, id2, id3]:
    ev(i, "punção", "pré-qt", "qt", "retirada", "higienização")

# ── Sessões de hoje ─────────────────────────────────────────────────────────

# Já em andamento — qt em curso
id_a = ag("José Ferreira de Sousa",    "carbo_paclit_q3w",   TODAY, municipio="Cidade A",        nome_mae="Maria Ferreira",    nasc="15/06/1961", total_ciclos=6,  flexibilidade="baixa")
id_b = ag("Raimunda Alves Carvalho",   "r_chop",             TODAY, municipio="Cidade D",     nome_mae="Benedita Alves",    nasc="08/02/1970", total_ciclos=8,  flexibilidade="baixa")
id_c = ag("Luiz Carlos Ferreira",      "gencit_cis",         TODAY, municipio="Cidade E",        nome_mae="Conceição Ferreira",nasc="30/10/1955", total_ciclos=6,  flexibilidade="baixa")
ev(id_a, "punção", "pré-qt", "qt")
ev(id_b, "punção", "pré-qt", "qt")
ev(id_c, "punção", "pré-qt")

# Aguardando punção
id_d = ag("Ana Beatriz Costa",         "paclitaxel_semanal", TODAY, municipio="Cidade B",nome_mae="Socorro Costa",     nasc="17/03/1975", total_ciclos=12, flexibilidade="baixa")
id_e = ag("Marta Regina Borges",       "tc",                 TODAY, municipio="Cidade A",         nome_mae="Irene Borges",      nasc="29/07/1968", total_ciclos=8,  flexibilidade="baixa")
id_f = ag("Sebastião Alves Torres",    "imunoterapia",       TODAY, municipio="Cidade F",      nome_mae="Maria Torres",      nasc="04/12/1949", total_ciclos=6,  flexibilidade="alta")
id_g = ag("Rita de Cássia Mendes",     "fac",                TODAY, municipio="Cidade G",          nome_mae="Joana Mendes",      nasc="21/05/1978", total_ciclos=6,  flexibilidade="baixa")
id_h = ag("Lúcia de Fátima Souza",     "docetaxel_mono",     TODAY, municipio="Cidade C",            nome_mae="Helena Souza",      nasc="11/08/1963", total_ciclos=6,  flexibilidade="baixa")
id_i = ag("Carlos Eduardo Lima",       "bevacizumabe",       TODAY, municipio="Cidade B",nome_mae="Ana Lima",          nasc="05/01/1957", total_ciclos=10, flexibilidade="alta")
id_j = ag("Benedita dos Santos",       "vinorelbina",        TODAY, municipio="Cidade A",         nome_mae="Tereza Santos",     nasc="18/09/1972", total_ciclos=8,  flexibilidade="baixa")
id_k = ag("Manoel Rodrigues Filho",    "xelox_d1",           TODAY, municipio="Cidade E",        nome_mae="Filomena Rodrigues",nasc="27/02/1950", total_ciclos=8,  flexibilidade="alta")

# Walk-in de hoje (ordem médica)
id_l = ag("Pedro Henrique Maia",       "cisplatina_semanal", TODAY, municipio="Cidade B",nome_mae="Sandra Maia",      nasc="13/11/1983", total_ciclos=6,  flexibilidade="alta",  status="walk_in", ordem_medica=True)

# Convênio
id_m = ag("Francisca Sousa Oliveira",  "trastuzumabe_1dose", TODAY, municipio="Cidade A",        nome_mae="Conceição Sousa",   nasc="02/06/1967", total_ciclos=6,  flexibilidade="baixa", is_convenio=True)
id_n = ag("Antônio Neto Gomes",        "duplo_bloqueio",     TODAY, municipio="Cidade B",nome_mae="Maria Gomes",      nasc="09/04/1960", total_ciclos=6,  flexibilidade="baixa", is_convenio=True)

# ── Sessões de amanhã (visíveis na confirmação) ─────────────────────────────
ag("Maria das Graças Silva",  "gencitabina_mono",    TOMORROW, municipio="Cidade A",         total_ciclos=8)
ag("Ana Beatriz Costa",       "paclitaxel_semanal",  TOMORROW, municipio="Cidade B",total_ciclos=12)
ag("Benedita dos Santos",     "vinorelbina",         TOMORROW, municipio="Cidade A",         total_ciclos=8)
ag("Marta Regina Borges",     "tc",                  TOMORROW, municipio="Cidade A",         total_ciclos=8)
ag("Sebastião Alves Torres",  "imunoterapia",        TOMORROW, municipio="Cidade F",      total_ciclos=6, flexibilidade="alta")
ag("Raimunda Alves Carvalho", "r_chop",              TOMORROW, municipio="Cidade D",     total_ciclos=8)
ag("Luiz Carlos Ferreira",    "gencit_cis",          TOMORROW, municipio="Cidade E",        total_ciclos=6)
ag("Carlos Eduardo Lima",     "bevacizumabe",        TOMORROW, municipio="Cidade B",total_ciclos=10, flexibilidade="alta")
ag("Francisca Sousa Oliveira","trastuzumabe_1dose",  TOMORROW, municipio="Cidade A",         total_ciclos=6, is_convenio=True)

# ── Horizonte — próximos 14 dias ────────────────────────────────────────────
ag("José Ferreira de Sousa",  "carbo_paclit_q3w", D7,  municipio="Cidade A",         total_ciclos=6)
ag("Rita de Cássia Mendes",   "fac",              D7,  municipio="Cidade G",           total_ciclos=6)
ag("Lúcia de Fátima Souza",   "docetaxel_mono",   D7,  municipio="Cidade C",             total_ciclos=6)
ag("Francisco Alves Neto",    "folfox_d1",        D14, municipio="Cidade C",             total_ciclos=12)
ag("Antônio Neto Gomes",      "duplo_bloqueio",   D14, municipio="Cidade B", total_ciclos=6, is_convenio=True)
ag("Manoel Rodrigues Filho",  "xelox_d1",         D14, municipio="Cidade E",         total_ciclos=8)

print("Seed concluído.")
