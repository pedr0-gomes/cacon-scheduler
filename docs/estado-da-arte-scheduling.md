# Estado da arte — escala e sequenciamento de quimioterapia ambulatorial

> **O que é este documento.** Síntese do estado-da-arte acadêmico sobre agendamento/escala de
> sessões de quimioterapia ambulatorial, ancorado numa dissertação diretamente análoga ao CACON,
> e a leitura do que isso significa para o centro. Draft para o Pedro curar.
>
> **Fonte principal:** POMPEU, Nana Flora Elias. *Otimização de escala de tratamento de
> quimioterapia: aplicação ao Hospital das Clínicas da UFMG.* Dissertação (Mestrado em Engenharia
> de Produção) — UFMG, Belo Horizonte, 2018. Orientador: Maurício Cardoso de Souza.
> Estudo de caso: **Ambulatório Borges da Costa, HC-UFMG**.

---

## 1. Por que essa dissertação é o análogo certo

O Borges da Costa é quase um espelho do CACON — mesma escala, mesmo tipo de serviço:

| | Borges da Costa (HC-UFMG) | CACON (CACON) |
|---|---|---|
| Rede | SUS, referência regional | SUS, referência regional |
| Origem dos pacientes | ~40% do interior de MG | interior do Ceará (45 municípios) |
| Espaços de infusão | **28 leitos** | **26 poltronas** |
| Volume | **41 pacientes/dia** | **~44 sessões/dia** |
| Equipe | 3 enfermeiros + 6 técnicos | (a confirmar) |

Não é uma referência genérica de "hospital grande": é um ambulatório do mesmo porte, no SUS,
com o mesmo perfil de demanda regional. O que vale lá tende a valer aqui.

---

## 2. O que a dissertação faz (o método)

Um modelo de **programação linear inteira (ILP)** que gera a **escala de agendamento** do dia —
isto é, quantos "espaços" de cada tipo de tratamento (por tipo de preparo × duração de infusão)
devem ser oferecidos em cada horário de início, para melhor alocar os recursos escassos.

- **Solver:** GLPK — **open-source** (relevante: reprodutível sem licença cara).
- **Variável de decisão:** `x[a,n,j,t]` = nº de pacientes com preparo tipo `a`, infusão de `j`
  horas, iniciando no horário `t`.
