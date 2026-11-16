# CACON Scheduler

Sistema de gestão para **quimioterapia ambulatorial**: a equipe organiza a agenda e as poltronas, e o sistema registra cada etapa do atendimento e mede **quanto tempo cada paciente realmente levou**, comparado com o previsto.

Feito para um CACON do interior do Nordeste, em uso pela equipe do setor, e pensado para servir a qualquer centro oncológico ambulatorial. Roda na rede local do hospital, sem nuvem.

---

## Por que existe

Na quimioterapia ambulatorial, boa parte do tempo do paciente na poltrona não é infusão: é espera pela punção, pela pré-medicação, pela droga. Uma análise de campo neste setor encontrou **63% de utilização da poltrona** — em 37% do tempo ela está ocupada sem infusão. Para reduzir isso, primeiro é preciso **medir**: quanto cada etapa demora de verdade, para quais protocolos, em quais horários.

O sistema faz isso sem mudar a forma de trabalhar: **quem decide horário e poltrona é a equipe**. Não há teto de pacientes, vaga reservada nem horário proibido.

---

## As quatro telas

| Tela | Quem usa | Para quê |
|---|---|---|
| **Hoje** | Enfermeiro de triagem | Escolher a poltrona de quem vem hoje, cadastrar walk-in, ajustar horário |
| **Salão** | Técnicos e enfermeiros (tablet) | Tocar na poltrona e registrar a etapa: punção → pré-QT → QT → retirada → higienização |
| **Agenda** | Triagem / agendamento | Ver os próximos dias, marcar horário, confirmar presença, agendar quem precisa de nova data |
| **Relatório** | Farmacêutica / coordenação | Tempo de cada paciente, previsto → real, e a média por protocolo |

Mais a **⚙ Configuração** (pacientes, poltronas, tempos dos protocolos, escala e auditoria), usada na implantação e quando algo muda.

### Como um dia funciona

1. **Agenda** — dias antes, cada paciente tem data e horário. Na véspera, a equipe liga e marca a confirmação.
2. **Hoje** — no dia, quem chega aparece em *Aguardando poltrona*; a triagem escolhe a poltrona. Walk-in entra pelo botão **+ Walk-in**.
3. **Salão** — a cada etapa, o técnico ou enfermeiro toca na poltrona e registra. O horário é gravado na hora. Depois da retirada, a mesma janela agenda a próxima sessão.
4. **Relatório** — no fim do dia, o tempo de cada paciente em cada etapa, com o desvio em relação ao previsto (ex.: previsto 4h, real 5h, dos quais +30 min na pré-QT).

Guia completo para os operadores: [`docs/uso.md`](docs/uso.md).

---

## Instalação

```bash
git clone https://github.com/pedr0-gomes/cacon-scheduler.git
cd cacon-scheduler
cp config.example.py config.py   # defina a senha e o secret
uv sync
uv run uvicorn app:app --host 0.0.0.0 --port 8001
```

Acesse `http://<IP-do-servidor>:8001` de qualquer computador ou tablet da rede. O **Salão** não pede senha (tablet compartilhado); as outras telas pedem a senha do `config.py`.

Para experimentar com dados fictícios: `uv run python seed.py`.

Guia passo a passo — servidor, backup automático, serviço systemd, primeira configuração: [`docs/instalacao.md`](docs/instalacao.md).

### Atualizar

```bash
uv run python backup.py && git pull && uv sync
# depois reinicie o servidor
```

O banco é preservado; colunas novas são criadas sozinhas. Veja [`docs/instalacao.md` §11](docs/instalacao.md#11-atualizar-uma-instalação-existente) — inclui o que muda para quem usa na atualização de novembro/2026.

---

## Adaptar ao seu centro

Tudo pela tela **Configuração**, sem mexer no código:

1. **Parâmetros** — número de poltronas (SUS, convênio, hematologia) e os tempos de cada etapa, que formam o **previsto** do relatório.
2. **Pacientes** — carga inicial de quem já está em tratamento, a partir das fichas (com os ciclos já feitos e, se souber, o horário da próxima sessão).
3. **Escala da equipe** — opcional; é só registro e não limita nada.

Com algumas semanas de uso, a tabela *Média por protocolo* do Relatório mostra quanto cada protocolo leva de verdade. Ajuste os tempos em Parâmetros (ou no cadastro do paciente) para o previsto ficar perto do real.

---

## LGPD

O sistema guarda dados de saúde (dado sensível, Art. 11 da LGPD). Antes de qualquer dado real entrar, leia [`docs/lgpd.md`](docs/lgpd.md): papéis de controlador e operador, medidas técnicas já implementadas (login, auditoria, backup) e retenção.

---

## Estrutura

```
app.py          rotas e telas (FastAPI + Jinja2)
database.py     SQLite: esquema, migrações automáticas e consultas
scheduler.py    tempos por protocolo, poltronas e parâmetros; também contém o
                algoritmo de alocação automática, mantido mas não usado (ver Histórico)
backup.py       cópia do banco com rotação dos últimos 30
seed.py         dados fictícios de demonstração
config.py       senha e secret (não versionado — copie de config.example.py)
templates/      telas: agenda.html = Hoje, painel.html = Salão, lista.html = Agenda,
                relatorio.html, config_*.html = Configuração
docs/
  uso.md                         guia dos operadores
  instalacao.md                  instalação, backup, serviço, atualização
  lgpd.md                        obrigações LGPD
  migrar-postgres.md             migração opcional para PostgreSQL
  mapeamento-protocolos-cor.md   protocolos → faixa de duração da QT
  mapeamento-premed-duracao.md   pré-medicação → tempo
  modelagem-problema.md          (histórico) modelagem do scheduler automático
  estado-da-arte-scheduling.md   (pesquisa) literatura sobre agendamento de quimioterapia
```

**Stack:** Python 3.13 + uv · FastAPI + Jinja2 · SQLite.

---

## Limitações conhecidas

- Login simples, com senha compartilhada — adequado ao fluxo do setor, não substitui controle de acesso institucional.
- Não há importação de planilha: a carga inicial é digitada em Configuração → Pacientes.
- Rode com **um único processo** (sem `--workers`): parâmetros ficam em memória e são recarregados do banco a cada alteração.
- SQLite basta para o volume de um centro ambulatorial; a migração para PostgreSQL está em [`docs/migrar-postgres.md`](docs/migrar-postgres.md).

---

## Histórico

- **Setembro/2026** — primeira versão, com um **scheduler automático** que montava o dia a partir da escala da equipe (heurística Heijunka + DBR; modelagem em `docs/modelagem-problema.md`). Validado em simulação presencial com a equipe.
- **Novembro/2026** — com o sistema em uso real, a equipe precisou de liberdade para escolher horário e poltrona; o algoritmo impunha o dia e travava a operação. O sistema passou a ser de **gestão e medição**: a equipe decide, o sistema registra e mede. O algoritmo continua em `scheduler.py`, desligado das telas — pode voltar como sugestão quando houver dados reais suficientes para calibrá-lo.

A lição ficou registrada: primeiro registrar e medir; otimizar só depois, com dados.

Desenvolvido por Pedro Gomes Sampaio (Ciência da Computação). Contribuições são bem-vindas.
