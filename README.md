# CACON Scheduler

Sistema de agendamento e rastreio de fluxo para quimioterapia ambulatorial em centros oncológicos do SUS.

Desenvolvido originalmente para um CACON do interior do Nordeste e pensado para ser reutilizável em qualquer centro oncológico ambulatorial.

---

## O problema

Centros de quimioterapia ambulatorial do SUS acumulam espera antes da infusão não por falta de capacidade, mas por **agendamento desconectado da capacidade operacional real do momento**: técnicos de punção, enfermeiros de QT e poltronas disponíveis variam ao longo do dia conforme a escala de profissionais, e o agendamento tradicional ignora isso.

Análise de campo mostrou 63% de utilização de poltrona — 37% do tempo, a poltrona está ocupada sem infusão ativa.

---

## O que o sistema faz

- **Scheduler** que nivela chegadas com base na escala real de profissionais (técnico de punção, enfermeiro, limpeza) e na duração de cada protocolo
- **Triagem:** cadastro de walk-ins, escala do dia com vagas semafóricas, confirmação de presença D-1
- **Painel de poltronas:** rastreio em tempo real de cada etapa (punção → pré-QT → QT → retirada → higienização), log de intercorrências
- **Horizonte:** lista de retornos esperados com agendamento direto pela interface
- **Lista de agendamentos:** exportação CSV com horário de chegada sugerido, para o profissional do agendamento contatar os pacientes
- **Relatório de fim de dia:** parâmetros operacionais com campo de observação acumulável (base de calibração do algoritmo)
- **Auditoria:** log de todas as ações de escrita com usuário e horário

---

## Stack

- Python 3.13 + uv
- FastAPI + Jinja2 + SQLite
- Sem dependência de nuvem ou banco externo — roda inteiramente na rede local do hospital

---

## Instalação

Veja [`docs/instalacao.md`](docs/instalacao.md) para o guia completo.

Resumo:

```bash
git clone https://github.com/pedro-gomes-sampaio/cacon-scheduler.git
cd cacon-scheduler
cp config.example.py config.py   # edite a senha e o secret
uv sync
uv run uvicorn app:app --host 0.0.0.0 --port 8001
```

---

## Guia de uso

Veja [`docs/uso.md`](docs/uso.md) para o guia dos operadores (triagem, painel, horizonte, relatório).

---

## LGPD

O sistema processa dados de saúde (dado sensível, Art. 11 LGPD). Veja [`docs/lgpd.md`](docs/lgpd.md) para as obrigações do hospital (controlador) e do desenvolvedor (operador), medidas técnicas implementadas e retenção de dados.

---

## Adaptação ao seu centro

O sistema foi projetado para ser parametrizável sem mexer na lógica principal.

### 1. Escala de profissionais

Edite o bloco `# 2. ESCALA DE PROFISSIONAIS` em `scheduler.py`. A capacidade do dia é derivada automaticamente da escala que você definir — não há número mágico fixo.

### 2. Número de poltronas

Ajuste `N_POLTRONAS` no topo de `scheduler.py` e o segmento por número em `app.py` (`SEGMENTO`).

### 3. Parâmetros operacionais

Todos os tempos e taxas estão no bloco `# 1. ESTIMATIVAS CALIBRÁVEIS` de `scheduler.py`. Valores iniciais conservadores; calibre com os dados reais do seu centro após 2–4 semanas de uso.

O parâmetro que mais move o teto do dia é `PUNCOES_POR_TECNICO_HORA`. Compare o teto calculado com o realizado no `/relatorio` e ajuste.

---

## Estrutura

```
app.py          rotas FastAPI
scheduler.py    algoritmo de alocação por recursos
database.py     SQLite (schema + queries)
backup.py       backup com rotação de 30 dias
config.py       credenciais (não commitado — copie de config.example.py)
docs/
  instalacao.md             guia de instalação
  uso.md                    guia de uso para operadores
  lgpd.md                   obrigações LGPD
  migrar-postgres.md        migração opcional para PostgreSQL
  modelagem-problema.md     decisões algorítmicas e próximos passos
  mapeamento-protocolos-cor.md   lookup de protocolos → cor/duração
  mapeamento-premed-duracao.md   lookup de pré-medicação → tempo
  estado-da-arte-scheduling.md   referências acadêmicas sobre o problema
templates/      HTML das telas (Jinja2)
seed.py         dados de demonstração para testar o sistema
```

---

## Limitações conhecidas

Este é um MVP operacional, não um sistema otimizado. Algumas decisões foram tomadas conscientemente:

- O scheduler usa heurística (Heijunka + DBR), não otimização inteira. Próximo passo algorítmico depois de calibrado: CP-SAT (OR-Tools) — ver `docs/modelagem-problema.md`
- Não há importação em massa de pacientes — o cadastro inicial é manual
- O login é simples (senha compartilhada), adequado para o fluxo do setor; não substitui controle de acesso institucional
- SQLite é suficiente para o volume de um centro ambulatorial típico; migração para PostgreSQL está documentada em `docs/migrar-postgres.md`

---

## Contexto

Desenvolvido por Pedro Gomes Sampaio (estudante de Enfermagem) em setembro de 2026. O problema foi validado em simulação presencial com a equipe do setor antes da entrega.

Contribuições são bem-vindas.