- **Evolução do modelo:** de monobjetivo → multiobjetivo, com **fronteira de Pareto** via método
  **ε-restrito** (equilibra "atender mais pacientes" contra "respeitar a frequência histórica dos
  tipos de tratamento").

### Recursos escassos modelados

1. **Leitos/poltronas** (capacidade física).
2. **Capacidade de manipulação de medicamento** (farmácia) — limite de doses por horário.
3. **Enfermagem**, com **nível de acuidade**: cada preparo/acompanhamento consome capacidade da
   equipe; cada enfermeiro cobre acuidade acumulada até um teto.
4. **Horas de funcionamento** (8h–19h; última infusão começa 16h).

### Restrições empíricas — que já espelham o modelo manual do pai

A autora refina o modelo com regras da vivência da equipe. Elas batem, uma a uma, com o que a
chefia do centro rascunhou na planilha:

| Restrição empírica na dissertação | Equivalente na planilha do pai |
|---|---|
| Tratamentos de **5–8h só iniciam de manhã** (margem p/ intercorrência e terminar no horário) | "**vermelhos/longos primeiro**", concentrados às 6h–7h |
| **Equilíbrio manhã/tarde** (limita desbalanço de inícios) | espalhar chegadas — o oposto do "**7 chegam às 7h**" |
| **Piso mínimo** por tipo de tratamento | manter mix de perfis por janela |
| **Acuidade:** infusão 1–4h = nível 1; 5–8h = nível 2; enfermeiro cobre acuidade ≤ 6 | (não formalizado, mas é a intuição de "quem é pesado, quem é leve") |

> A dissertação é, essencialmente, a **formalização matemática do que o pai já fez à mão.**
> Ele chegou na escala por intuição de campo; ela chega por otimização — no mesmo problema.

---

## 3. O ganho medido lá (a prova de viabilidade)

- Ocupação dos leitos no Borges: apenas **57%** (a ANS recomenda **75–85%**).
  — O CACON está em **63%** de utilização de poltrona pelos dados do pai: mesmo regime de
  subutilização, mesma ordem de grandeza.
- Só **reorganizando a escala**, sem obra nem contratação, o modelo mostra potencial de
  **+70% de atendimentos** (de 41 para 70 pacientes/dia).
- Elevar em 15% a capacidade de farmácia levaria a ocupação de 57% → 64% (ganho marginal;
  o grande ganho vem da **escala**, não de mais capacidade).

> A mensagem que interessa ao CACON: **o maior ganho não custa infraestrutura — está na ordem.**

---

## 4. As 3 diferenças CACON × Borges (o que muda o desenho)

A dissertação é fundação, não receita para copiar. Três diferenças mudam o desenho para o CACON —
e todas favorecem o CACON:

### 4.1 O gargalo é a enfermagem/punção, não a farmácia
No Borges, o recurso *binding* (que limita) é a **farmácia** (manipulação); a restrição de
enfermagem existe no modelo mas fica **dormente** (não-ativa). No CACON é o inverso: a droga
está pronta em **D-1**, então o que trava é a **punção/enfermagem na entrada** (ver
`analise-campo.md` §4). **A restrição já está modelada na dissertação — só precisa ser a que
manda.** É reusar a mesma máquina virando a chave de qual recurso é o crítico.

### 4.2 O CACON pode operar *off-line* (a literatura diz que rende mais)
O Borges agenda **online** — o paciente pede horário e a clínica encaixa contra uma escala-modelo,
sem conhecer o dia inteiro de antemão. O CACON, com **prescrições prontas em D-1**, conhece o
**grupo inteiro da véspera** → pode montar a escala **off-line** (com o conjunto fechado de
pacientes do dia). A literatura é clara que o agendamento off-line dá resultado melhor que o
online — o Borges simplesmente não tinha essa informação a tempo. **O CACON tem.**
Referência que valida a prática D-1: **Dobish (2003)**, *next-day scheduling* (infusão no dia
seguinte aos exames) — reduz espera e melhora carga de enfermagem e farmácia.

### 4.3 O CACON tem o dado real que trata a incerteza
O modelo da dissertação é **determinístico**. A autora admite (na conclusão) que tratar
**incerteza** — atraso, absenteísmo, intercorrência — exigiria **programação dinâmica/estocástica**,
e que isso depende de **coletar dados reais de variabilidade**. O dado do pai (263 sessões
cronometradas) **é** essa variabilidade medida. É a matéria-prima que falta ao próximo passo.

---

## 5. A assimetria de ouro (por que o CACON tem algo que a literatura não tem)

A autora confessa a mesma limitação **três vezes** ao longo da dissertação: os dados dela são de
tempo **agendado**, não do tempo **real** de permanência. Trechos (paráfrase fiel):

- *"os dados históricos que foram a base das análises são desta previsão de duração das sessões e
  não, efetivamente, de suas durações."*
- *"seria de grande interesse a coleta de dados pelo ambulatório quanto às incertezas citadas."*
- No Borges, **quem estima a duração da sessão é o setor administrativo, sem conhecimento clínico** —
  o que gera desalinhamento entre duração prevista e efetiva.

> **A assimetria:** a tese tem o **método** (ILP, publicado, com solver open-source) mas **dado
> fraco** (agendado). O pai tem o **dado que falta a toda a literatura** (263 sessões de tempo
> **real** cronometrado). **CACON = método publicado + o dado real que a academia reclama que falta.**

E note a rima: a nota do pai na aba "Análise" — *"Nosso trabalho é uma aproximação da realidade.
Falta-nos precisão"* — é literalmente a mesma preocupação da acadêmica, dos dois lados do mesmo
problema. Um tem o método sem o dado; o outro tem o dado e busca o método.

---

## 6. Ressalva honesta (o que a dissertação NÃO resolve)

A dissertação otimiza a **escala** — *quantos* espaços de cada tipo por dia — que é um passo
**antes** do **sequenciamento fino** da punção em tempo real que o dia do CACON exige. Ela é
**prova de viabilidade e fundação**, não solução pronta:

- Ela responde "como deve ser a agenda do dia" (planejamento da véspera).
- O gargalo do CACON (a espera de 35–46 min pela punção) vive um degrau abaixo: "dado o grupo do
  dia, em que **ordem** e **em que momento** cada paciente é puncionado".
- Os dois se encaixam: a escala (dela) define o campo de jogo; o sequenciamento (o que o pai
  persegue) joga dentro dele. O dado real do pai serve **aos dois**.

> Para a visita: a dissertação é o argumento de que **isso é planejável e já foi provado num
> ambulatório igual** — não a promessa de um produto. Mantém o tom Mom Test.

---

## 7. Referências-chave

Da bibliografia da dissertação (seção 8), as mais relevantes para o eixo escala/sequenciamento:

- **Turkcan, A.; Zeng, B.; Lawley, M.** Chemotherapy operations planning and scheduling.
  *IIE Transactions on Healthcare Systems Engineering*, v. 2, n. 1, p. 31–49, 2012.
  — Referência de base para a complexidade do agendamento de quimioterapia.
- **Hahn-Goldberg, S.; Carter, M.; Beck, J.; Trudeau, M.; Sousa, P.; Beattie, K.** Dynamic
  optimization of chemotherapy outpatient scheduling with uncertainty. *Health Care Management
  Science*, v. 17, n. 4, p. 379–392, 2014.
  — Único trabalho que trata **escala de agendamento com atualização dinâmica** e considera a
  farmácia como limitante; o mais próximo do problema do CACON com incerteza.
- **Dobish, R.** Next-day chemotherapy scheduling: a multidisciplinary approach to solving workload
  issues in a tertiary oncology center. *Journal of Oncology Pharmacy Practice*, v. 9, n. 1,
  p. 37–42, 2003.
  — Valida empiricamente a prática **D-1** (infusão no dia seguinte aos exames): reduz espera e
  alivia enfermagem + farmácia. É a prática que o CACON já tem.
- **Alvarado, M.; Ntaimo, L.** Chemotherapy appointment scheduling under uncertainty using
  mean-risk stochastic integer programming. *Health Care Management Science*, p. 1–18, 2016.
  — Caminho **estocástico** para tratar a incerteza (atraso/absenteísmo/intercorrência) que a
  dissertação deixa em aberto — o passo que o dado real do pai habilita.
- **Ahmadi-Javid, A.; Jalali, Z.; Klassen, K. J.** Outpatient appointment systems in healthcare:
  A review of optimization studies. *European Journal of Operational Research*, v. 258, n. 1,
  p. 3–34, 2017.
  — Revisão ampla de sistemas de agendamento ambulatorial; mapa do campo.

Outras citadas na dissertação, úteis se aprofundar acuidade de enfermagem e classificação de
pacientes: Liang & Turkcan (2015, acuity-based nurse assignment); Liang et al. (2014, patient flow
em clínica oncológica); Chabot & Fox (2005, patient-classification em infusion center);
Woodall et al. (2013, melhoria de acesso no Duke Cancer Institute).

<!-- Pedro: dados bibliográficos completos de todas as 42 referências estão no fim de /tmp/nana.txt (seção 8). Puxei as 5-6 diretamente ligadas ao eixo. Se for citar em algum edital/artigo, conferir volume/página na fonte. -->
