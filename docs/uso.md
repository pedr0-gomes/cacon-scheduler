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
| Configuração | `/configuracao` | Farmacêutica / coordenação | Implantação e quando a equipe ou os parâmetros mudam |
| Auditoria | `/auditoria` | Uso restrito (login) | Quando necessário |

---

## Login

Somente as telas de triagem exigem login (`/`, `/confirmacao`, `/horizonte`, `/relatorio`, `/configuracao`, `/auditoria`).

O painel de poltronas (`/painel`) **não exige login** — foi uma decisão deliberada para não criar atrito no tablet compartilhado do salão.

Use a senha definida em `config.py` (`SENHA_TRIAGEM`).

---

## Fluxo diário — enfermeiro de triagem

### Tarde do dia anterior: confirmar presença (D-1)

1. Acesse `/confirmacao`
2. A lista mostra todos os pacientes agendados para amanhã, com o horário marcado na Triagem
3. Contate cada paciente e marque **Confirmado** ou **Não confirmou**
4. Quem não confirmou fica marcado; a equipe decide o que fazer com o horário e a poltrona dele

### Alocar os pacientes: horário e poltrona

**Quem decide o horário e a poltrona é a equipe.** O sistema não sugere, não limita horário e não tem teto de pacientes por dia. Ele só guarda o que foi marcado e mede quanto tempo cada atendimento levou de verdade.

1. Acesse `/` (Triagem). Ela abre no dia de hoje; use o campo **Dia** no topo para ver e alocar qualquer outro dia (amanhã, a semana que vem…)
2. O quadro **Para alocar** lista os pacientes daquele dia que ainda não têm horário ou poltrona (por exemplo, os cadastrados em Configuração → Pacientes ou agendados pelo Horizonte). Escolha o **horário de início** e a **poltrona** e clique em **Salvar**
3. Quem já tem horário e poltrona aparece na **Escala do dia**, em ordem de horário, com o **fim previsto** (horário + tempo do protocolo do paciente). Para mudar, altere na própria linha e **Salvar**
4. Se dois pacientes ficarem na mesma poltrona em horários que se cruzam, a linha mostra **⚠ sobrepõe com…**. É só um aviso: o sistema não impede
5. **Salão agora** (só no dia de hoje) mostra cada poltrona com o paciente e a etapa. Poltrona **reservada** (amarela) é a de quem ainda não foi puncionado, com o horário marcado
6. O ✕ na linha tira o paciente daquele dia

O paciente só aparece no Painel depois de ter horário **e** poltrona.

#### Cadastrar um walk-in

Clique em **+ Walk-in** e preencha:

| Campo | Obrigatório | Notas |
|---|---|---|
| Nome do paciente | Sim | |
| Protocolo | Sim | Escolha da lista ou "Outro protocolo..." para protocolo fora da lista. Os tempos de pré-QT e QT viram o **previsto** do relatório |
| Horário de início e poltrona | Não | Se ficarem vazios, o paciente vai para **Para alocar** |
| Total de ciclos | Recomendado | Usado para saber quando o tratamento termina |
| Ciclos já feitos | Se já estava em tratamento | Só vale para paciente novo no sistema; sem ele a contagem começa do zero. Para quem já tem cadastro, corrija em Configuração → Pacientes → Editar |
| Número de prontuário | Recomendado | |
| Telefone | Recomendado | |
| Nome da mãe + data de nascimento | Recomendado | Dois identificadores para segurança da identificação |
| Convênio / Ordem médica | Se aplicável | Só registro — não muda horário nem poltrona |

O walk-in entra no dia que está aberto na Triagem.

**Protocolo fora da lista:** selecione "Outro protocolo...", informe o nome, a cor de duração (verde/azul/amarelo/vermelho) e o bucket de pré-medicação (A/B/C/Z). Esses valores dão o tempo previsto.

### Agendar retornos (horizonte)

Após a sessão de um paciente ser concluída no painel, acesse `/horizonte` para agendar a próxima:

1. O horizonte mostra todos os pacientes com retorno esperado nos próximos 30 dias (ajustável)
2. Pacientes com badge **Aguardando** ainda não têm próxima sessão agendada
3. Clique em **Agendar** → ajuste a data se necessário → confirme
4. A sessão é criada na data escolhida, sem verificação de vaga. Depois, aloque horário e poltrona na Triagem (no dia da sessão, ela aparece em **Para alocar**)

---

## Fluxo diário — equipe do salão (painel)

1. Acesse `/painel` em qualquer navegador na rede local
2. O painel mostra todas as poltronas (quantidade definida em Configuração → Parâmetros) com status em tempo real por cor:
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

Quando o paciente recebe a retirada, o modal mostra o botão **Agendar próxima**. Informe o intervalo em dias; a data aparece pré-preenchida e pode ser mudada — vale a data que ficar no campo. O enfermeiro de triagem também pode fazer isso pelo `/horizonte`. O horário e a poltrona da próxima sessão se marcam na Triagem.

---

## Lista de agendamentos — profissional do agendamento

Acesse `/lista` para ver os pacientes agendados nos próximos 7 dias (padrão) com o horário marcado na Triagem ("—" = ainda sem horário).

- **`/lista.csv`** exporta a lista em planilha para ligar e confirmar

