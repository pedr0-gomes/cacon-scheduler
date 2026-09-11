#!/usr/bin/env python3
"""
CACON Scheduler — alocação por recursos (MVP)

Entrada (D-1): lista de pacientes com protocolo → escala de chegada + poltrona.

Modelo: em vez de um recurso agregado ("staff"), modela os recursos reais como
pools derivados da ESCALA de profissionais — técnico de punção, enfermeiro de QT,
montagem — e aloca cada paciente no primeiro horário viável em TODOS eles.
As restrições da modelagem (docs/modelagem-problema.md) caem naturalmente do modelo
de capacidade (ex.: "nenhuma QT antes das 7h" emerge de capacidade_qt(6h–7h)=0).

Princípio (docs/modelagem-problema.md): estimar → implantar → mensurar → otimizar.
Toda estimativa está nomeada no bloco 1; o sistema registra timestamps de cada
evento e essas estimativas se recalibram com o uso. Próximo passo algorítmico
depois de calibrado: CP-SAT (OR-Tools) — ver modelagem-problema.md §CP-SAT.
"""

from dataclasses import dataclass, field, replace
from typing import List, Optional
import math

# ===========================================================================
# 1. ESTIMATIVAS CALIBRÁVEIS
#    Todas iniciais — o sistema mede e refina. Um lugar só para ajustar.
# ===========================================================================

# --- Tempos (minutos) ---
T_PUNCAO           = 8    # punção em si (bloqueio instantâneo do técnico)
T_2A_OFFSET        = 25   # técnico volta ~25 min após a punção (retira a pré-med)
T_2A_DUR           = 5    # duração dessa segunda interação
T_MONTAGEM         = 15   # montagem da droga por paciente (1 técnico rotativo)
T_HIGIENIZACAO     = 5    # limpeza da poltrona antes do próximo paciente
T_ENF_INICIO_QT    = 5    # enfermeiro pendura a droga / inicia a QT
GAP_PRE_QT         = 10   # fim da pré-med → início da QT (mediana ~5, média 11)
GAP_SAIDA          = 12   # fim da QT → paciente deixa a poltrona

# --- Offset de chegada ao hospital (minutos antes da punção prevista) ---
# Informado ao paciente pelo profissional do agendamento para que os trâmites
# (recepção, cadastro) terminem antes do atendimento. Estimativa inicial;
# calibrar com dados reais do fluxo de entrada.
OFFSET_CHEGADA_HOSPITAL = 120

# --- Vazão (o parâmetro-rei do teto do dia) ---
# Dado de campo (docs/analise-campo.md §6): teto demonstrado ~10 punções/h com
# 5–6 técnicos (~2/h por técnico, em rajada); média atual realizada ~1,1/h por
# técnico (operação sem sequenciamento). O alcançável sustentado fica no meio.
# Este é o número que mais move o N_AGENDADO — o primeiro a calibrar com o real.
PUNCOES_POR_TECNICO_HORA = 1.49  # calibrado para teto Seg–Qui = 80 (54 téc-h × 1,49); Sex ≈ 77

# --- Taxas (para dimensionamento; refinam com o histórico) ---
TAXA_NAO_CONFIRMACAO = 0.20  # % que não confirma em D-1 (libera slot walk-in)
TAXA_REACAO_ADVERSA  = 0.08  # 5–10% — margem operacional
RAZAO_WALK_IN        = 0.20  # fração da capacidade reservada ao dia (walk-in)

# --- Poltronas ---
N_POLTRONAS = 34             # 1–25 SUS, 26–30 convênio, 31–34 hemato

# --- Janela do dia (minutos desde 0h) ---
DIA_INI        = 6 * 60      # 06:00 — abertura
DIA_FIM        = 20 * 60     # 20:00 — teto das arrays (sessões longas terminam antes)
ULTIMA_CHEGADA = 16 * 60     # 16:00 — última punção do dia (margem p/ terminar)
HORA_MIN_QT    = 7 * 60      # 07:00 — nenhuma QT inicia antes (redundante c/ escala; explícito)


