# Copie este arquivo para config.py e preencha os valores antes de rodar.
# config.py está no .gitignore — nunca commite credenciais reais.

SENHA_TRIAGEM = "troque-esta-senha"        # senha usada pelo enfermeiro de triagem no login
SESSION_SECRET = "troque-esta-chave-longa" # string aleatória longa; gere com: python -c "import secrets; print(secrets.token_hex(32))"
