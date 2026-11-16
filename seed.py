"""
Seed de demonstração — popula o banco com pacientes e sessões realistas.
Roda uma única vez; seguro re-rodar (ignora duplicatas por nome+data).

    uv run python seed.py

Monta: ontem concluído, hoje com gente em atendimento, aguardando punção e
aguardando poltrona, e a Agenda dos próximos dias (com um paciente sem horário).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from database import init_db, criar_agendamento, registrar_evento, get_db

init_db()

TODAY     = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW  = TODAY + timedelta(days=1)
D7        = TODAY + timedelta(days=7)
D14       = TODAY + timedelta(days=14)


def _min(hhmm):
    if not hhmm:
        return None
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def ag(nome, protocolo, data_sessao, *, status="agendado", municipio,
       nome_mae=None, nasc=None, total_ciclos=6,
       intervalo=None, is_convenio=False, ordem_medica=False,
       horario=None, poltrona=None):
    """horario 'HH:MM' = marcado na Agenda; poltrona = escolhida em Hoje."""
    from scheduler import INTERVALO_CICLO
    iv = intervalo or INTERVALO_CICLO.get(protocolo, 21)
    ag_id = criar_agendamento(
        nome=nome, nome_mae=nome_mae, data_nascimento=nasc,
        protocolo=protocolo, pre_override=None, qt_override_min=None,
        intervalo_ciclo_dias=iv, data_sessao=str(data_sessao),
        is_convenio=is_convenio, municipio=municipio, ordem_medica=int(ordem_medica),
        total_ciclos=total_ciclos, horario=_min(horario), poltrona=poltrona,
    )
    if status == "agendado":
        with get_db() as db:
            db.execute("UPDATE agendamentos SET status='agendado' WHERE id=?", (ag_id,))
    return ag_id


def ev(ag_id, *passos):
    """passos = pares (etapa, 'HH:MM')."""
    for tipo, hora in passos:
        registrar_evento(ag_id, tipo, hora)


# ── Ontem (concluídos — alimentam o Relatório) ──────────────────────────────
id1 = ag("Maria das Graças Silva", "gencitabina_mono",   YESTERDAY, municipio="Cidade A", nome_mae="Francisca Silva", nasc="12/04/1958", total_ciclos=8,  horario="07:00", poltrona=1)
id2 = ag("Antônia Lima Rodrigues", "trastuzumabe_manut", YESTERDAY, municipio="Cidade B", nome_mae="Raimunda Lima",   nasc="03/09/1965", total_ciclos=6,  horario="07:00", poltrona=2)
id3 = ag("Francisco Alves Neto",   "folfox_d1",          YESTERDAY, municipio="Cidade C", nome_mae="Ana Alves",       nasc="22/11/1952", total_ciclos=12, horario="07:15", poltrona=3)
ev(id1, ("punção", "07:05"), ("pré-QT", "07:15"), ("QT", "07:55"), ("retirada", "08:45"), ("higienização", "08:55"))
ev(id2, ("punção", "07:20"), ("pré-QT", "07:30"), ("QT", "07:50"), ("retirada", "08:40"), ("higienização", "08:50"))
ev(id3, ("punção", "07:15"), ("pré-QT", "07:25"), ("QT", "08:40"), ("retirada", "11:10"), ("higienização", "11:20"))

# ── Hoje ─────────────────────────────────────────────────────────────────────
# Em atendimento
id_a = ag("José Ferreira de Sousa",  "carbo_paclit_q3w", TODAY, municipio="Cidade A", nome_mae="Maria Ferreira",     nasc="15/06/1961", total_ciclos=6, horario="07:00", poltrona=1)
id_b = ag("Raimunda Alves Carvalho", "r_chop",           TODAY, municipio="Cidade D", nome_mae="Benedita Alves",     nasc="08/02/1970", total_ciclos=8, horario="07:00", poltrona=2)
id_c = ag("Luiz Carlos Ferreira",    "gencit_cis",       TODAY, municipio="Cidade E", nome_mae="Conceição Ferreira", nasc="30/10/1955", total_ciclos=6, horario="07:15", poltrona=3)
ev(id_a, ("punção", "07:05"), ("pré-QT", "07:15"), ("QT", "07:50"))
ev(id_b, ("punção", "07:10"), ("pré-QT", "07:20"), ("QT", "08:00"))
ev(id_c, ("punção", "07:20"), ("pré-QT", "07:30"))

# Com poltrona, aguardando punção
ag("Ana Beatriz Costa",     "paclitaxel_semanal", TODAY, municipio="Cidade B", nome_mae="Socorro Costa", nasc="17/03/1975", total_ciclos=12, horario="08:00", poltrona=4)
ag("Marta Regina Borges",   "tc",                 TODAY, municipio="Cidade A", nome_mae="Irene Borges",  nasc="29/07/1968", total_ciclos=8,  horario="08:00", poltrona=5)
ag("Sebastião Alves Torres","imunoterapia",       TODAY, municipio="Cidade F", nome_mae="Maria Torres",  nasc="04/12/1949", total_ciclos=6,  horario="08:30", poltrona=6)
ag("Rita de Cássia Mendes", "fac",                TODAY, municipio="Cidade G", nome_mae="Joana Mendes",  nasc="21/05/1978", total_ciclos=6,  horario="09:00", poltrona=7)
ag("Lúcia de Fátima Souza", "docetaxel_mono",     TODAY, municipio="Cidade C", nome_mae="Helena Souza",  nasc="11/08/1963", total_ciclos=6,  horario="09:30", poltrona=8)
ag("Francisca Sousa Oliveira", "trastuzumabe_1dose", TODAY, municipio="Cidade A", nome_mae="Conceição Sousa", nasc="02/06/1967", total_ciclos=6, is_convenio=True, horario="08:00", poltrona=26)

# Aguardando poltrona (aparecem no quadro de Hoje)
ag("Carlos Eduardo Lima",    "bevacizumabe", TODAY, municipio="Cidade B", nome_mae="Ana Lima",           nasc="05/01/1957", total_ciclos=10, horario="10:00")
ag("Benedita dos Santos",    "vinorelbina",  TODAY, municipio="Cidade A", nome_mae="Tereza Santos",      nasc="18/09/1972", total_ciclos=8,  horario="13:00")
ag("Pedro Henrique Maia",    "cisplatina_semanal", TODAY, municipio="Cidade B", nome_mae="Sandra Maia",  nasc="13/11/1983", total_ciclos=6,  status="walk_in", ordem_medica=True, horario="10:30")

# ── Agenda dos próximos dias (horário marcado; poltrona só no dia) ──────────
ag("Maria das Graças Silva",  "gencitabina_mono",   TOMORROW, municipio="Cidade A", total_ciclos=8,  horario="07:00")
ag("Antônio Neto Gomes",      "duplo_bloqueio",     TOMORROW, municipio="Cidade B", total_ciclos=6,  horario="07:00", is_convenio=True)
ag("Manoel Rodrigues Filho",  "xelox_d1",           TOMORROW, municipio="Cidade E", total_ciclos=8,  horario="07:30")
ag("Antônia Lima Rodrigues",  "trastuzumabe_manut", TOMORROW, municipio="Cidade B", total_ciclos=6,  horario="08:00")
ag("Francisco Alves Neto",    "folfox_d1",          TOMORROW, municipio="Cidade C", total_ciclos=12)   # sem horário ainda

ag("José Ferreira de Sousa",  "carbo_paclit_q3w",   D7,  municipio="Cidade A", total_ciclos=6,  horario="07:00")
ag("Raimunda Alves Carvalho", "r_chop",             D7,  municipio="Cidade D", total_ciclos=8,  horario="07:00")
ag("Luiz Carlos Ferreira",    "gencit_cis",         D7,  municipio="Cidade E", total_ciclos=6,  horario="08:00")
ag("Ana Beatriz Costa",       "paclitaxel_semanal", D7,  municipio="Cidade B", total_ciclos=12, horario="08:30")
ag("Marta Regina Borges",     "tc",                 D14, municipio="Cidade A", total_ciclos=8,  horario="07:30")
ag("Sebastião Alves Torres",  "imunoterapia",       D14, municipio="Cidade F", total_ciclos=6,  horario="09:00")

print("Seed concluído.")