def h(hora: int, minuto: int = 0) -> int:
    """Minutos desde 0h. Açúcar para escrever a escala legível."""
    return hora * 60 + minuto


# ===========================================================================
# 2. ESCALA DE PROFISSIONAIS  (a fonte da capacidade)
#    Calibrar a capacidade = editar esta lista, não recomputar curvas.
#    Escala real levantada com a farmacêutica em 09/set (ver CONTEXT §Escala real).
# ===========================================================================

@dataclass(frozen=True)
class Profissional:
    """Um profissional num turno. funcao define de que pool ele participa.
    Disponível em t se está dentro do turno e fora do intervalo de 1h."""
    funcao: str          # enfermeiro | enfermeiro_triagem | tecnico | tecnico_hemato | limpeza
    entrada: int
    saida: int
    alm_ini: int         # início do intervalo de 1h
    alm_fim: int

    def disponivel(self, t: int) -> bool:
        return self.entrada <= t < self.saida and not (self.alm_ini <= t < self.alm_fim)


# Seg–Qui: 9h trabalho + 1h intervalo = 10h no relógio. Entradas escalonadas 6/7/8h.
ESCALA_SEGQUI: List[Profissional] = [
    # Enfermeiros (4) — triagem é dedicada ao sistema, não entra no pool de QT
    Profissional("enfermeiro_triagem", h(6), h(16), h(11), h(12)),
    Profissional("enfermeiro",         h(7), h(17), h(12), h(13)),
    Profissional("enfermeiro",         h(7), h(17), h(12), h(13)),
    Profissional("enfermeiro",         h(8), h(18), h(13), h(14)),
    # Técnicos de salão (8) — 1 deles fica sempre na montagem (descontado no pool)
    Profissional("tecnico",            h(6), h(16), h(11), h(12)),
    Profissional("tecnico",            h(6), h(16), h(11), h(12)),
    Profissional("tecnico",            h(7), h(17), h(11), h(12)),
    Profissional("tecnico",            h(7), h(17), h(11), h(12)),
    Profissional("tecnico",            h(7), h(17), h(12), h(13)),
    Profissional("tecnico",            h(7), h(17), h(12), h(13)),
    Profissional("tecnico",            h(8), h(18), h(13), h(14)),
    Profissional("tecnico",            h(8), h(18), h(13), h(14)),
    # Técnica da hematoterapia (1) — exclusiva das poltronas 31–34, pool à parte
    Profissional("tecnico_hemato",     h(7), h(17), h(12), h(13)),
    # Limpeza (2) — turno partido modelado como intervalo longo
    Profissional("limpeza",            h(6), h(16), h(11), h(13)),
    Profissional("limpeza",            h(10), h(20), h(13), h(15)),
]


def _sexta(escala: List[Profissional]) -> List[Profissional]:
    """Sex: todos saem 1h mais cedo (8h trabalho + 1h intervalo = 9h no relógio)."""
    return [replace(p, saida=p.saida - 60) for p in escala]


ESCALA_SEX = _sexta(ESCALA_SEGQUI)


def _escala_do_dia(dia_semana: Optional[int]) -> List[Profissional]:
    """dia_semana: 0=seg … 6=dom (date.weekday()). 4=sex tem escala reduzida."""
    if dia_semana == 4:
        return ESCALA_SEX
    return ESCALA_SEGQUI


def _presentes(escala: List[Profissional], funcao: str, t: int) -> int:
    return sum(1 for p in escala if p.funcao == funcao and p.disponivel(t))


def capacidade_puncao(t: int, escala: Optional[List[Profissional]] = None) -> int:
    """Técnicos disponíveis para punção no minuto t.
    = técnicos de salão presentes − 1 (sempre na montagem) − lanche.
    (hemato é pool à parte; nunca entrou aqui.)"""
    escala = escala or ESCALA_SEGQUI
    pool = _presentes(escala, "tecnico", t)
    if pool >= 1:
        pool -= 1  # 1 técnico sempre dedicado à montagem
    return max(0, pool)


