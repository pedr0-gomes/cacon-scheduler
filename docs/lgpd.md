# LGPD — Proteção de dados no CACON

Este documento descreve as obrigações legais envolvidas na operação do sistema. Público: hospital (controlador), desenvolvedor/mantenedor (operador), DPO.

---

## Enquadramento legal

O sistema processa **dados de saúde** (Art. 5º, II e Art. 11 LGPD — Lei 13.709/2018), que são dados pessoais sensíveis. O tratamento exige:

- Base legal: Art. 11, II, "f" — tutela da saúde, exclusivamente por profissionais de saúde, serviços de saúde ou autoridade sanitária
- Finalidade: gestão operacional do setor de quimioterapia ambulatorial

---

## Papéis

| Papel | Quem | Obrigação |
|---|---|---|
| Controlador | Hospital (CACON) | Define finalidade e meios do tratamento; responsável perante o titular |
| Operador | Desenvolvedor (Pedro Gomes Sampaio) | Processa dados segundo instruções do controlador; Art. 39 LGPD |

O contrato entre controlador e operador deve ser formalizado antes de qualquer dado real entrar no sistema.

---

## Dados coletados

| Dado | Categoria | Necessidade |
|---|---|---|
| Nome completo | Pessoal | Identificação do paciente |
| Nome da mãe | Pessoal | Segundo identificador (ANVISA RDC 220/2004) |
| Data de nascimento | Pessoal | Segundo identificador |
| Número de prontuário | Pessoal | Vínculo com o registro físico |
| Telefone | Pessoal | Contato para confirmação de presença |
| Protocolo quimioterápico | Saúde (sensível) | Base do agendamento |
| Número de ciclos | Saúde (sensível) | Controle de tratamento |
| Eventos de sessão (punção, QT, retirada) com horário | Saúde (sensível) | Registro clínico operacional |
| Intercorrências livres | Saúde (sensível) | Anotações da equipe |

---

## Medidas técnicas implementadas

- **Banco local:** SQLite no servidor do hospital — dados nunca saem da rede local
- **Autenticação:** login com senha para as rotas de triagem; painel sem login (tablet compartilhado, decisão de usabilidade)
- **Log de auditoria:** todas as ações de escrita são registradas com usuário (`triagem` ou `painel`), agendamento e horário — acessível em `/auditoria`
- **Backup com rotação:** `backup.py` mantém 30 cópias; backups devem ficar no mesmo servidor ou em mídia controlada pelo hospital

---

## Medidas organizacionais necessárias (hospital)

- [ ] **RIPD** (Relatório de Impacto à Proteção de Dados Pessoais) — Art. 38 LGPD; obrigatório para tratamento de dados sensíveis
- [ ] **Contrato de operador** — formalizar relação com o desenvolvedor antes de dados reais entrarem
- [ ] **Indicação de DPO** — Art. 41 LGPD (se aplicável ao porte do hospital)
- [ ] **Treinamento da equipe** — todos os operadores do sistema devem saber o que não fazer com os dados (não fotografar tela, não compartilhar fora da rede, etc.)
- [ ] **Procedimento de resposta a incidentes** — o que fazer em caso de acesso não autorizado ou perda de dados; notificar ANPD em até 2 dias úteis se risco relevante (Art. 48 LGPD)

---

## Retenção e descarte

O sistema não tem exclusão automática de dados. O hospital deve definir:

- Por quanto tempo os dados operacionais são mantidos (recomendação: alinhar com política de prontuário físico — mínimo 20 anos, CFM 1821/2007)
- Procedimento de anonimização ou exclusão ao desativar o sistema

Para remover um paciente manualmente:

```sql
-- Conecte ao banco com sqlite3 cacon.db
DELETE FROM eventos WHERE agendamento_id IN (SELECT id FROM agendamentos WHERE paciente_id = ?);
DELETE FROM intercorrencias WHERE agendamento_id IN (SELECT id FROM agendamentos WHERE paciente_id = ?);
DELETE FROM agendamentos WHERE paciente_id = ?;
DELETE FROM pacientes WHERE id = ?;
```

Substitua `?` pelo `id` do paciente (visível na tabela `pacientes`).

---

## Dados que NÃO devem entrar no sistema

- Diagnóstico oncológico (CID) — não há campo; não improvise
- Resultado de exames — fora do escopo
- Informações financeiras — fora do escopo

O sistema é operacional (agendamento e rastreio de fluxo), não clínico.
