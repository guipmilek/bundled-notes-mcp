# Contribuindo

Este projeto usa endpoints não documentados e pode acessar dados pessoais reais.
Mudanças devem ser pequenas, revisáveis e acompanhadas de testes.

```powershell
uv sync --extra dev
uv run ruff format .
uv run ruff check .
uv run pytest
uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp
uv build
```

Regras:

- Nunca inclua `.env`, credenciais, tokens, sessões, respostas Firebase, conteúdo
  de notas ou anexos reais.
- Toda escrita exige `confirm: true`.
- Preserve campos desconhecidos com updates parciais.
- Atualize `llms.txt` e a documentação ao alterar contratos ou arquitetura.
- Para mudanças do Bundled Notes Web, siga `docs/schema-maintenance.md` e anexe
  somente relatórios sanitizados de campos/tipos.
- Testes ao vivo devem usar um prefixo único e remover todos os artefatos.

O projeto foi desenvolvido majoritariamente com assistência de IA. Contribuições
assistidas são aceitas, mas precisam de revisão humana e verificação local.
