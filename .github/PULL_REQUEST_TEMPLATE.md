## Resumo

-

## Verificação

- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp`
- [ ] `uv build`

## Segurança e privacidade

- [ ] Não inclui tokens, senhas, `.env`, sessões, respostas Firebase, notas ou anexos reais.
- [ ] Ferramentas de escrita/destrutivas continuam exigindo `confirm: true`.
- [ ] Atualizei `llms.txt`, `AGENTS.md` e `docs/` quando alterei arquitetura ou contratos.
