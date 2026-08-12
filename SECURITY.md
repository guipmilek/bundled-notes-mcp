# Segurança

Este MCP acessa notas, arquivos e configurações reais de uma conta Bundled Notes.

- Nunca faça commit de `.env`, tokens, senhas, sessões, respostas Firebase, notas
  privadas, anexos ou URLs com download tokens.
- Configure secrets somente pelo ambiente do processo ou por um gerenciador de
  secrets confiável.
- Use um fork e um deployment por conta. Nunca conecte ao deployment do
  mantenedor ou de outra pessoa: ele opera com os secrets da conta configurada
  naquele servidor.
- Não compartilhe a URL do deployment nem conceda OAuth a terceiros.
- O refresh token é equivalente a uma senha. Revogue-o e troque as credenciais se
  ele aparecer em chat, log, screenshot ou commit.
- Nunca passe a senha do Bundled Notes como argumento de ferramenta MCP.
- Revise toda escrita e exija `confirm: true`.
- Prefira arquivar a excluir. Exclusões permanentes não têm recuperação pelo MCP.
- Use apenas artefatos descartáveis e identificáveis em testes autenticados.

`BUNDLED_FIREBASE_API_KEY` é uma chave pública do frontend, mas continua sendo
configurada por variável de ambiente e não deve ser hardcoded no código.

Para reportar uma vulnerabilidade, use o canal privado de security advisories do
GitHub e não inclua dados reais da conta na prova de conceito.
