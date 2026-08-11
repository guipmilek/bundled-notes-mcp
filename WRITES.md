# Escritas e segurança

Toda ferramenta que altera a conta exige `confirm: true` e retorna antes de chamar
Firebase quando a confirmação não é enviada.

## Fluxo recomendado

1. Liste o bundle, nota, tag, template ou arquivo e confira o ID atual.
2. Chame a ferramenta de escrita sem `confirm` para revisar a operação proposta.
3. Confira destino, campos, referências e se a ação é reversível.
4. Repita os mesmos argumentos com `confirm: true`.
5. Consulte novamente o recurso e confirme o resultado.

## Semântica

- Updates usam máscaras Firestore e preservam campos desconhecidos.
- Arquivar/restaurar define um estado explícito; não usa toggle cego.
- Mover uma nota cria e relê o destino antes de excluir a origem. Se a exclusão da
  origem falhar, a cópia é removida como compensação.
- Excluir bundle ou template remove recursivamente suas subcoleções conhecidas.
- Excluir tag bloqueia referências de notas/Kanban, salvo override explícito.
- Upload cria objeto, catálogo e referência da nota; falhas intermediárias tentam
  remover os registros já criados.
- Desanexar mantém o arquivo no catálogo. Excluir o arquivo da conta é permanente.

O Firestore não oferece uma transação única para todos os fluxos multietapa usados
pelo app. A compensação reduz resíduos, mas não substitui backup.

## Annotations MCP

- Leituras: `readOnlyHint=true`, não destrutivas e idempotentes.
- Criações: escrita não destrutiva e não idempotente.
- Updates, movimentações e exclusões: destrutivas; o estado desejado é explícito.
- Todas as ferramentas operam somente na conta Bundled Notes configurada:
  `openWorldHint=false`.
