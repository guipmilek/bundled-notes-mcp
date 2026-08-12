# Deploy no Prefect Horizon

O Prefect Horizon clona um fork, instala `pyproject.toml`, importa o objeto
FastMCP e fornece URL, OAuth, CI/CD e previews.

> [!IMPORTANT]
> Cada usuário deve fazer fork deste repositório e publicar o próprio deployment.
> Não use nem compartilhe um deployment de terceiros: ele acessa a conta Bundled
> Notes configurada nos secrets daquele servidor.

## Modelo operacional

- Um fork e um deployment por conta Bundled Notes.
- Horizon OAuth controla quem acessa aquele MCP.
- Credenciais Firebase ficam somente nos secrets do servidor do próprio usuário.
- Tokens renovados permanecem em memória; cold starts usam o refresh token.
- Payload logging deve ficar desabilitado porque notas e metadados são privados.

## Configuração

1. Faça fork do repositório no GitHub.
2. Acesse <https://horizon.prefect.io/> com GitHub e selecione o seu fork.
3. Configure o entrypoint `src/bundled_notes_mcp/server.py:mcp`.
4. Use `pyproject.toml` como arquivo de dependências.
5. Mantenha a autenticação do Horizon habilitada.
6. Cadastre `BUNDLED_FIREBASE_API_KEY`, `BUNDLED_FIREBASE_REFRESH_TOKEN` e,
   preferencialmente, `BUNDLED_FIREBASE_UID` da sua conta como secrets.
7. Faça deploy e teste `bundled_status` e `bundled_schema_status` antes de escritas.

O endpoint publicado terá formato semelhante a:

```text
https://seu-servidor.fastmcp.app/mcp
```

Use somente essa URL do seu próprio deployment ao conectar clientes MCP.

## Atualização do catálogo

Quando uma versão adiciona ferramentas ou parâmetros, atualize o seu fork, aguarde
o build saudável e reconecte o servidor nos clientes que mantiverem o catálogo em
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
