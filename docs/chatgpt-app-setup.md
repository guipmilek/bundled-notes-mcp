# Conectar o Bundled Notes MCP ao ChatGPT

> [!IMPORTANT]
> Faça fork deste repositório e publique o seu próprio deployment no Prefect
> Horizon antes de conectar o MCP. Cada deployment acessa a conta Bundled Notes
> definida nos secrets daquele servidor. Não use a URL publicada pelo mantenedor
> nem o deployment de outra pessoa.

No seu fork, configure somente as suas credenciais e mantenha a autenticação do
Horizon habilitada. Copie do seu deployment a URL terminada em `/mcp`, semelhante
a:

```text
https://seu-servidor.fastmcp.app/mcp
```

As credenciais do Bundled Notes permanecem somente nos secrets do seu servidor e
não são informadas ao ChatGPT durante a conexão.

## Metadados prontos para copiar

| Campo | Valor |
| --- | --- |
| Nome | `Bundled Notes` |
| Descrição | `Consulte e gerencie bundles, notas, tags, Kanban, templates e arquivos da sua conta Bundled Notes, com confirmação obrigatória antes de alterações.` |
| Server URL | A URL `/mcp` exibida pelo seu deployment no Horizon |
| Authentication | OAuth |
| Imagem | [`assets/bundled-notes-mcp.png`](../assets/bundled-notes-mcp.png) |
| Formato da imagem | PNG quadrado, 512 × 512, menor que 100 KB |

A imagem usa o ícone público do aplicativo Bundled Notes somente para identificar
a integração. Bundled Notes e sua identidade visual pertencem aos respectivos
titulares; este projeto continua não oficial e não afiliado.

## Passo a passo no ChatGPT

1. Confirme que você publicou o seu fork e copiou a URL do seu deployment.
2. Abra **Configurações** no ChatGPT.
3. Entre em **Segurança e login** e ative o **Modo de desenvolvedor**.
4. Abra **Plugins**.
5. Selecione **+** para adicionar um plugin.
6. Informe o nome, a descrição e a Server URL da tabela acima.
7. Quando a interface solicitar uma imagem, envie
   `assets/bundled-notes-mcp.png`.
8. Crie a conexão e conclua o OAuth do seu deployment no Horizon.
9. Revise as ferramentas e os metadados detectados antes de usar o MCP.

A disponibilidade do modo de desenvolvedor e de plugins pode depender do plano e
das políticas do workspace. Consulte a
[documentação oficial de conexão do ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt).

## Validar a conexão

Execute, nesta ordem:

- “Mostre o status do Bundled Notes.”
- “Liste meus bundles sem alterar nada.”
- “Execute a auditoria sanitizada de schema.”
- “Prepare a criação de uma nota de teste, mas não confirme.”

Confirme no primeiro retorno o `server_version`, o
`schema_contract_version` e a contagem esperada de ferramentas. Uma escrita
deve primeiro retornar `confirmation_required` e `api_called=false`.
Revise IDs e payload antes de repetir a chamada com `confirm: true`.

## Atualizar depois de um deploy

Se ferramentas ou parâmetros mudarem e o ChatGPT continuar mostrando um catálogo
antigo:

1. confirme que o novo build do seu deployment está saudável;
2. remova a conexão antiga do plugin;
3. adicione novamente a URL `/mcp` do seu próprio deployment;
4. repita os testes de validação acima.

Nunca coloque credenciais do Bundled Notes na descrição, na URL ou em prompts.
