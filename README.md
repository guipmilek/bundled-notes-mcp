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
uv sync --extra dev
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

| Grupo | Capacidades |
| --- | --- |
| Conta | Status autenticado e projeção segura do usuário |
| Compatibilidade | Auditoria sanitizada de schema e detecção de drift aditivo/quebrável |
| Bundles | Listar, consultar, criar, editar, arquivar, restaurar e excluir |
| Notas | Listar, buscar, criar, editar, duplicar, mover, concluir e excluir |
| Tags e tarefas | Criar, editar, aplicar, remover, trocar e executar ações |
| Kanban | Configurar colunas ordenadas e mover notas para coluna/backlog |
| Templates | Criar a partir de bundle, aplicar e excluir |
| Files & Photos | Listar, enviar, anexar, desanexar e excluir |

A busca filtra notas localmente porque o aplicativo também usa um índice/cache no
cliente, não um endpoint Firestore de texto completo. Os limites são finitos por
padrão; aumente-os deliberadamente em contas grandes.

## Desenvolvimento

```powershell
uv run ruff check .
uv run pytest
uv build
```

Consulte [engenharia reversa](docs/reverse-engineering.md),
[modelo de dados](docs/data-model.md), [manutenção de schema](docs/schema-maintenance.md)
e [testes](docs/testing.md). `llms.txt` contém
o mapa compacto para agentes.

## Limites conhecidos

- Endpoints Firebase e caminhos Firestore são detalhes de implementação, não uma
  promessa de compatibilidade.
- Importação do Google Keep, exportação JSON, lembretes e geração derivada de rich
  links foram observados, mas não são ferramentas de mutação na versão `0.1.0`.
- Antes de excluir um arquivo da conta, desanexe-o das notas relevantes.
- Contadores do documento de usuário podem atrasar; as listagens são a fonte
  operacional deste servidor.
