# Mapeamento Protocolos → Cor (bucket de duração de QT)

> **O que é este documento.** Lookup table para popular `t_qt[p]` no algoritmo de
> sequenciamento. Mapeia os principais protocolos usados em CACON brasileiro às cores
> (buckets de duração de QT) definidas pelos dados do centro.
>
> **Fonte dos tempos:** Protocolo Estadual SE/BR (Funesa/SE, 2019) — tempos explícitos;
> Guia de Enfermagem FCECON/AM (2024) — horários de início como proxy de duração;
> literatura clínica padrão (bulas/protocolo). Tempos são de infusão de QT, sem pré-med.
>
> **Pendência crítica:** confirmar na visita quais protocolos são de fato usados no centro
> (ver §Pendências). A tabela cobre o universo de um CACON brasileiro típico.

---

## Definição dos buckets (dados CACON, 262 sessões)

| Cor      | Faixa QT    | N na amostra | % |
|----------|-------------|:---:|:---:|
| 🟢 verde  | < 1h        | 78  | 30% |
| 🔵 azul   | 1h – 2h     | 95  | 36% |
| 🟡 amarelo| 2h – 4h     | 79  | 30% |
| 🔴 vermelho| > 4h       | 10  |  4% |

Ordem do pai: **Amarelos > Azuis > vermelho > verde** (longos primeiro).

---

## Tabela de mapeamento por tumor

### Mama

| Protocolo | Droga-âncora e tempo | Cor | Obs |
|---|---|:---:|---|
| Paclitaxel semanal (80 mg/m²) | Paclitaxel 1h | 🔵 azul | Mais comum adjuvante |
| AC (Doxo + Ciclo) | Doxo 15–30 min + Ciclo 30 min ≈ 1h | 🔵 azul | Pré-med domina o tempo total |
| FAC (5-FU + Doxo + Ciclo) | + 5-FU bolus 15 min ≈ 1,5h | 🔵 azul | |
| TC (Docetaxel + Ciclo) | Docetaxel 1h + Ciclo 30 min | 🔵/🟡 azul | Confirmar tempo local |
| CMF IV | Ciclo + MTX + 5-FU ≈ 1,5h | 🔵 azul | Alternativa se antraciclina CI |
| Paclitaxel q3w (175 mg/m²) | Paclitaxel **3h** | 🟡 amarelo | Tempo explícito: "IV 3h" |
| TAC (Docetaxel + Doxo + Ciclo) | Docetaxel 1h + Doxo 30 min + Ciclo 30 min ≈ 2,5h | 🟡 amarelo | |
| Trastuzumabe manutenção | Tras. **30 min** | 🟢 verde | Dose subsequente |
| Trastuzumabe 1ª dose | Tras. **90 min** | 🔵 azul | Dose de ataque |
| Pertuzumabe + Trastuzumabe (duplo bloqueio) | Pert. 60 min + Tras. 30–90 min ≈ 1,5h | 🔵 azul | |
| Carboplatina + Paclitaxel q3w | Paclit. 3h + Carbo 30–60 min ≈ 4h+ | 🔴 vermelho | Começa às 7h no FCECON |
| Carboplatina + Paclitaxel semanal | Paclit. 1h + Carbo 30 min ≈ 1,5h | 🔵 azul | |

### Colo do útero / Colo uterino

| Protocolo | Droga-âncora e tempo | Cor | Obs |
|---|---|:---:|---|
| Cisplatina semanal (40 mg/m²) — concomitante RT | Cis. 1–2h | 🔵 azul | Mais comum; com hidratação pode ir a 2h |
| Paclitaxel + Carboplatina | Paclit. 3h + Carbo 30–60 min ≈ 4h | 🔴/🟡 vermelho | Paliativo; borderline |
| 5-FU + Cisplatina | 5-FU bolus + Cis. 2h ≈ 2,5h | 🟡 amarelo | Protocolo Al-Sarraf |
| 5-FU infusional (24h) | Infusor portátil | — | Não ocupa poltrona após instalação |

### Colorretal