def capacidade_qt(t: int, escala: Optional[List[Profissional]] = None) -> int:
    """Enfermeiros disponíveis para iniciar QT no minuto t.
    Triagem não conta (dedicada ao sistema). 0 antes das 7h → restrição 3 emerge."""
    escala = escala or ESCALA_SEGQUI
    pool = _presentes(escala, "enfermeiro", t)
    return max(0, pool)


# ===========================================================================
# 3. CAPACIDADE DO DIA  (N_AGENDADO / N_WALK_IN dinâmicos)
#    Substitui as constantes fixas 20/14 — o teto é calculado da escala.
# ===========================================================================

def capacidade_do_dia(escala: Optional[List[Profissional]] = None, dia_semana: Optional[int] = None) -> dict:
    """Teto de pacientes do dia = técnico-horas de punção × vazão por técnico.
    Reparte agendado/walk-in por RAZAO_WALK_IN."""
    if escala is None:
        escala = _escala_do_dia(dia_semana)
    tecnico_min = sum(capacidade_puncao(t, escala) for t in range(DIA_INI, ULTIMA_CHEGADA))
    tecnico_horas = tecnico_min / 60
    teto = int(tecnico_horas * PUNCOES_POR_TECNICO_HORA)
    n_walk_in = round(teto * RAZAO_WALK_IN)
    n_agendado = teto - n_walk_in
    return {
        "teto":          teto,
        "n_agendado":    n_agendado,
        "n_walk_in":     n_walk_in,
        "tecnico_horas": round(tecnico_horas, 1),
    }


# --- Compatibilidade: STAFF_CURVE derivada da escala (bandas visuais da triagem) ---
def _derivar_curva(escala: Optional[List[Profissional]] = None) -> list:
    """Agrupa capacidade_puncao(t) em janelas de valor constante → (ini, fim, n).
    Alimenta a UI antiga (capacidade_por_janela) com a curva REAL, não 4/4/2/4."""
    escala = escala or ESCALA_SEGQUI
    curva, ini, atual = [], DIA_INI, capacidade_puncao(DIA_INI, escala)
    for t in range(DIA_INI + 1, DIA_FIM + 1):
        n = capacidade_puncao(t, escala) if t < DIA_FIM else None
        if n != atual:
            curva.append((ini, t, atual))
            ini, atual = t, n
    return curva


STAFF_CURVE = _derivar_curva()


def curva_do_dia(dia_semana: Optional[int] = None) -> list:
    """Curva de pool de punção derivada da escala do dia (sexta sai 1h mais cedo).
    dia_semana: 0=seg … 6=dom (date.weekday())."""
    return _derivar_curva(_escala_do_dia(dia_semana))

# Referência de carga por papel no painel (pico realista da escala Seg–Qui).
# Candidato a virar dinâmico por janela (hoje é um teto único para a barra).
STAFF_REFERENCIA = {"tecnico": 7, "enfermeiro": 3, "limpeza": 2}


def staff_agora(t: int, dia_semana: Optional[int] = None) -> dict:
    """Pool disponível de cada papel no minuto t do dia. dia_semana: 0=seg…6=dom."""
    escala = _escala_do_dia(dia_semana)
    return {
        "tecnico":    capacidade_puncao(t, escala),
        "enfermeiro": capacidade_qt(t, escala),
        "limpeza":    _presentes(escala, "limpeza", t),
    }


def staff_em(t: int, curve=None) -> int:
    """Compat: pool de punção no minuto t (usado por app.py)."""
    return capacidade_puncao(t)


def e_janela_reduzida(t: int, curve=None) -> bool:
    pico = max((n for _, _, n in STAFF_CURVE), default=0)
    return capacidade_puncao(t) < pico


def capacidade_por_janela(curve=None) -> list:
    """Descreve cada janela de staff com sua capacidade (duração_h × pool)."""
    curve = curve or STAFF_CURVE
    result = []
    for inicio, fim, staff in curve:
        duracao_h = (fim - inicio) / 60
        hi, hm = divmod(inicio, 60)
        fi, fm = divmod(fim, 60)
        result.append({
            "label":      f"{hi:02d}:{hm:02d}–{fi:02d}:{fm:02d}",
            "staff":      staff,
            "inicio":     inicio,
            "fim":        fim,
            "capacidade": int(duracao_h * staff),
        })
    return result