O horário da lista é exatamente o marcado na Triagem — se o paciente precisa chegar antes por causa da recepção, isso é combinado por quem liga.

---

## Relatório de fim de dia

Acesse `/relatorio` ao final do expediente.

O relatório mostra:
- Total de pacientes no dia, agendados vs. walk-ins, concluídos
- **Atendimentos do dia: previsto × real** — uma linha por paciente (explicação abaixo)
- **Tempos por protocolo: planejado × real** — a mediana de todo o histórico, por protocolo
- Parâmetros operacionais atuais com campo de observação por parâmetro
- Intercorrências do dia

**Previsto × real, paciente a paciente.** O previsto é o horário marcado na Triagem e os tempos do protocolo do paciente. O real é o que a equipe registrou no painel:

| Coluna | Previsto | Real |
|---|---|---|
| Início | horário marcado na Triagem | hora da punção (a diferença é o **atraso**) |
| Pré-QT | tempo de pré-QT do protocolo | do registro de pré-QT até o de QT |
| QT | tempo de QT do protocolo | do registro de QT até o de retirada |
| Total na poltrona | pré-QT + intervalo + QT | da punção até a retirada |

Diferença **positiva (vermelha)** = demorou mais que o previsto; negativa (verde) = terminou antes. Exemplo: total previsto 4h00, real 5h00, **+60**; na mesma linha, pré-QT **+30** mostra quanto desse atraso veio da pré-QT. Para a linha ficar completa, registre **punção, pré-QT, QT e retirada** no painel; etapa sem registro aparece como "—".

**Como usar o campo de observação:** se o tempo real de punção foi diferente do parâmetro padrão, registre. Esses registros acumulam o histórico de calibração.

**Exportar:** `/relatorio/csv` gera um arquivo para arquivamento.

---

## Dicas operacionais

**O sistema não limita.** Não há teto de pacientes por dia, vaga de walk-in nem horário proibido. Quem organiza o salão é a equipe; o sistema registra e mede.

**Tempos planejados × reais por protocolo.** A tabela *Tempos por protocolo* do relatório junta todo o histórico: para cada protocolo, o pré-QT e o QT planejados ao lado da mediana do que foi registrado, com o número de sessões. Com menos de 5 sessões, trate como indício. Quando os números se firmarem, ajuste o tempo em Configuração → Parâmetros ou no cadastro do paciente — assim o **previsto** fica mais perto do real.

**Paciente não confirmou mas apareceu.** Cadastre como walk-in normalmente. O sistema trata como entrada do dia.

**Protocolo novo não está na lista.** Use "Outro protocolo..." no modal. Informe a duração estimada da QT para o previsto do relatório fazer sentido. Para entrar na lista fixa, o protocolo precisa ser adicionado em `scheduler.py` (`PROTOCOLO`) e `app.py` (`PROTOCOLO_LABEL`).

---

## Configuração — farmacêutica / coordenação

Acesse **Configuração** no menu. Cada aba tem as instruções na própria tela.

### Pacientes — carga inicial

Para cadastrar os pacientes que já estão em tratamento, a partir das fichas:

1. Preencha nome, protocolo e **data da próxima sessão** (obrigatórios)
2. Em **Ciclos já feitos**, informe quantas sessões o paciente já fez antes do sistema (cada ida à poltrona conta 1) e o **total prescrito** — é o que permite ao sistema saber quando o tratamento termina
3. **Salvar e cadastrar o próximo**

A sessão já entra como agendada: aparece na Confirmação D-1, no Horizonte e na Lista. Cadastro errado → **Editar** na lista. **Remover** só funciona enquanto o paciente não tem sessão registrada no painel.

### Escala da equipe

Registro de quem trabalha em cada dia e horário. **Não limita a Triagem** — o teto e as vagas que a tela mostra são só informativos.

- Escolha o dia da semana, ajuste horários e intervalo de cada profissional, **Salvar** na linha
- **+ Adicionar** inclui um profissional; **Remover** tira
- **Copiar** replica a escala de um dia para outros; **Restaurar escala padrão** volta ao original
- Um técnico do salão fica sempre na montagem da droga — o sistema já desconta; cadastre todos os técnicos

A tela mostra quantos técnicos, enfermeiros e higienizadores estão disponíveis em cada hora.

### Parâmetros

Número de poltronas (SUS, convênio, hematologia) — é o que aparece para escolher na Triagem — e os tempos de cada etapa, que formam o **previsto**. Os campos de capacidade (punções por técnico, % walk-in, última punção) não limitam mais nada. Valor diferente do padrão fica destacado em amarelo; **Restaurar padrões** volta tudo.

Toda alteração em Configuração fica registrada na Auditoria.

---

## Segurança e LGPD

O sistema manipula dados de saúde — dado sensível pela LGPD. Veja `docs/lgpd.md` para as obrigações do hospital e do operador (desenvolvedor).

Regras básicas:
- Não compartilhe a senha de triagem com pessoas de fora do setor
- Não acesse o sistema em redes Wi-Fi públicas
- Faça backup diário (configure o cron — ver `docs/instalacao.md §7`)
- Em caso de incidente de segurança (acesso não autorizado, perda de dados), comunique a DPO do hospital