| Protocolo | Droga-âncora e tempo | Cor | Obs |
|---|---|:---:|---|
| FOLFOX (D1 no CACON) | Oxaliplatina **2h** + 5-FU bolus ≈ 2,5h; infusor em casa | 🟡 amarelo | 5-FU 46h vai pro infusor portátil |
| FOLFIRI (D1 no CACON) | Irinotecan **90 min** + 5-FU bolus ≈ 2h; infusor | 🔵/🟡 azul | Borderline; infusor em casa |
| XELOX (D1) | Oxaliplatina **2h** (Capecitabina é oral) | 🟡 amarelo | Capecitabina não ocupa poltrona |
| Capecitabina isolada | Oral — sem infusão | — | Não usa poltrona de QT |
| Bevacizumabe manutenção | Bev. 30 min | 🟢 verde | |
| Bevacizumabe 1ª dose | Bev. 60–90 min | 🔵 azul | |
| Cetuximabe | Cet. 1–2h (1ª dose 2h, subsequente 1h) | 🔵/🟡 azul | |

### Pulmão

| Protocolo | Droga-âncora e tempo | Cor | Obs |
|---|---|:---:|---|
| Carboplatina + Pemetrexede | Carbo 30 min + Pem. 10 min ≈ 1h (+ hidratação) | 🔵 azul | Com hidratação pode ir a 1,5h |
| Carboplatina + Paclitaxel q3w | Paclit. 3h + Carbo 30–60 min ≈ 4h | 🔴 vermelho | Começa às 7h no FCECON |
| Carboplatina + Paclitaxel semanal | Paclit. 1h + Carbo 30 min ≈ 1,5h | 🔵 azul | |
| Gencitabina + Cisplatina | Gem. 30 min + Cis. **2h** ≈ 2,5h | 🟡 amarelo | |
| Gencitabina + Carboplatina | Gem. 30 min + Carbo 30–60 min ≈ 1h | 🔵 azul | |
| Gencitabina monoterapia | Gem. **30 min** | 🟢 verde | |
| Etoposídeo + Cisplatina (D1 de multiday) | Etop. **1h** × 3 doses + Cis. **2h** ≈ 5h | 🔴 vermelho | Multiday; D1 é o mais longo |
| Pemetrexede monoterapia | Pem. **10 min** | 🟢 verde | |
| Imunoterapia (Nivolumabe/Pembrolizumabe) | 30–60 min | 🟢 verde | Cada dose é curta |

### Próstata

| Protocolo | Droga-âncora e tempo | Cor | Obs |
|---|---|:---:|---|
| Docetaxel + Prednisona q3w | Docetaxel **1h** | 🔵 azul | |
| Docetaxel q2w (50 mg/m²) | Docetaxel **1h** | 🔵 azul | Alternativa baixa dose |
| Cabazitaxel | Caba. **1h** | 🔵 azul | 2ª linha |

### Linfoma

| Protocolo | Droga-âncora e tempo | Cor | Obs |
|---|---|:---:|---|
| CHOP (sem Rituximabe) | Doxo 30 min + Ciclo 1h + Vincristina bolus + Pred VO ≈ 2h | 🟡 amarelo | |
| R-CHOP (1ª dose Rituximabe) | Ritual. **4h** + restante ≈ 6–8h total | 🔴 vermelho | 1ª dose é a mais longa |
| R-CHOP (doses subsequentes Rituximabe) | Ritual. **3h** + CHOP ≈ 5h | 🔴 vermelho | |
| R-COP (sem Doxo) | Ritual. 3–4h + COP ≈ 4–5h | 🔴 vermelho | Alternativa cardiopatia |
| ABVD (Linfoma Hodgkin) | Doxo + Bleomicina + Vinblastina + Dacarba ≈ 2–3h | 🟡 amarelo | |
| BEP D1 (Testículo/Germ) | Etop. 1h + Cis. **2h** + Bleo 30 min ≈ 3–4h | 🟡 amarelo | |

### Outros / transversais

| Protocolo | Droga-âncora e tempo | Cor | Obs |
|---|---|:---:|---|
| Ácido Zoledrônico | Zoled. **15 min** (ou 2h — depende protocolo) | 🟢 verde | Confirmar protocolo local |
| Denosumabe | SC — sem infusão EV | — | Não usa poltrona de QT |
| Vinorelbina IV | Vinor. **6–10 min** (bolus) | 🟢 verde | |
| Dacarbazina | Dacarba **30–60 min** | 🟢/🔵 verde | |
| Irinotecan monoterapia | Irinot. **90 min** | 🔵 azul | |
| Oxaliplatina monoterapia | Oxali. **2h** | 🟡 amarelo | |
| Fludarabina | Fluda. **30 min** | 🟢 verde | |

---

## Resumo por cor (protocolos-âncora por bucket)