# ===========================================================================
# 4. LOOKUPS  (protocolo → cor/pré-med, durações, ciclos) — inalterados
#    Ver docs/mapeamento-protocolos-cor.md e mapeamento-premed-duracao.md
# ===========================================================================

QT_MIN = {
    "verde":    45,   # < 60 min  — ponto médio
    "azul":     90,   # 60–120 min
    "amarelo": 150,   # 120–240 min
    "vermelho": 300,  # > 240 min
}

PRE_MIN = {
    "Z":  0,   # sem pré-med
    "A": 15,   # mínima
    "B": 35,   # padrão (antiemético + anti-histamínico + corticoide)
    "C": 90,   # longa com hidratação (cisplatina plena, ifosfamida, BEP)
}

# Protocolos multi-aplicação: intervalos rotativos (dias). Índice = (ciclo-1) % len.
CICLO_MULTIAPP = {
    "gencitabina_mono": [7, 7, 13],  # D1→D8, D8→D15, D15→D1-próximo (ciclo 28d)
    "vinorelbina":       [7, 13],     # D1→D8, D8→D1-próximo (ciclo 21d)
}

INTERVALO_CICLO = {
    "gencitabina_mono":      7,
    "trastuzumabe_manut":   21,
    "pemetrexede_mono":     21,
    "vinorelbina":           7,
    "imunoterapia":         21,
    "vincristina":          21,
    "bleomicina":           28,
    "bortezomibe_sc":       28,
    "bevacizumabe":         14,
    "paclitaxel_semanal":    7,
    "ac":                   21,
    "fac":                  21,
    "tc":                   21,
    "cmf":                  28,
    "docetaxel_mono":       21,
    "cisplatina_semanal":    7,
    "trastuzumabe_1dose":   21,
    "duplo_bloqueio":       21,
    "carbo_pem":            21,
    "carbo_paclit_semanal":  7,
    "gencit_carbo":         21,
    "folfiri_d1":           14,
    "docetaxel_prostata":   21,
    "irinotecan_mono":      21,
    "paclitaxel_q3w":       21,
    "folfox_d1":            14,
    "xelox_d1":             21,
    "tac":                  21,
    "gencit_cis":           21,
    "abvd":                 28,
    "bep_d1":               21,
    "chop":                 21,
    "cisplatina_plena":     21,
    "oxaliplatina_mono":    21,
    "carbo_paclit_q3w":     21,
    "r_chop":               21,
    "etop_cis_d1":          21,
    "daratumumabe_1dose":   28,
}

# Protocolo → (cor_qt, bucket_pre)
PROTOCOLO = {
    # Verde / mínima ou sem pré-med
    "gencitabina_mono":     ("verde",    "A"),
    "trastuzumabe_manut":   ("verde",    "A"),
    "pemetrexede_mono":     ("verde",    "A"),
    "vinorelbina":          ("verde",    "A"),
    "imunoterapia":         ("verde",    "A"),
    "vincristina":          ("verde",    "Z"),
    "bleomicina":           ("verde",    "Z"),
    "bortezomibe_sc":       ("verde",    "Z"),
    "bevacizumabe":         ("verde",    "Z"),
    # Azul
    "paclitaxel_semanal":   ("azul",     "B"),
    "ac":                   ("azul",     "B"),
    "fac":                  ("azul",     "B"),
    "tc":                   ("azul",     "B"),
    "cmf":                  ("azul",     "B"),
    "docetaxel_mono":       ("azul",     "B"),
    "cisplatina_semanal":   ("azul",     "B"),
    "trastuzumabe_1dose":   ("azul",     "B"),
    "duplo_bloqueio":       ("azul",     "B"),
    "carbo_pem":            ("azul",     "B"),
    "carbo_paclit_semanal": ("azul",     "B"),
    "gencit_carbo":         ("azul",     "B"),
    "folfiri_d1":           ("azul",     "B"),
    "docetaxel_prostata":   ("azul",     "B"),
    "irinotecan_mono":      ("azul",     "B"),
    # Amarelo
    "paclitaxel_q3w":       ("amarelo",  "B"),
    "folfox_d1":            ("amarelo",  "B"),
    "xelox_d1":             ("amarelo",  "B"),
    "tac":                  ("amarelo",  "B"),
    "gencit_cis":           ("amarelo",  "C"),
    "abvd":                 ("amarelo",  "B"),
    "bep_d1":               ("amarelo",  "C"),
    "chop":                 ("amarelo",  "B"),
    "cisplatina_plena":     ("amarelo",  "C"),
    "oxaliplatina_mono":    ("amarelo",  "B"),
    # Vermelho
    "carbo_paclit_q3w":     ("vermelho", "B"),
    "r_chop":               ("vermelho", "B"),
    "etop_cis_d1":          ("vermelho", "C"),
    "daratumumabe_1dose":   ("vermelho", "B"),
}

