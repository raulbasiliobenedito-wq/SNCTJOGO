# Refatoração — 11/09/2026

Primeira etapa implementada na branch `testes`, com prioridade para preservar imagens, física, controles e regras da partida.

## Etapas concluídas

1. **Base de verificação.** Dependências desktop fixadas em `requirements.txt`; benchmark portátil no Windows, relatórios JSON, capturas e comparação automática. Testes usam dados temporários. O roteiro de 600 quadros alcança os eventos de interação, item e disparo que ficavam fora do benchmark antigo de 250 quadros.
2. **Separação de responsabilidades.** Carregamento de imagens extraído para `assets.py`; regras e textos para `game_data.py`; persistência para `progress.py`; adaptadores comuns para `input_adapter.py`. `Game` continua coordenando a sessão e mantém os mesmos pontos de entrada.
3. **Contrato de desenho.** `Level.draw` recebe recursos e um `WorldDrawState`, substituindo a lista extensa de sprites e estados posicionais. A sequência de desenho foi preservada.
4. **Persistência e coletas.** Save validado antes de alterar a sessão e escrito em arquivo temporário antes da substituição. Erros são registrados sem interromper a partida. Artefatos usam conjuntos independentes por fase/sala, mantidos ao sair e voltar à sala.
5. **Alocações de desenho.** Reutilização do fundo escuro dos minigames (cache limitado), brilho dos projéteis (cache limitado) e imagem ampliada do diagrama da caixa de energia (cache da instância).

## Correções deliberadas de comportamento

- A saída da escola grava o save depois de desbloquear o ataque à distância. Saves v1 de fases posteriores com o desbloqueio ausente são normalizados ao carregar.
- A saída da vila salva a escola e seu checkpoint, permitindo continuar na fase recém-iniciada.
- Coletar o artefato de índice zero da biblioteca não impede mais a coleta do índice zero do laboratório.
- Um save inválido não troca parcialmente a fase nem altera o personagem antes de falhar.

O formato continua v1. O progresso de puzzles e salas continua restrito à sessão; não foi introduzida uma migração de save para persistir esses dados.

## Validação realizada

- 15 testes de regressão aprovados: saves, falha de substituição de arquivo, entradas inválidas, desbloqueio, passagem vila/escola, coletas por sala, arraste/retomada do microscópio, encaminhamento de mouse, entrada web nativa e referências de pixels para caches.
- `smoke_main.py`: 120 quadros, validação real dos nomes dos hooks pelo Pygame Zero e execução dos handlers desktop.
- Benchmark: 600 quadros em cada um dos sete cenários, totalizando 4.200. As sete imagens iniciais, posições finais, vidas e contagens de estados coincidiram com a referência anterior às mudanças estruturais.
- Comparação separada dos modos parafusos e fios da caixa de energia contra o código anterior: pixels idênticos após desenhos repetidos.
- O SHA-256 do `save.json` do jogador permaneceu inalterado durante as verificações.

As medições de tempo oscilaram entre execuções com tarefas concorrentes. As mudanças eliminam alocações e escalas repetidas, mas esses números não sustentam uma porcentagem de ganho de FPS. Não houve validação de áudio audível, uma partida completa ou build WASM em navegador nesta rodada.

Relatórios e capturas locais: `.test-output/before.json`, `.test-output/final.json` e as pastas `before/` e `final/`. São artefatos de verificação ignorados pelo Git.

## Próximas etapas, em ordem

1. **Inimigos comuns.** Criar testes de caracterização por estado e extrair apenas rotinas equivalentes de patrulha, dano, animação e respawn. Manter os estados específicos de chefes separados. Aceite: mesma sequência de estados e posições com entradas determinísticas.
2. **Combate e interações.** Separar de `Game` os sistemas de combate, inventário e puzzles em mudanças independentes. Manter a ordem de atualização e os temporizadores em quadros; não converter a física para `dt` nesta etapa. Aceite: regressões de colisão, dano, parry e progressão.
3. **Desenho dos mapas.** Resolver a duplicação de tiles entre chunks junto com a ordem de sobreposição das camadas. A tentativa isolada de deduplicação alterou capturas, portanto `tiled_map.py` foi mantido como estava. Criar referências em vários pontos de câmera, incluindo transparência e objetos grandes, antes de otimizar.
4. **Sessão e save completos.** Modelar o estado persistente de cada mapa e definir a migração para uma versão posterior do save se puzzles, ferramentas e chefes também precisarem sobreviver ao fechamento do jogo.
5. **Áudio e empacotamento web.** Separar o backend de áudio dos globais do Pygame Zero, depois validar no navegador. O teste web atual verifica a integração da entrada com Pygame nativo, não o ambiente WASM.
6. **Documentação e conteúdo legado.** Consolidar os documentos históricos e ferramentas de arte; remover código comprovadamente sem uso. Manter assets e arquivos de mapas em seus caminhos até revisar todas as referências TMX/TSX.

A temporização da órbita do Bibliotecário e o descarte de invocações mortas precisam de testes de combate específicos antes de entrar numa alteração posterior. Os parâmetros de balanceamento e os estados dos inimigos não foram modificados nesta etapa.
