# Deploy no Prefect Horizon

O deploy remoto mantido é o Prefect Horizon. O Horizon clona o repositório,
instala `pyproject.toml`, importa o objeto FastMCP e fornece URL, OAuth, CI/CD e
previews.

## Modelo operacional

- Um deployment por conta Bundled Notes configurada.
- Horizon OAuth controla quem acessa o MCP.
- Credenciais Firebase ficam somente nos secrets do servidor.
- Tokens renovados permanecem em memória; cold starts usam o refresh token.
- Payload logging deve ficar desabilitado porque notas e metadados são privados.

## Configuração

1. Selecione o repositório no Horizon.
2. Configure o entrypoint `src/bundled_notes_mcp/server.py:mcp`.
3. Use `pyproject.toml` como arquivo de dependências.
4. Mantenha a autenticação do Horizon habilitada.
5. Cadastre `BUNDLED_FIREBASE_API_KEY`, `BUNDLED_FIREBASE_REFRESH_TOKEN` e,
   preferencialmente, `BUNDLED_FIREBASE_UID` como secrets.
6. Faça deploy e teste `bundled_status` e `bundled_schema_status` antes de escritas.

O endpoint mantido é:

```text
https://bundled-notes-mcp.fastmcp.app/mcp
```

## Atualização do catálogo

Quando uma versão adiciona ferramentas ou parâmetros, publique o commit, aguarde o
build saudável e reconecte o servidor nos clientes que mantiverem o catálogo em
cache. Valide versão, contrato de schema e contagem de ferramentas no Horizon
Inspector e no cliente final.

## Verificação de release

```powershell
uv sync --locked --extra dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp
uv build
```

Depois do deploy, execute a auditoria ao vivo com artefatos descartáveis, compare
as contagens com o baseline e confirme zero resíduo. Mudanças de schema seguem
`schema-maintenance.md`.