# Ordem de prioridade da cor (longos primeiro — regra do pai, ver estado-da-arte §2)
COR_PRIORIDADE = {"azul": 0, "vermelho": 1, "amarelo": 2, "verde": 3}

# Carga por papel por estágio (barras do painel). 1.0 = recurso dedicado do papel.
CARGA_POR_PAPEL = {
    "aguardando_puncao":       {"tecnico": 1.0, "enfermeiro": 0.0, "limpeza": 0.0},
    "aguardando_preqt":        {"tecnico": 0.4, "enfermeiro": 0.0, "limpeza": 0.0},
    "aguardando_qt":           {"tecnico": 0.0, "enfermeiro": 0.2, "limpeza": 0.0},
    "aguardando_retirada":     {"tecnico": 0.0, "enfermeiro": 1.0, "limpeza": 0.0},
    "aguardando_higienizacao": {"tecnico": 0.0, "enfermeiro": 0.0, "limpeza": 1.0},
    "livre":                   {"tecnico": 0.0, "enfermeiro": 0.0, "limpeza": 0.0},
}


# ===========================================================================
# 5. ESTRUTURAS DE DADOS
# ===========================================================================

@dataclass
class Paciente:
    nome: str
    protocolo: str
    pre_override: Optional[str] = None
    qt_override_min: Optional[int] = None
    flexibilidade: str = "alta"   # "alta" | "baixa"
    is_convenio: bool = False
    municipio: Optional[str] = None
    cor_qt: str    = field(init=False)
    bucket_pre: str = field(init=False)

    def __post_init__(self):
        if self.protocolo not in PROTOCOLO:
            raise ValueError(f"Protocolo desconhecido: {self.protocolo!r}. "
                             f"Adicione em PROTOCOLO ou use cor_qt/bucket_pre diretamente.")
        cor, bucket = PROTOCOLO[self.protocolo]
        self.cor_qt = cor
        self.bucket_pre = self.pre_override if (self.pre_override and self.pre_override in PRE_MIN) else bucket

    @property
    def t_pre(self) -> int:
        return PRE_MIN[self.bucket_pre]

    @property
    def t_qt(self) -> int:
        if self.qt_override_min is not None:
            return self.qt_override_min
        return QT_MIN[self.cor_qt]

    @property
    def t_total(self) -> int:
        """Tempo total estimado na poltrona (pré + gap + QT + saída)."""
        return self.t_pre + GAP_PRE_QT + self.t_qt + GAP_SAIDA


@dataclass
class PacienteManual:
    """Para protocolos não mapeados — informa cor e bucket diretamente."""
    nome: str
    protocolo: str
    cor_qt: str
    bucket_pre: str
    flexibilidade: str = "alta"
    is_convenio: bool = False

    @property
    def t_pre(self) -> int:
        return PRE_MIN[self.bucket_pre]

    @property
    def t_qt(self) -> int:
        return QT_MIN[self.cor_qt]

    @property
    def t_total(self) -> int:
        return self.t_pre + GAP_PRE_QT + self.t_qt + GAP_SAIDA


