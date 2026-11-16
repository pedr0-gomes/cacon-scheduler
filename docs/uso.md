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

- **Horário:** é o primeiro campo da linha. Mude o horário e aparece o botão **Salvar**. Quem ainda não tem horário fica com o campo em amarelo, e o cabeçalho do dia avisa quantos são
- **Por hora:** o cabeçalho de cada dia mostra quantos pacientes começam em cada hora (ex.: "07h: 9"). É só para enxergar o dia e não empilhar todo mundo no mesmo horário: o sistema não limita
- **Confirmação:** depois de ligar para o paciente, clique em **✓ Confirmou** ou **✕ Não confirmou**. O selo fica na linha; **desfazer** volta para pendente. Vale para qualquer dia — o costume é confirmar os de amanhã na tarde anterior
- **Precisam de nova data** (quadro amarelo no topo, só aparece quando há alguém): quem já fez a última sessão e não tem a próxima marcada. A data sugerida segue o intervalo do protocolo; ajuste se precisar, informe o horário e clique em **Agendar**. Não há verificação de vaga
- **+ Agendar paciente novo:** leva a Configuração → Pacientes, para cadastrar alguém que vem num dia futuro (quem chega hoje é walk-in, em Hoje)
- **Baixar planilha** exporta a lista para ligar e confirmar

O horário é o que foi marcado. Se o paciente precisa chegar antes por causa da recepção, isso é combinado por quem liga.

---

## Hoje — o dia de hoje

1. **Dar poltrona** (quadro amarelo, só aparece quando há alguém): pacientes de hoje que ainda não têm poltrona. Confira o horário, escolha a poltrona e clique em **Salvar**
2. **Pacientes do dia:** quem já tem poltrona, em ordem de horário, com a **situação** e o horário em que deve terminar. Para mudar horário ou poltrona, clique em **Alterar**; na mesma janela há **Tirar da lista de hoje** para quem não veio
3. Se dois pacientes ficarem na mesma poltrona em horários que se cruzam, aparece **⚠ mesma poltrona que…**. É só um aviso: o sistema não impede
4. **Poltronas agora** mostra cada poltrona com o paciente e a situação — ajuda a escolher uma poltrona livre

**Situação** (as mesmas palavras aparecem no Salão): Aguardando punção → Puncionado → Em pré-QT → Em QT → Limpar poltrona → Concluído.

O paciente só aparece no Salão depois de ter horário **e** poltrona.

#### Cadastrar um walk-in

Clique em **+ Walk-in**. Nome e protocolo são obrigatórios; horário, poltrona, prontuário e telefone ficam à vista; o resto está em **Mais dados (opcional)**:

| Campo | Obrigatório | Notas |
|---|---|---|
| Nome do paciente | Sim | |
| Protocolo | Sim | Escolha da lista ou "Outro protocolo..." para protocolo fora da lista. Os tempos de pré-QT e QT viram o **previsto** do relatório |
| Horário e poltrona | Não | Se ficarem vazios, o paciente vai para **Dar poltrona** |
| Total de ciclos | Recomendado | Usado para saber quando o tratamento termina |
| Ciclos já feitos | Se já estava em tratamento | Só vale para paciente novo no sistema; sem ele a contagem começa do zero. Para quem já tem cadastro, corrija em Configuração → Pacientes → Editar |
| Número de prontuário | Recomendado | |
| Telefone | Recomendado | |
| Nome da mãe + data de nascimento | Recomendado | Dois identificadores para segurança da identificação |
| Convênio / Ordem médica | Se aplicável | Só registro — não muda horário nem poltrona |

O walk-in entra no dia de hoje.

**Protocolo fora da lista:** escolha "Outro protocolo (digitar)", informe o nome e a duração aproximada; em **Mais dados** ajuste a pré-QT e os minutos de QT. Esses valores dão o tempo previsto.

---

## Salão — registrar as etapas

1. Botão **Salão** (`/painel`), em qualquer navegador da rede local — não pede senha. Todas as poltronas cabem na tela
2. Cada poltrona mostra o número, o primeiro nome e a situação (ou "chega 07:45" para quem ainda não foi puncionado). A barra embaixo é o tempo já passado em relação ao previsto
3. **Toque na poltrona** e use o botão grande para registrar a próxima etapa (Punção, Pré-QT, QT, Retirada, Higienização). O horário é registrado na hora
4. Errou o toque? Na mesma janela, clique em **desfazer** ao lado da etapa
5. **Intercorrência:** escreva no campo da janela e clique em **Salvar anotação**. Aparece no Relatório
6. **Agendar a próxima sessão:** depois da retirada, a janela mostra data (já sugerida) e horário. Quem não for agendado aqui aparece em **Precisam de nova data**, na Agenda

---

## Relatório

Escolha o dia no topo (abre no dia de hoje).

**Tempo de cada paciente.** Para cada etapa aparece *previsto → real*, e embaixo a diferença: **vermelho** = demorou mais, **verde** = terminou antes, cinza = no tempo.

| Coluna | Previsto | Real |
|---|---|---|
| Chegada | horário marcado | hora da punção (diferença = atraso) |
| Pré-QT | tempo de pré-QT do protocolo | do registro de pré-QT até o de QT |
| QT | tempo de QT do protocolo | do registro de QT até o de retirada |
| Total na poltrona | pré-QT + intervalo + QT | da punção até a retirada |

Exemplo: total 4h00 → 5h00, **+60 min**; na mesma linha, pré-QT **+30 min** mostra quanto desse atraso veio da pré-QT. Etapa sem registro no Salão aparece como "não registrado".

**Média por protocolo (todos os dias).** Quanto cada protocolo costuma levar de verdade. Com poucas sessões ainda não é confiável. Quando os números se firmarem, ajuste os tempos em Configuração → Parâmetros ou no cadastro do paciente — assim o previsto fica mais perto do real.

**Baixar planilha** gera o mesmo conteúdo em planilha, para arquivar.

---

## Dicas operacionais

**O sistema não limita.** Não há teto de pacientes por dia, vaga de walk-in nem horário proibido. Quem organiza o salão é a equipe; o sistema registra e mede.

**Paciente não confirmou mas apareceu.** Ele continua na lista do dia: é só dar a poltrona em Hoje. A confirmação não tira ninguém da lista.

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
