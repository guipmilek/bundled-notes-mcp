<p align="right">
  <a href="./README.en.md"><img src="https://img.shields.io/badge/lang-en-gray?style=flat-square&amp;labelColor=202024" alt="English" /></a>
  <img src="https://img.shields.io/badge/lang-pt--br-green?style=flat-square&amp;labelColor=202024" alt="Português" />
</p>

<h1 id="top" align="center">Bundled Notes MCP</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-%3E%3D3.11-3776ab?style=flat-square&amp;logo=python&amp;logoColor=white&amp;labelColor=202024" alt="Python >= 3.11" />
  <img src="https://img.shields.io/badge/FastMCP-3.x-7c3aed?style=flat-square&amp;labelColor=202024" alt="FastMCP 3" />
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square&amp;labelColor=202024" alt="MIT" /></a>
</p>

<p align="center">MCP não oficial para consultar e administrar uma conta autenticada do Bundled Notes Web.</p>

Este servidor local expõe bundles, notas Markdown, tags/tarefas, quadros Kanban,
templates personalizados, busca e Files & Photos pelo mesmo modelo Firebase usado
pelo aplicativo web.

> [!WARNING]
> Este projeto não é afiliado ao Bundled Notes. O aplicativo não publica uma API
> estável ou suportada; mudanças de schema ou regras Firebase podem quebrar a
> integração. Mantenha backup e revise toda escrita.

## Contrato de segurança

- Toda ferramenta que altera estado retorna `confirmation_required` sem chamar a
  API, a menos que receba `confirm=true`.
- Arquivamento e restauração são explícitos. Exclusões permanentes têm nomes claros
  e removem recursivamente as subcoleções Firestore conhecidas.
- Atualizações usam update masks e preservam campos desconhecidos.
- Tokens de autenticação, compra e download nunca são retornados pelas ferramentas.
- Downloads autenticados retornam Base64 somente até 10 MiB e nunca expõem URLs
  assinadas ou tokens do Firebase Storage.
- Movimentações criam e verificam o destino antes de remover a origem, com rollback
  compensatório da cópia quando necessário.
- Exclusões de tag bloqueiam referências pendentes por padrão.
- Uploads respeitam o limite observado de 400 MiB, validam tamanho/metadados no
  Storage, relêem o catálogo e compensam falhas parciais.
- `bundled_schema_status` compara formas sanitizadas do Firestore com um contrato
  versionado sem retornar títulos, conteúdo, nomes de arquivo, IDs ou outros valores.

Consulte [WRITES.md](WRITES.md) antes de habilitar mutações.

## Início rápido

Requer Python 3.11+ e [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --locked --extra dev
```

O bootstrap descobre a configuração pública atual do site e obtém um refresh token
sem imprimir a senha ou o token:

```powershell
uv run bundled-notes-bootstrap-auth --output .env
```

O helper solicita e-mail e senha interativamente. O `.env` é ignorado pelo Git e
deve ser tratado como uma senha. Se a descoberta automática deixar de funcionar,
informe a chave pública atual com `--api-key`.

## Executar

### Prefect Horizon (hospedado)

O deployment oficial deste repositório está disponível em:

```text
https://bundled-notes-mcp.fastmcp.app/mcp
```

O endpoint exige autenticação do Horizon e promove automaticamente builds bem-
sucedidos da branch `main`. No Horizon, use o entrypoint
`src/bundled_notes_mcp/server.py:mcp`, `pyproject.toml` como arquivo de dependências
e configure as variáveis Firebase como secrets. Os payloads MCP de requisição e
resposta devem permanecer desabilitados nos logs porque podem conter notas e
metadados privados.

### Local (stdio)

```powershell
uv run bundled-notes-mcp
```

Exemplo de configuração no Codex; em ambientes compartilhados, use um gerenciador
de secrets:

```toml
[mcp_servers.bundled-notes]
command = "uv"
args = ["--directory", "C:/Users/guipm/Desktop/MCPs/bundled-notes-mcp", "run", "bundled-notes-mcp"]

[mcp_servers.bundled-notes.env]
BUNDLED_FIREBASE_API_KEY = "..."
BUNDLED_FIREBASE_REFRESH_TOKEN = "..."
BUNDLED_FIREBASE_UID = "..."
```

Comece com `bundled_status` e `bundled_list_bundles`. Para uma escrita, chame uma
vez sem confirmação, revise IDs e payload, depois repita com `confirm=true`.

## Ferramentas

O catálogo da versão `0.3.0` expõe **43 ferramentas**. A leitura de lembretes é suportada; criação e agendamento permanecem deliberadamente bloqueados até existir um contrato upstream validado end-to-end.

| Grupo | Capacidades |
| --- | --- |
| Conta | Status autenticado e projeção segura do usuário |
| Compatibilidade | Auditoria sanitizada de schema e detecção de drift aditivo/quebrável |
| Backup | Exportar a conta ou um bundle em JSON estruturado |
| Bundles | Listar, consultar, criar, editar, reordenar, arquivar, restaurar e excluir |
| Notas | Listar, buscar, criar, editar, reordenar, duplicar, mover, concluir e excluir |
| Tags e tarefas | Gerenciar tags locais/globais, assinaturas, prioridade e ações |
| Kanban | Configurar colunas ordenadas e mover notas para coluna/backlog |
| Templates | Criar a partir de bundle, aplicar e excluir |
| Files & Photos | Listar, baixar até 10 MiB, enviar, anexar, desanexar e excluir |
| Rich links | Gerar ou atualizar previews pela callable function nativa |
| Lembretes | Listar metadados de lembretes anexados às notas |

A busca filtra notas localmente porque o aplicativo também usa um índice/cache no
cliente, não um endpoint Firestore de texto completo. Os limites são finitos por
padrão; aumente-os deliberadamente em contas grandes.

## Desenvolvimento

```powershell
uv sync --locked --extra dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp
uv build
```

Consulte o [índice de documentação](docs/README.md), o [mapa de arquitetura](docs/agent-architecture-map.md), o [playbook para agentes](docs/agent-playbook.md), o [guia de deploy](docs/deployment.md), a [manutenção de schema](docs/schema-maintenance.md) e os [testes](docs/testing.md). O arquivo `llms.txt` contém o mapa compacto e o catálogo exato para agentes.

## Limites conhecidos

- Endpoints Firebase e caminhos Firestore são detalhes de implementação, não uma
  promessa de compatibilidade.
- Escritas de lembretes continuam bloqueadas até que o contrato Android de
  agendamento/notificação possa ser validado end-to-end; persistir um documento
  Firestore sem garantir o disparo não é considerado suporte funcional.
- Importação do Google Keep permanece fora do MCP enquanto o fluxo oficial ainda
  estiver em desenvolvimento.
- Antes de excluir um arquivo da conta, desanexe-o das notas relevantes.
- Contadores do documento de usuário podem atrasar; as listagens são a fonte
  operacional deste servidor.
