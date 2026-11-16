# Guia de uso — CACON

Este documento é para os operadores do sistema. Público: enfermeiro de triagem, farmacêutica, profissional do agendamento, técnicos de enfermagem.

---

## As quatro telas do dia a dia

O menu tem só o que se usa todo dia:

| Botão | Endereço | Quem usa | Para quê |
|---|---|---|---|
| **Hoje** | `/` | Enfermeiro de triagem | Dar a poltrona a quem vem hoje, cadastrar walk-in, ajustar horário |
| **Salão** | `/painel` | Técnicos e enfermeiros do salão | Registrar as etapas de cada paciente |
| **Agenda** | `/lista` | Triagem / agendamento | Ver os próximos dias, marcar horário, confirmar presença, agendar quem está esperando |
| **Relatório** | `/relatorio` | Farmacêutica / coordenação | Previsto × real, no fim do expediente |

À direita ficam **⚙ Configuração** (pacientes, escala, parâmetros e auditoria; usada na implantação e quando algo muda) e **Sair**.

**Quem decide é a equipe.** O sistema não sugere, não limita horário e não tem teto de pacientes por dia. Ele guarda o que foi marcado e mede quanto tempo cada atendimento levou de verdade. **Data e horário** se marcam na **Agenda**; **a poltrona** se dá **no dia**, em **Hoje**.

---

## Login

O Salão (`/painel`) **não exige login** — decisão deliberada para não criar atrito no tablet compartilhado. As outras telas pedem a senha definida em `config.py` (`SENHA_TRIAGEM`).

---

## Agenda — os próximos dias

Um bloco por dia (7, 14 ou 30 dias), com os pacientes em ordem de horário.

- **Horário:** defina ou mude na própria linha e clique em **Salvar**. Quem ainda não tem horário aparece com "—" no fim do dia, e o cabeçalho avisa quantos são
- **Por hora:** o cabeçalho de cada dia mostra quantos pacientes começam em cada hora (ex.: "07h · 9"). É só para enxergar o dia e não empilhar todo mundo no mesmo horário: o sistema não limita
- **Confirmação:** depois de ligar para o paciente, marque **✓ Confirmou** ou **✕ Não**. O selo fica na linha; **desfazer** volta para pendente. Vale para qualquer dia — o costume é confirmar os de amanhã na tarde anterior
- **Esperando agendamento** (quadro amarelo no topo, só aparece quando há alguém): pacientes em tratamento sem a próxima sessão marcada. A data esperada já vem preenchida pelo intervalo do protocolo; ajuste se precisar, informe o horário e clique em **Agendar**. Não há verificação de vaga
- **+ Agendar paciente novo:** leva a Configuração → Pacientes, para cadastrar alguém que vem num dia futuro (quem chega hoje é walk-in, em Hoje)
- **Baixar planilha** (`/lista.csv`) exporta a lista para ligar e confirmar

O horário é o que foi marcado. Se o paciente precisa chegar antes por causa da recepção, isso é combinado por quem liga.

---

## Hoje — o dia de hoje

1. O quadro **Para alocar** lista os pacientes de hoje ainda sem poltrona (ou sem horário). O horário agendado já vem preenchido: confira, escolha a **poltrona** e clique em **Salvar**
2. Quem já tem horário e poltrona aparece na **Escala do dia**, em ordem de horário, com o **fim previsto** (horário + tempo do protocolo do paciente). Se alguém atrasar ou trocar de lugar, altere na própria linha e **Salvar**
3. Se dois pacientes ficarem na mesma poltrona em horários que se cruzam, a linha mostra **⚠ sobrepõe com…**. É só um aviso: o sistema não impede
4. **Salão agora** mostra cada poltrona com o paciente e a etapa. Poltrona **reservada** (amarela) é a de quem ainda não foi puncionado, com o horário marcado
5. O ✕ na linha tira o paciente do dia

O paciente só aparece no Salão depois de ter horário **e** poltrona.

#### Cadastrar um walk-in

Clique em **+ Walk-in** e preencha:

