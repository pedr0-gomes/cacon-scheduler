# Guia de instalação — CACON

Este documento é para quem vai instalar e manter o sistema. Público: TI do hospital ou desenvolvedor responsável pela implantação.

---

## Requisitos

| Requisito | Mínimo | Observação |
|---|---|---|
| Python | 3.13+ | |
| uv | qualquer | gerenciador de pacotes/ambientes |
| Sistema operacional | Linux ou macOS | Windows funciona mas não foi testado |
| Rede local | acesso por IP ou nome | todos os computadores do setor precisam alcançar o servidor |
| Porta | 8001 (padrão) | ajustável no comando de inicialização |

O sistema não precisa de banco externo, servidor de nuvem nem internet após a instalação. Tudo roda localmente em SQLite.

---

## 1. Instalar o uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Feche e abra o terminal depois. Verifique:

```bash
uv --version
```

---

## 2. Clonar o repositório

```bash
git clone https://github.com/pedr0-gomes/cacon-scheduler.git
cd cacon-scheduler
```

---

## 3. Criar o arquivo de configuração

```bash
cp config.example.py config.py
```

Abra `config.py` e edite:

```python
SENHA_TRIAGEM = "senha-do-enfermeiro"   # escolha uma senha forte
SESSION_SECRET = "string-aleatória-longa"
```

Para gerar um `SESSION_SECRET` seguro:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> **Atenção:** `config.py` nunca deve ser commitado nem compartilhado. Ele está no `.gitignore` por padrão.

---

## 4. Instalar dependências

```bash
uv sync
```

---

## 5. Rodar o servidor

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8001
```

O banco de dados (`cacon.db`) é criado automaticamente na primeira execução.

Para descobrir o IP do servidor na rede local:

```bash
hostname -I
```

Os outros computadores do setor acessam pelo navegador:

```
http://<IP-do-servidor>:8001
```

---

## 6. Primeira configuração (pela tela, sem mexer no código)

Tudo que precisa ser ajustado ao seu centro fica em **⚙ Configuração** (canto direito do menu; pede a senha). Nesta ordem:

1. **Parâmetros** (`/configuracao/parametros`) — número de poltronas (SUS, convênio, hematologia) e os tempos de cada etapa. Os tempos formam o **previsto** do Relatório; os valores padrão servem para começar.
2. **Pacientes** (`/configuracao/pacientes`) — cadastre quem já está em tratamento, a partir das fichas: nome, protocolo, data da próxima sessão, quantos ciclos já foram feitos e, se souber, o horário. **Salvar e cadastrar o próximo** para ir em sequência.
3. **Escala da equipe** (`/configuracao/escala`) — opcional. É só registro de quem trabalha em cada dia; não limita a agenda nem a quantidade de pacientes.

Depois da carga inicial, o dia a dia acontece nas quatro telas do menu (Hoje, Salão, Agenda, Relatório) — ver [`uso.md`](uso.md). Pacientes novos entram pelo **+ Walk-in** (em Hoje, para o mesmo dia) ou pelo **+ Agendar paciente novo** (na Agenda, para um dia futuro).

**Campos recomendados no cadastro:**
- Número de prontuário (facilita busca)
- Telefone (para a confirmação de presença)
- Nome da mãe + data de nascimento (dois identificadores — ANVISA RDC 220/2004)

**Para testar antes dos dados reais:** `uv run python seed.py` cria pacientes fictícios (ontem concluído, hoje em andamento, próximos dias na Agenda). Num servidor que vai receber dados reais, rode o seed só numa cópia de teste.

> **LGPD:** o banco contém dados de saúde (dado sensível, Art. 11 LGPD). Leia o [`lgpd.md`](lgpd.md) antes de qualquer dado real entrar no sistema.

---

## 7. Backup automático

O script `backup.py` copia o banco com timestamp e mantém os últimos 30. Rodar manualmente:

```bash
uv run python backup.py
```

Para backup automático diário às 2h, adicione ao cron do servidor:

```bash
crontab -e
```

Adicione a linha (ajuste o caminho):

```
0 2 * * * cd /caminho/cacon-scheduler && uv run python backup.py >> /var/log/cacon-backup.log 2>&1
```

Os backups ficam em `backups/cacon_AAAA-MM-DD_HHMMSS.db`.

---

## 8. Rodar como serviço (Linux)

Para o servidor iniciar automaticamente com o sistema operacional, crie um serviço systemd:

```bash
sudo nano /etc/systemd/system/cacon.service
```

Conteúdo (ajuste os caminhos e o usuário):

```ini
[Unit]
Description=CACON Scheduler
After=network.target

[Service]
User=<usuario>
WorkingDirectory=/caminho/cacon-scheduler
ExecStart=/home/<usuario>/.local/bin/uv run uvicorn app:app --host 0.0.0.0 --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ativar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cacon
sudo systemctl start cacon
sudo systemctl status cacon
```

---

## 9. Migração para PostgreSQL (opcional, futuro)

O sistema usa SQLite por padrão — adequado para o volume do CACON. Se o hospital já tiver um servidor PostgreSQL e quiser migrar, veja `docs/migrar-postgres.md`.

---

## 10. Ajustar os tempos previstos

Os tempos de cada etapa ficam em **Configuração → Parâmetros** e no cadastro de cada paciente (pré-QT e QT). Ficam gravados no banco — não é preciso editar código nem reiniciar o servidor. Os valores em `scheduler.py` são só o **padrão** da primeira execução e dos botões "Restaurar padrão".

Depois de 2–4 semanas de uso, abra o **Relatório → Média por protocolo**: ele mostra quanto cada protocolo leva de verdade. Ajuste os tempos para o previsto ficar perto do real.

> Rode o servidor com **um único processo** (o comando do §5, sem `--workers`): os parâmetros ficam em memória e são recarregados do banco a cada alteração.

---

## 11. Atualizar uma instalação existente

```bash
cd /caminho/cacon-scheduler
uv run python backup.py        # backup antes de atualizar
git pull
uv sync
sudo systemctl restart cacon   # ou pare e rode de novo o comando do §5
```

O banco (`cacon.db`) é preservado: tabelas e colunas novas são criadas automaticamente no start, sem apagar dados.

### Atualização de novembro/2026 — o que muda para quem usa

Esta versão troca o agendamento automático pela gestão manual. **Nenhum dado se perde**; o que muda na tela:

- **Menu com quatro telas:** Hoje (era Triagem), Salão (era Painel), Agenda (era Lista; absorveu Confirmação e Horizonte) e Relatório. A Configuração fica no canto direito. Endereços antigos (`/confirmacao`, `/horizonte`) levam à Agenda.
- **Ninguém é mais limitado:** sem teto de pacientes por dia, sem vagas de walk-in, sem horário proibido. Horário e poltrona são escolhidos pela equipe.
- **Horário na Agenda, poltrona em Hoje.** Os pacientes já cadastrados aparecem na Agenda **sem horário** (campo em amarelo) — marque o horário de cada um. No dia, eles aparecem em Hoje, em *Aguardando poltrona*.
- **Relatório:** mostra o tempo de cada paciente, previsto → real, por etapa. Para funcionar, o Salão precisa registrar punção, pré-QT, QT e retirada.
- Guia completo: [`uso.md`](uso.md).

