## Resumo

-

## Verificação

- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp`
- [ ] `uv build`
- [ ] O catálogo e os links de documentação continuam consistentes.

## Segurança e privacidade

- [ ] Não inclui tokens, senhas, `.env`, sessões, respostas Firebase, notas ou anexos reais.
- [ ] Ferramentas de escrita/destrutivas continuam exigindo `confirm: true`.
- [ ] Atualizei `README.md`, `README.en.md`, `llms.txt`, `AGENTS.md`, `WRITES.md` e `docs/` quando alterei arquitetura, comandos, ferramentas ou contratos.
- [ ] Se executei teste autenticado, usei apenas artefatos prefixados e provei baseline restaurado/zero resíduo.