@dataclass
class Sessao:
    paciente: object
    chegada: int          # minuto da chegada / punção
    poltrona: int         # 1-indexed
    inicio_pre: int
    inicio_qt: int
    saida_est: int
    fim_montagem: int = 0   # droga pronta (gargalo de montagem)
    inicio_2a: int = 0      # 2ª interação do técnico (retirada da pré-med)
    saturado: bool = False  # True se alocado no fallback (capacidade do dia estourada)


# ===========================================================================
# 6. ALGORITMO — alocação por recursos (Heijunka + DBR sobre pools reais)
# ===========================================================================

def _chave_ordenacao(p):
    """Longos primeiro (vermelho→verde); dentro da cor, flex 'baixa' antes; t_total desc."""
    flex = getattr(p, "flexibilidade", "alta")
    return (COR_PRIORIDADE[p.cor_qt], 0 if flex == "baixa" else 1, -p.t_total)


def _primeira_poltrona(disponivel: List[int], t: int, is_convenio: bool) -> Optional[int]:
    """Índice da primeira poltrona livre em t, ou None. Convênio → 26–30 (idx 25–29)."""
    indices = range(25, 30) if is_convenio else range(len(disponivel))
    for i in indices:
        if disponivel[i] <= t:
            return i
    return None


def gerar_escala(
    pacientes: List,
    escala: Optional[List[Profissional]] = None,
    dia_semana: Optional[int] = None,
    n_poltronas: int = N_POLTRONAS,
) -> List[Sessao]:
    """
    Para cada paciente (longos primeiro), acha o horário de chegada mais cedo
    (a partir do ideal Heijunka) em que há capacidade em TODOS os recursos:
      1. técnico livre para a punção            [t, t+T_PUNCAO)
      2. técnico livre para a 2ª interação      [t+T_2A_OFFSET, +T_2A_DUR)   (restrição 4)
      3. poltrona livre (regra convênio)                                     (restrição 6)
      4. montagem entrega a droga (1 servidor, fila)                         (restrição 5)
      5. enfermeiro livre para iniciar a QT, ≥ 7h                            (restrições 2,3)
    Punção simultânea ≤ pool técnico e QT simultânea ≤ pool enfermeiro são
    garantidas pelos contadores por minuto (restrições 1,2).
    """
    escala = escala or _escala_do_dia(dia_semana)
    n = len(pacientes)
    if n == 0:
        return []

    N = DIA_FIM - DIA_INI
    cap_tec = [capacidade_puncao(DIA_INI + i, escala) for i in range(N)]
    cap_enf = [capacidade_qt(DIA_INI + i, escala) for i in range(N)]
    usado_tec = [0] * N
    usado_enf = [0] * N
    montagem_livre = DIA_INI                       # 1 servidor de montagem (FIFO)
    disponivel_pol = [DIA_INI] * n_poltronas       # minuto em que cada poltrona fica livre

    def _tec_livre(ini: int, dur: int) -> bool:
        for t in range(ini, ini + dur):
            i = t - DIA_INI
            if i < 0 or i >= N or usado_tec[i] >= cap_tec[i]:
                return False
        return True

    def _enf_livre(ini: int, dur: int) -> bool:
        for t in range(ini, ini + dur):
            i = t - DIA_INI
            if i < 0 or i >= N or usado_enf[i] >= cap_enf[i]:
                return False
        return True

    def _ocupa(arr, ini, dur):
        for t in range(ini, ini + dur):
            arr[t - DIA_INI] += 1

    def _proximo_enf(ini_min: int, dur: int) -> Optional[int]:
        for t in range(max(ini_min, HORA_MIN_QT), DIA_FIM - dur):
            if _enf_livre(t, dur):
                return t
        return None

    takt = (ULTIMA_CHEGADA - DIA_INI) / n
    ordenados = sorted(pacientes, key=_chave_ordenacao)

    sessoes: List[Sessao] = []
    for seq, p in enumerate(ordenados):
        chegada_ideal = DIA_INI + round(seq * takt)
        is_conv = getattr(p, "is_convenio", False)

        alocado = None
        for t in range(chegada_ideal, ULTIMA_CHEGADA):
            if not _tec_livre(t, T_PUNCAO):
                continue
            if not _tec_livre(t + T_2A_OFFSET, T_2A_DUR):
                continue
            poltrona = _primeira_poltrona(disponivel_pol, t, is_conv)
            if poltrona is None:
                continue
            # Montagem: inicia após a punção, servidor único em fila
            ini_montagem = max(t + T_PUNCAO, montagem_livre)
            fim_montagem = ini_montagem + T_MONTAGEM
            # QT: após pré-med, após droga pronta, ≥ 7h, com enfermeiro livre
            qt_min = max(t + p.t_pre + GAP_PRE_QT, fim_montagem, HORA_MIN_QT)
            inicio_qt = _proximo_enf(qt_min, T_ENF_INICIO_QT)
            if inicio_qt is None:
                continue
            alocado = (t, poltrona, fim_montagem, inicio_qt)
            break

        if alocado is None:
            # Overflow: capacidade do dia estourada. Best-effort — nunca some paciente.
            t = chegada_ideal
            poltrona = _primeira_poltrona(disponivel_pol, t, is_conv)
            if poltrona is None:
                poltrona = min(range(n_poltronas), key=lambda i: disponivel_pol[i])
            fim_montagem = max(t + T_PUNCAO, montagem_livre) + T_MONTAGEM
            inicio_qt = max(t + p.t_pre + GAP_PRE_QT, fim_montagem, HORA_MIN_QT)
            saturado = True
        else:
            t, poltrona, fim_montagem, inicio_qt = alocado
            saturado = False
            _ocupa(usado_tec, t, T_PUNCAO)
            _ocupa(usado_tec, t + T_2A_OFFSET, T_2A_DUR)
            _ocupa(usado_enf, inicio_qt, T_ENF_INICIO_QT)
            montagem_livre = fim_montagem

        saida = inicio_qt + p.t_qt + GAP_SAIDA
        disponivel_pol[poltrona] = saida + T_HIGIENIZACAO

        sessoes.append(Sessao(
            paciente=p,
            chegada=t,
            poltrona=poltrona + 1,
            inicio_pre=t,
            inicio_qt=inicio_qt,
            saida_est=saida,
            fim_montagem=fim_montagem,
            inicio_2a=t + T_2A_OFFSET,
            saturado=saturado,
        ))

    sessoes.sort(key=lambda s: s.chegada)
    return sessoes