| Campo | Obrigatório | Notas |
|---|---|---|
| Nome do paciente | Sim | |
| Protocolo | Sim | Escolha da lista ou "Outro protocolo..." para protocolo fora da lista. Os tempos de pré-QT e QT viram o **previsto** do relatório |
| Horário de início e poltrona | Não | Se ficarem vazios, o paciente vai para **Para alocar**, em Hoje |
| Total de ciclos | Recomendado | Usado para saber quando o tratamento termina |
| Ciclos já feitos | Se já estava em tratamento | Só vale para paciente novo no sistema; sem ele a contagem começa do zero. Para quem já tem cadastro, corrija em Configuração → Pacientes → Editar |
| Número de prontuário | Recomendado | |
| Telefone | Recomendado | |
| Nome da mãe + data de nascimento | Recomendado | Dois identificadores para segurança da identificação |
| Convênio / Ordem médica | Se aplicável | Só registro — não muda horário nem poltrona |

O walk-in entra no dia de hoje.

**Protocolo fora da lista:** selecione "Outro protocolo...", informe o nome, a cor de duração (verde/azul/amarelo/vermelho) e o bucket de pré-medicação (A/B/C/Z). Esses valores dão o tempo previsto.

---

## Salão — registrar as etapas

1. Acesse `/painel` (botão **Salão**) em qualquer navegador na rede local
2. A tela mostra todas as poltronas (quantidade definida em Configuração → Parâmetros) com status em tempo real por cor:
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

### Agendar a próxima sessão

Quando o paciente recebe a retirada, a janela da poltrona mostra **Agendar próxima**. Informe o intervalo em dias; a data aparece preenchida e pode ser mudada — vale a data que ficar no campo. Há também o campo **Horário**; se ficar vazio, defina depois na Agenda. Quem não for agendado aqui aparece em **Esperando agendamento**, na Agenda.

---

## Relatório de fim de dia

Acesse `/relatorio` ao final do expediente.

O relatório mostra:
- Total de pacientes no dia, agendados vs. walk-ins, concluídos
- **Atendimentos do dia: previsto × real** — uma linha por paciente (explicação abaixo)
- **Tempos por protocolo: planejado × real** — a mediana de todo o histórico, por protocolo
- Parâmetros operacionais atuais com campo de observação por parâmetro
- Intercorrências do dia

**Previsto × real, paciente a paciente.** O previsto é o horário agendado e os tempos do protocolo do paciente. O real é o que a equipe registrou no painel:

| Coluna | Previsto | Real |
|---|---|---|
| Início | horário agendado | hora da punção (a diferença é o **atraso**) |
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

1. Preencha nome, protocolo e **data da próxima sessão** (obrigatórios) e, se já souber, o **horário** (dá para definir depois na Lista)
2. Em **Ciclos já feitos**, informe quantas sessões o paciente já fez antes do sistema (cada ida à poltrona conta 1) e o **total prescrito** — é o que permite ao sistema saber quando o tratamento termina
3. **Salvar e cadastrar o próximo**

A sessão já entra como agendada e aparece na Agenda. Cadastro errado → **Editar** na lista. **Remover** só funciona enquanto o paciente não tem sessão registrada no painel.

### Escala da equipe

Registro de quem trabalha em cada dia e horário. **Não limita nada** — o teto e as vagas que a tela mostra são só informativos.

- Escolha o dia da semana, ajuste horários e intervalo de cada profissional, **Salvar** na linha
- **+ Adicionar** inclui um profissional; **Remover** tira
- **Copiar** replica a escala de um dia para outros; **Restaurar escala padrão** volta ao original
- Um técnico do salão fica sempre na montagem da droga — o sistema já desconta; cadastre todos os técnicos

A tela mostra quantos técnicos, enfermeiros e higienizadores estão disponíveis em cada hora.

### Parâmetros

Número de poltronas (SUS, convênio, hematologia) — é o que aparece para escolher em Hoje — e os tempos de cada etapa, que formam o **previsto**. Os campos de capacidade (punções por técnico, % walk-in, última punção) não limitam mais nada. Valor diferente do padrão fica destacado em amarelo; **Restaurar padrões** volta tudo.

Toda alteração em Configuração fica registrada na Auditoria.

---

## Segurança e LGPD

O sistema manipula dados de saúde — dado sensível pela LGPD. Veja `docs/lgpd.md` para as obrigações do hospital e do operador (desenvolvedor).

Regras básicas:
- Não compartilhe a senha de triagem com pessoas de fora do setor
- Não acesse o sistema em redes Wi-Fi públicas
- Faça backup diário (configure o cron — ver `docs/instalacao.md §7`)
- Em caso de incidente de segurança (acesso não autorizado, perda de dados), comunique a DPO do hospital
