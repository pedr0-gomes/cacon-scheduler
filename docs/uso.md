# Guia de uso — CACON

Este documento é para os operadores do sistema. Público: enfermeiro de triagem, farmacêutica, profissional do agendamento, técnicos de enfermagem.

---

## Visão geral das telas

| Tela | Endereço | Quem usa | Quando |
|---|---|---|---|
| Triagem | `/` | Enfermeiro de triagem | Todo dia, durante o turno |
| Painel de poltronas | `/painel` | Técnicos e enfermeiros do salão | Durante a infusão |
| Confirmação D-1 | `/confirmacao` | Enfermeiro de triagem | Tarde do dia anterior |
| Horizonte | `/horizonte` | Enfermeiro de triagem | Agendamento de retornos |
| Lista de agendamentos | `/lista` | Profissional do agendamento | Para contato com pacientes |
| Relatório de fim de dia | `/relatorio` | Farmacêutica / coordenação | Final do expediente |
| Auditoria | `/auditoria` | Uso restrito (login) | Quando necessário |

---

## Login

Somente as telas de triagem exigem login (`/`, `/confirmacao`, `/horizonte`, `/relatorio`, `/auditoria`).

O painel de poltronas (`/painel`) **não exige login** — foi uma decisão deliberada para não criar atrito no tablet compartilhado do salão.

Use a senha definida em `config.py` (`SENHA_TRIAGEM`).

---

## Fluxo diário — enfermeiro de triagem

### Tarde do dia anterior: confirmar presença (D-1)

1. Acesse `/confirmacao`
2. A lista mostra todos os pacientes agendados para amanhã com o horário sugerido de chegada
3. Contate cada paciente e marque **Confirmado** ou **Não confirmou**
4. Pacientes que não confirmam liberam a vaga para walk-in no dia seguinte

### Manhã: gerenciar walk-ins e acompanhar o dia

1. Acesse `/` (Triagem)
2. A tela mostra a escala do dia: vagas disponíveis por janela de horário e total de walk-ins ainda possíveis
3. Quando chegar um paciente walk-in ou uma ordem médica: clique em **+ Walk-in**

#### Cadastrar um walk-in

No modal, preencha:

| Campo | Obrigatório | Notas |
|---|---|---|
| Nome do paciente | Sim | |
| Protocolo | Sim | Escolha da lista ou "Outro protocolo..." para protocolo fora da lista |
| Data da sessão | Sim | Trava em hoje para walk-in |
| Total de ciclos | Recomendado | Necessário para o agendamento automático de retorno |
| Número de prontuário | Recomendado | |
| Telefone | Recomendado | |
| Nome da mãe + data de nascimento | Recomendado | Dois identificadores para segurança da identificação |
| Convênio | Se aplicável | Reserva poltrona 26–30 |
| Ordem médica | Se aplicável | Prioridade máxima no scheduler |
| Flexibilidade | Padrão: Alta | "Baixa" = paciente com restrição de horário |

**Protocolo fora da lista:** selecione "Outro protocolo...", informe o nome, a cor de duração (verde/azul/amarelo/vermelho) e o bucket de pré-medicação (A/B/C/Z). O scheduler aloca com base nesses parâmetros.

### Agendar retornos (horizonte)

Após a sessão de um paciente ser concluída no painel, acesse `/horizonte` para agendar a próxima:

1. O horizonte mostra todos os pacientes com retorno esperado nos próximos 30 dias (ajustável)
2. Pacientes com badge **Aguardando** ainda não têm próxima sessão agendada
3. Clique em **Agendar** → ajuste a data se necessário → confirme
4. O sistema verifica automaticamente a disponibilidade de vagas antes de confirmar

---

## Fluxo diário — equipe do salão (painel)

1. Acesse `/painel` em qualquer navegador na rede local
2. O painel mostra as 34 poltronas com status em tempo real por cor:
   - **Cinza** — livre
   - **Amarelo** — aguardando punção
   - **Laranja** — pré-QT em andamento
   - **Azul** — QT em andamento
   - **Roxo** — aguardando retirada
   - **Verde** — aguardando higienização

### Registrar uma etapa

1. Clique na poltrona do paciente
2. Clique no botão da etapa concluída (Punção, Pré-QT, QT, Retirada, Higienização)
3. O horário é registrado automaticamente

### Desfazer um evento

No modal da poltrona, clique em **↩** ao lado do evento para remover o registro. Use quando houver erro de toque.

### Registrar intercorrência

No modal da poltrona, há um campo de texto livre para anotar intercorrências (reação adversa, troca de poltrona, etc.). Essas notas aparecem no relatório de fim de dia.

### Agendar próxima sessão pelo painel

Quando o paciente recebe a retirada, o modal mostra o botão **Agendar próxima**. Informe o intervalo em dias e a data sugerida aparece pré-preenchida. O enfermeiro de triagem também pode fazer isso pelo `/horizonte`.

---

## Lista de agendamentos — profissional do agendamento

Acesse `/lista` para ver os pacientes agendados nos próximos 7 dias (padrão) com o horário de chegada sugerido pelo sistema.

- **`/lista.csv`** exporta a lista em planilha para ligar e confirmar

O horário informado ao paciente já desconta o tempo de espera (recepção, cadastro) — o scheduler calcula a punção no horário ótimo e informa ao paciente 2h antes.

---

## Relatório de fim de dia

Acesse `/relatorio` ao final do expediente.

O relatório mostra:
- Total de pacientes no dia, agendados vs. walk-ins, concluídos
- Capacidade calculada pelo scheduler (teto, pool agendado, pool walk-in)
- Parâmetros operacionais atuais com campo de observação por parâmetro
- Intercorrências do dia

**Como usar o campo de observação:** se o tempo real de punção foi diferente do parâmetro padrão, registre. Esses registros acumulam o histórico de calibração.

**Exportar:** `/relatorio/csv` gera um arquivo para arquivamento.

---

## Dicas operacionais

**O scheduler não é uma ordem.** Os horários sugeridos são pontos de partida; a equipe continua decidindo na prática. O valor do sistema está no nivelamento do fluxo ao longo do dia, não em controlar cada detalhe.

**Calibração ao longo do tempo.** Após 2–4 semanas de uso, compare o teto calculado com o total realizado no relatório. Se o teto calculado estiver muito acima do real, o parâmetro `PUNCOES_POR_TECNICO_HORA` em `scheduler.py` precisa ser reduzido — chame o desenvolvedor.

**Walk-in esgotou as vagas.** Se o pool walk-in estiver cheio e chegar um paciente com ordem médica, o sistema permite o cadastro e o scheduler move o agendado com `flexibilidade = alta` para acomodar.

**Paciente não confirmou mas apareceu.** Cadastre como walk-in normalmente. O sistema trata como entrada do dia.

**Protocolo novo não está na lista.** Use "Outro protocolo..." no modal. Informe a duração estimada da QT em minutos para o scheduler alocar corretamente. Avise o desenvolvedor para adicionar o protocolo à lista fixa.

---

## Segurança e LGPD

O sistema manipula dados de saúde — dado sensível pela LGPD. Veja `docs/lgpd.md` para as obrigações do hospital e do operador (desenvolvedor).

Regras básicas:
- Não compartilhe a senha de triagem com pessoas de fora do setor
- Não acesse o sistema em redes Wi-Fi públicas
- Faça backup diário (configure o cron — ver `docs/instalacao.md §7`)
- Em caso de incidente de segurança (acesso não autorizado, perda de dados), comunique a DPO do hospital