# ===========================================================================
# 7. SAÍDA / DEMO
# ===========================================================================

def _fmt(minutos: int) -> str:
    h_, m = divmod(int(minutos), 60)
    return f"{h_:02d}:{m:02d}"


def _cor_label(cor: str) -> str:
    return {"verde": "verde", "azul": "azul",
            "amarelo": "amarelo", "vermelho": "verm."}.get(cor, cor)


def imprimir_escala(sessoes: List[Sessao]) -> None:
    print()
    print("=" * 84)
    print("  ESCALA DE QUIMIOTERAPIA — CACON")
    print("=" * 84)
    header = (
        f"{'#':>3}  {'Paciente':<18} {'Protocolo':<20} {'Cor':<10} "
        f"{'Cheg':>6} {'Pol':>4} {'2ª':>6} {'Droga':>6} {'QT':>6} {'Saída':>6}"
    )
    print(header)
    print("-" * 84)
    for i, s in enumerate(sessoes, 1):
        p = s.paciente
        flag = " !" if s.saturado else ""
        print(
            f"{i:>3}  {p.nome:<18} {p.protocolo:<20} {_cor_label(p.cor_qt):<10} "
            f"{_fmt(s.chegada):>6} {s.poltrona:>4} {_fmt(s.inicio_2a):>6} "
            f"{_fmt(s.fim_montagem):>6} {_fmt(s.inicio_qt):>6} {_fmt(s.saida_est):>6}{flag}"
        )
    print("-" * 84)
    if sessoes:
        mais_cedo = min(s.chegada for s in sessoes)
        mais_tarde = max(s.saida_est for s in sessoes)
        poltronas_usadas = len({s.poltrona for s in sessoes})
        total_infusao = sum(s.paciente.t_qt for s in sessoes)
        total_ocup = sum(s.paciente.t_total for s in sessoes)
        util = total_infusao / total_ocup if total_ocup else 0
        saturados = sum(1 for s in sessoes if s.saturado)
        print(f"  {len(sessoes)} pacientes | poltronas: {poltronas_usadas} "
              f"| janela: {_fmt(mais_cedo)}–{_fmt(mais_tarde)} "
              f"| utilização: {util:.0%}"
              + (f" | SATURADOS: {saturados}" if saturados else ""))
    print("=" * 84)
    print()


