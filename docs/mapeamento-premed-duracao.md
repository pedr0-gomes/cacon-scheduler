# Mapeamento Pré-med → Duração (t_pre[p])

> **O que é este documento.** Lookup table para `t_pre[p]` no algoritmo de sequenciamento.
> Mapeia os principais protocolos à duração estimada de pré-medicação (tempo sentado na
> poltrona antes da QT começar).
>
> **Validação pelos dados CACON (229 sessões com pré-med, 34 sem):**
> - Mediana 25 min, média 33 min
> - 83% < 1h → bucket A/B domina
> - 17% entre 1h–2h → bucket C (hidratação)
> - 13% sem pré-med → bucket Z
>
> **Critério de classificação:** risco emetogênico (INCA/SBOC) + necessidade de hidratação
> pré-QT. Não é a pré-med em si que varia muito — é se tem hidratação obrigatória ou não.

---

## Definição dos buckets de pré-med

| Bucket | Duração estimada | Descrição |
|--------|-----------------|-----------|
| Z — sem pré-med | 0 min | Nenhuma pré-medicação EV |
| A — mínima | 10–20 min | Só antiemético VO ou 1 medicação IV rápida |
| B — padrão | 25–45 min | Antiemético IV ± anti-histamínico ± corticoide |
| C — longa (hidratação) | 60–120 min | Pré-hidratação SF/SG + manitol + antiemético |

> **Para o scheduler:** usar o ponto médio de cada bucket como `t_pre[p]`:
> Z = 0, A = 15, B = 35, C = 90 (minutos).

---

## Tabela por protocolo

### O que determina o bucket

| Regra | Bucket |
|---|:---:|
| Sem droga EV na sessão (oral, SC, VO) | Z |
| Risco emetogênico mínimo — uma droga simples | A |
| Alto risco emetogênico OU reação infusional (taxanos, antraciclinas) — sem hidratação | B |
| Cisplatina ≥ 50 mg/m² ou Ifosfamida — exige hidratação pré + manitol | C |

---

### Por protocolo/droga principal

| Protocolo | Pré-med típica | Bucket | Obs |
|---|---|:---:|---|
| **Paclitaxel** (qualquer dose) | Anti-histamínico (Difenidramina/Dexclorfeniramina) + Dexametasona + Ranitidina — 30 min | B | Mandatória p/ prevenir reação infusional; sem isso não se aplica |
| **Docetaxel** | Dexametasona oral D-1, D0, D+1 — só EV rápido no dia | B | Corticoide oral pré não conta como tempo de poltrona |
| **AC** (Doxo + Ciclo) | Ondansetrona + Dexametasona EV — 20–30 min | B | Alto emetogênico pela Doxo+Ciclo |
| **FAC / TAC** | Idem AC | B | |
| **TC** (Docetaxel + Ciclo) | Anti-histamínico + Dexametasona + Antiemético — 30–40 min | B | |
| **Carboplatina** (qualquer combinação) | Ondansetrona + Dexametasona — 20–30 min | B | Moderado emetogênico |
| **Cisplatina semanal** (40 mg/m²) | Ondansetrona + Dexametasona + SF 500 mL — 45–60 min | B/C | Dose baixa: hidratação leve; confirmar protocolo local |
| **Cisplatina plena** (≥ 50–75 mg/m²) | SF 500 mL–1 L + Manitol + Ondansetrona + Dexametasona — 1h–1h30 | C | Nefrotoxicidade exige pré-hidratação pesada |
| **Oxaliplatina** (FOLFOX/XELOX) | Ondansetrona + Dexametasona — 20–30 min | B | Leucovorin antes é parte do protocolo (pode sobrepor) |
| **Irinotecan** (FOLFIRI/mono) | Ondansetrona + Dexametasona — 20–30 min | B | Atropina SC se diarreia colinérgica: < 5 min |
| **Rituximabe** | Anti-histamínico + Paracetamol + Dexametasona — 30 min | B | Reação infusional, especialmente 1ª dose |
| **Trastuzumabe** | Anti-histamínico leve — 15 min (ou nenhum nas doses sub.) | A/Z | Confirmar protocolo local — pré-med varia por instituição |
| **Bevacizumabe** | Nenhuma obrigatória — pode ter antiemético se protocolo exigir | Z/A | Baixo risco de reação infusional |
| **Cetuximabe** | Anti-histamínico (Difenidramina) 30 min antes — 20–30 min | B | Reação infusional, especialmente 1ª dose |
| **Gencitabina** | Antiemético VO ou IV leve — 10–15 min | A | Baixo/moderado emetogênico |
| **Pemetrexede** | Dexametasona + Vitamina B12/Ácido fólico (VO D-1) — no dia: EV leve 15 min | A | Corticoide oral pré reduz toxicidade cutânea |
| **Etoposídeo** | Ondansetrona — 15–20 min | A | |
| **Vinorelbina** | Antiemético leve — 10–15 min | A | Baixo emetogênico |
| **Vincristina** | Geralmente nenhuma | Z | |
| **Bleomicina** | Antiemético leve VO, ou nenhuma | Z/A | |
| **Doxorrubicina Lipossomal** | Anti-histamínico + Dexametasona — 30 min | B | Reação infusional; velocidade de infusão lenta |
| **ABVD** | Ondansetrona + Dexametasona — 20–30 min | B | |
| **CHOP / R-CHOP** | Ondansetrona + Dexametasona + Anti-histamínico — 30–40 min | B | |
| **BEP** | Ondansetrona + Dexametasona + pré-hidratação Cisplatina | C | Cisplatina 60 mg/m² D1 → pré-hidratação obrigatória |
| **Ifosfamida** | SF 500 mL pré + Mesna (hora 0) — 45–60 min | C | Mesna vai junto, mas hidratação pré demora |
| **Daratumumabe** | Metilprednisolona + Anti-histamínico + Paracetamol — 45–60 min | B/C | Reação infusional intensa, especialmente 1ª dose |
| **Bortezomibe** (SC) | Geralmente nenhuma EV | Z | SC: sem infusão, sem pré-med EV |
| **Ácido Zoledrônico** | Hidratação oral antes — nenhuma EV | Z/A | |
| **Imunoterapia** (Nivolumabe/Pembrolizumabe) | Anti-histamínico leve — 15–20 min | A | Protocolo FCECON: 10h |

