# Conectar o deployment a um cliente MCP

O deployment mantido usa o endpoint:

```text
https://bundled-notes-mcp.fastmcp.app/mcp
```

A autenticação de entrada é gerenciada pelo Prefect Horizon. As credenciais do
Bundled Notes permanecem somente nos secrets do servidor.

Para clientes que aceitam MCP remoto:

- Nome: `Bundled Notes`
- Server URL: URL `/mcp` do Horizon
- Authentication: OAuth

Após um deploy que altera ferramentas ou parâmetros, remova e reconecte o MCP se o
cliente continuar exibindo um catálogo antigo. Confirme primeiro `bundled_status`,
o `server_version`, o `schema_contract_version` e a contagem esperada de ferramentas.

Prompts de teste:

- “Mostre o status do Bundled Notes.”
- “Liste meus bundles sem alterar nada.”
- “Execute a auditoria sanitizada de schema.”
- “Prepare a criação de uma nota de teste, mas não confirme.”

Antes de uma escrita real, revise IDs e payload no retorno
`confirmation_required`; só então repita com `confirm: true`.