if __name__ == "__main__":
    cap = capacidade_do_dia()
    print(f"\nCapacidade do dia (Seg–Qui): {cap['tecnico_horas']} téc-horas de punção "
          f"× {PUNCOES_POR_TECNICO_HORA}/h = teto {cap['teto']} "
          f"→ {cap['n_agendado']} agendados + {cap['n_walk_in']} walk-in")
    print("\nCurva de pool de punção (derivada da escala real):")
    for b in capacidade_por_janela():
        print(f"  {b['label']}  {b['staff']} técnicos")

    PACIENTES_DEMO = [
        Paciente("Ana Souza",       "carbo_paclit_q3w"),
        Paciente("José Lima",       "r_chop"),
        Paciente("Maria Ferreira",  "paclitaxel_q3w"),
        Paciente("Pedro Oliveira",  "folfox_d1"),
        Paciente("Luiza Cardoso",   "tac"),
        Paciente("Carlos Melo",     "abvd"),
        Paciente("Rita Santos",     "paclitaxel_q3w"),
        Paciente("João Neto",       "folfox_d1"),
        Paciente("Francisca Leal",  "xelox_d1"),
        Paciente("Antônio Gomes",   "chop"),
        Paciente("Raimunda Cruz",   "paclitaxel_q3w"),
        Paciente("Severino Brito",  "gencit_cis"),
        Paciente("Benedita Faria",  "cisplatina_plena"),
        Paciente("Manoel Rocha",    "bep_d1"),
        Paciente("Lúcia Dias",      "paclitaxel_semanal"),
        Paciente("Francisco Ramos", "ac"),
        Paciente("Tereza Lopes",    "docetaxel_mono"),
        Paciente("Paulo Vieira",    "fac"),
        Paciente("Conceição Pires", "tc"),
        Paciente("Marcos Alves",    "cisplatina_semanal"),
        Paciente("Sônia Barros",    "paclitaxel_semanal"),
        Paciente("Roberto Costa",   "docetaxel_prostata"),
        Paciente("Vera Mota",       "folfiri_d1"),
        Paciente("Cícero Freitas",  "carbo_pem"),
        Paciente("Aline Nascimento","ac"),
        Paciente("Edilson Cunha",   "duplo_bloqueio"),
        Paciente("Simone Teles",    "paclitaxel_semanal"),
        Paciente("Raimundo Assis",  "irinotecan_mono"),
        Paciente("Fátima Castro",   "trastuzumabe_1dose"),
        Paciente("Gilberto Mendes", "gencit_carbo"),
        Paciente("Helena Araujo",   "gencitabina_mono"),
        Paciente("Nilson Pereira",  "trastuzumabe_manut"),
        Paciente("Cleide Moura",    "bevacizumabe"),
        Paciente("Edson Queiroz",   "imunoterapia"),
        Paciente("Sueli Batista",   "gencitabina_mono"),
        Paciente("Wagner Ribeiro",  "pemetrexede_mono"),
        Paciente("Rosane Borges",   "trastuzumabe_manut"),
        Paciente("Djalma Correia",  "vinorelbina"),
        Paciente("Irene Monteiro",  "gencitabina_mono"),
        Paciente("Clóvis Sampaio",  "imunoterapia"),
        Paciente("Marlene Aguiar",  "trastuzumabe_manut"),
        Paciente("Eusébio Tavares", "bevacizumabe"),
        Paciente("Glória Figueiredo","gencitabina_mono"),
    ]
    sessoes = gerar_escala(PACIENTES_DEMO)
    imprimir_escala(sessoes)