---

## Resumo por bucket (proporção esperada no centro)

| Bucket | Protocolos âncora | Proporção esperada |
|---|---|:---:|
| Z (sem pré-med) | Vincristina, bleomicina, bortezomibe SC, bevacizumabe | ~13% (validado na planilha) |
| A (10–20 min) | Gencitabina, pemetrexede, etoposídeo, vinorelbina, imunoterapia | ~15–20% |
| B (25–45 min) | Paclitaxel, docetaxel, AC, FAC, TC, carboplatina, rituximabe, CHOP | ~55–60% |
| C (60–120 min) | Cisplatina plena, ifosfamida, BEP | ~10–17% (validado: 17% > 1h) |

---

## Pendências — confirmar na visita

1. **Cisplatina semanal para colo do útero:** hidratação leve (B) ou pesada (C)?
   Depende do protocolo local. Faz diferença de ~30 min por paciente.

2. **Leucovorin no FOLFOX:** é infundido 2h antes do 5-FU, ou em bolus simultâneo com
   Oxaliplatina? Se 2h antes, encaixa na pré-med do FOLFOX e muda o bucket.

3. **Protocolo de pré-med do Paclitaxel local:** o centro usa Difenidramina ou
   Dexclorfeniramina? Faz diferença de 5–10 min (tempo de infusão).

4. **Pré-med das 34 sessões sem pré-med:** quais eram os protocolos? Pode revelar
   padrão (ex.: todos eram Trastuzumabe ou todos eram Bortezomibe).

---

## Snippet Python para o scheduler

```python
# t_pre[p] em minutos (ponto médio do bucket)
PRE_MED_BUCKET = {
    # Bucket Z — sem pré-med
    "vincristina":         ("Z", 0),
    "bleomicina":          ("Z", 0),
    "bortezomibe_sc":      ("Z", 0),
    "bevacizumabe":        ("Z", 0),

    # Bucket A — mínima (15 min)
    "gencitabina_mono":    ("A", 15),
    "pemetrexede_mono":    ("A", 15),
    "etoposideo":          ("A", 15),
    "vinorelbina":         ("A", 15),
    "imunoterapia":        ("A", 15),
    "trastuzumabe_manut":  ("A", 15),

    # Bucket B — padrão (35 min)
    "paclitaxel_semanal":  ("B", 35),
    "paclitaxel_q3w":      ("B", 35),
    "docetaxel_mono":      ("B", 35),
    "ac":                  ("B", 35),
    "fac":                 ("B", 35),
    "tc":                  ("B", 35),
    "carboplatina":        ("B", 35),
    "carbo_paclit_q3w":    ("B", 35),
    "oxaliplatina":        ("B", 35),
    "irinotecan":          ("B", 35),
    "rituximabe":          ("B", 35),
    "r_chop":              ("B", 35),
    "chop":                ("B", 35),
    "abvd":                ("B", 35),
    "trastuzumabe_1dose":  ("B", 35),
    "cisplatina_semanal":  ("B", 35),  # confirmar na visita

    # Bucket C — longa com hidratação (90 min)
    "cisplatina_plena":    ("C", 90),
    "bep_d1":              ("C", 90),
    "ifosfamida":          ("C", 90),
}
```
