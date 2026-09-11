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

## 6. Populações iniciais do banco

O sistema não tem tela de importação em massa. O cadastro de pacientes é feito manualmente pela triagem via "+ Walk-in" na tela de Triagem.

**Quem cadastra:** o enfermeiro de triagem ou o profissional do agendamento.

**Fonte dos dados:** prontuário em papel ou sistema atual do hospital.

**Campos obrigatórios no primeiro cadastro:**
- Nome do paciente
- Protocolo quimioterápico (ou nome livre + cor + bucket de pré-medicação)
- Data da próxima sessão
- Total de ciclos prescritos

**Campos recomendados:**
- Número de prontuário (facilita busca)
- Telefone (facilita contato para confirmação)
- Nome da mãe + data de nascimento (identidade segura, dois identificadores — ANVISA RDC 220/2004)

> **LGPD:** o banco contém dados de saúde (dado sensível, Art. 11 LGPD). Leia o `docs/lgpd.md` antes de qualquer dado real entrar no sistema.

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
Description=CACON CACON
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

## 10. Calibração do scheduler

Os parâmetros do algoritmo ficam no topo de `scheduler.py` (bloco `# 1. ESTIMATIVAS CALIBRÁVEIS`). Os valores padrão refletem a escala real levantada com a farmacêutica do centro em setembro de 2026.

Se a escala de profissionais mudar (horários, número de técnicos/enfermeiros), edite o bloco `# 2. ESCALA DE PROFISSIONAIS` em `scheduler.py`. A capacidade do dia é derivada automaticamente da escala — não há número mágico hardcoded.

O parâmetro que mais move o teto do dia é `PUNCOES_POR_TECNICO_HORA`. Após 2–4 semanas de uso real, compare o teto calculado com o realizado no `/relatorio` e ajuste esse valor.
