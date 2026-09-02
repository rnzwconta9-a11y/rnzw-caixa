# 3105 Custom Build — v1.2.0

## Alterações desta versão

- Fluxo separado de **Usuário** e **Moderador**.
- Cleaner e Wallpapers removidos da navegação principal.
- Patches apresentados como **Arquivos**.
- Usuário pode visualizar/desbloquear/aplicar/restaurar/exportar arquivos, mas não pode criar, importar, editar ou excluir projetos.
- Moderador pode criar/importar/editar/excluir arquivos.
- Gerador de keys com planos de **1 hora, 1 dia, 15 dias e 30 dias**.
- Key inicia a contagem na primeira ativação.
- Key fica vinculada ao aparelho na primeira ativação.
- Menu do usuário mostra tempo restante, plano, expiração, desenvolvedor, segurança e compatibilidade.
- Português (pt-BR) adicionado como idioma padrão em instalações novas.
- Onboarding, tela de atualização e atribuição antiga foram removidos do fluxo principal.

## Acesso do moderador (desenvolvimento)

PIN inicial: `3105`

Troque o PIN dentro da aba **Keys > Moderador** antes de distribuir o aplicativo.

## Importante sobre as keys nesta etapa

O armazenamento de keys é **local**, usando UserDefaults. Isso permite testar o fluxo completo no mesmo aparelho/instalação.

Para o moderador gerar uma key no aparelho dele e o usuário ativar essa key em outro aparelho, será necessário conectar o `LocalKeyStore` a um backend/API. O modelo atual já separa geração, ativação, expiração, vínculo de aparelho e revogação para facilitar essa próxima etapa.

## Arquivos/Patches

Os pacotes continuam usando a estrutura `.3105` original e o sistema de aplicação/restauração existente. A interface de usuário foi limitada para evitar edição administrativa.
