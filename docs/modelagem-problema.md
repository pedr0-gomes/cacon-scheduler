# Modelagem do Problema de Alocação — CACON

## Entrada (D-1)
Lista de N pacientes agendados: protocolo, duração estimada, flexibilidade, convênio/SUS/hemato.
Dia da semana (define horizonte: 6h–18h seg–qui · 6h–17h sex).

## Saída
Para cada paciente: horário de chegada + poltrona.
Walk-in: slots reservados, não pré-atribuídos.

## Capacidade real do dia
O limite diário não é o número de poltronas (34) — é a capacidade da equipe (tambor). Uma poltrona pode atender múltiplos pacientes no mesmo dia (protocolo curto de 30 min pode ocupar a mesma poltrona 4–5 vezes). O teto verdadeiro é calculado dinamicamente: soma do throughput de punção em todas as janelas do dia dado o pool_técnico(t) e T_punção estimado.

N_AGENDADO e N_WALK_IN deixam de ser constantes fixas e passam a ser calculados por dia com base na capacidade real da escala.

---

## Recursos e capacidade

| Recurso | Capacidade | Observação |
|---|---|---|
| Técnicos (salão) | pool(t) − 1 montagem | varia por janela (1 a 7) |
| Enfermeiros (salão) | pool(t) | 0 às 6h–7h; 1 às 12h–13h; 3 demais |
| Poltronas | 34 | higienização = 5 min estimados (registrada pela limpeza no sistema) |
| Montagem | 1 técnico rotativo | inicia após punção; throughput estimado |
| Lanche 9h–10h | ~metade do pool | técnicos e enfermeiros |
| Hemato 31–34 | 1 técnica exclusiva | pool separado |

---

## Restrições

1. Punções simultâneas ≤ pool_técnico(t)
2. QT simultâneas ≤ pool_enfermeiro(t)
3. Nenhuma QT pode iniciar entre 6h–7h (zero enfermeiros no salão)
4. Técnico tem segunda interação ~25 min após a punção (retirada da pré-med) — não pode estar em outra punção nesse momento
5. QT só inicia após medicamento pronto (depende do throughput da montagem)
6. Convênio → poltronas 26–30 preferencialmente
7. Flexibilidade=baixa: horário fixo; flexibilidade=alta: pode ceder se o pool estiver cheio
8. Ordem médica: prioridade absoluta, override em qualquer fila
9. Sex: pacientes longos (4h+) com chegada tardia bloqueados

---

## Objetivo
Maximizar pacientes atendidos dentro do horizonte do dia, respeitando todas as restrições.

---

## Algoritmo (Heijunka + DBR)
- Ordenação: longos primeiro, depois flexibilidade=baixa antes de alta
- Tambor: taxa de chegada = min(pool_técnico(t), pool_enfermeiro(t − 25 min))
- Atribuição de poltrona: primeira livre respeitando regra convênio
- Slot de segunda interação do técnico: reservado em t_punção + 25 min

---

## Estimativas iniciais

Todas a refinar com dados reais. O sistema registra timestamps de todos os eventos — as estimativas se refinam automaticamente com o uso.

| Parâmetro | Estimativa inicial |
|---|---|
| T_punção | 8 min |
| T_pré-medicação | 25 min |
| T_higienização | 5 min |
| T_montagem | 15 min/paciente |
| Taxa de não-confirmação D-1 | 20% |
| Taxa de reação adversa | 5–10% |
| Taxa de chegada fora do horário | a observar |
| Razão agendados / walk-in | 60/40 (20 agendados · 14 walk-in) |

---

## Princípio central
Estimar → implantar → mensurar → otimizar. Os dados coletados pelo sistema retroalimentam diretamente as estimativas acima.

---

## Próximo passo algorítmico: CP-SAT (Google OR-Tools)
O Heijunka + DBR é o algoritmo do MVP — simples, explicável, já resolve o problema principal. À medida que as restrições reais (segunda interação do técnico, dependência da montagem, dois pools simultâneos) forem incorporadas, a migração natural é para **Programação por Restrições com CP-SAT**.

Justificativa: com ~34 poltronas e capacidade dinâmica, o problema é pequeno o suficiente para ser resolvido de forma exata em segundos. CP-SAT modela todas as restrições diretamente sem aproximação e garante solução ótima — não apenas boa.

Gatilho para migrar: quando tivermos dados reais suficientes para validar as estimativas e o greedy começar a produzir conflitos nas restrições de segunda interação ou montagem.