| Cor | Protocolos mais prováveis no CACON |
|---|---|
| 🟢 verde (< 1h) | Gencitabina mono, Trastuzumabe manutenção, Pemetrexede, Imunoterapia (nivolumabe/pembrolizumabe), Vinorelbina, Bortezomibe, Zoledronato |
| 🔵 azul (1–2h) | Paclitaxel semanal, AC, FAC, TC, CMF, Docetaxel mono, Cisplatina semanal (colo do útero), Trastuzumabe 1ª dose, Duplo bloqueio, Carbo+Pem, Carbo+Paclit semanal, Gencit+Carbo, FOLFIRI D1, Bevacizumabe, Docetaxel próstata |
| 🟡 amarelo (2–4h) | Paclitaxel q3w, FOLFOX D1, XELOX D1, TAC, Gencit+Cis, ABVD, BEP D1, CHOP, 5-FU+Cis, Cisplatina plena |
| 🔴 vermelho (> 4h) | Carbo+Paclit q3w, R-CHOP (qualquer dose), Etoposídeo+Cis D1, Daratumumabe 1ª dose |

---

## Pendências — confirmar na visita

1. **Quais protocolos são de fato usados no CACON?** A tabela cobre um CACON genérico.
   A visita é a chance de perguntar à farmacêutica (origem do projeto) quais protocolos ela
   manipula mais e se ela já tem uma lista de protocolos × tumor no sistema.

2. **Cisplatina para colo do útero:** duração varia com protocolo e hidratação.
   Confirmar se é semanal 40 mg/m² (azul) ou plena (amarelo).

3. **FOLFOX/FOLFIRI:** o tempo "na poltrona" depende de quando o infusor portátil é conectado.
   Se o centro usa infusor (bomba elastomérica), o D1 em poltrona é ~2–2,5h (amarelo/azul).
   Se não usa infusor, o 5-FU 46h demanda internação → fora do ambulatório.

4. **Rituximabe:** se o centro tem Linfoma com R-CHOP, 1ª dose Rituximabe ocupa poltrona por
   4h+ — vermelho sólido. Confirmar se hemato é tratado no CACON ou em outro serviço.

5. **Cor dos protocolos no sistema do pai:** a planilha usa vermelho/azul/verde/amarelo mas
   não nomeia protocolos. Perguntar se eles têm mapeamento interno protocolo → cor.
   Se tiverem, esta tabela é só validação.

---

## Como usar no algoritmo

```python
# Mapa de lookup: nome_protocolo → minutos_qt_mediana
PROTOCOLO_COR = {
    # Verde < 60 min
    "gencitabina_mono":      ("verde", 30),
    "trastuzumabe_manut":    ("verde", 30),
    "pemetrexede_mono":      ("verde", 10),
    "vinorelbina_iv":        ("verde", 15),
    "imunoterapia":          ("verde", 45),

    # Azul 60–120 min
    "paclitaxel_semanal":    ("azul", 60),
    "ac":                    ("azul", 90),
    "fac":                   ("azul", 90),
    "tc":                    ("azul", 90),
    "docetaxel_mono":        ("azul", 60),
    "cisplatina_semanal":    ("azul", 90),
    "trastuzumabe_1dose":    ("azul", 90),
    "duplo_bloqueio":        ("azul", 90),
    "carbo_pem":             ("azul", 90),
    "carbo_paclit_semanal":  ("azul", 90),
    "docetaxel_prostata":    ("azul", 60),

    # Amarelo 120–240 min
    "paclitaxel_q3w":        ("amarelo", 180),
    "folfox_d1":             ("amarelo", 150),
    "xelox_d1":              ("amarelo", 120),
    "tac":                   ("amarelo", 150),
    "gencit_cis":            ("amarelo", 150),
    "abvd":                  ("amarelo", 150),
    "bep_d1":                ("amarelo", 180),
    "chop":                  ("amarelo", 120),
    "cisplatina_plena":      ("amarelo", 180),

    # Vermelho > 240 min
    "carbo_paclit_q3w":      ("vermelho", 270),
    "r_chop":                ("vermelho", 360),
    "etop_cis_d1":           ("vermelho", 300),
    "daratumumabe_1dose":    ("vermelho", 420),
}
```

> **Nota:** os minutos são estimativas medianas para uso no scheduling. A visita deve calibrar
> os valores reais para os protocolos do centro. O algoritmo só precisa de granularidade de
> bucket (cor), não de minuto exato.
