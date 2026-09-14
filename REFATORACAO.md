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

## Segunda etapa — inimigos de chão

Concluída para Slime, CrystalStag, PossessedStudent e JanitorGuardian. `enemy_common.py` concentra 14 rotinas antes repetidas: `GroundEnemy` mantém posição, hitbox, dano, morte e respawn; `PausingGroundEnemy` acrescenta a patrulha com repouso e seu desenho. Cada classe concreta conserva os parâmetros de balanceamento. O slime conserva sua patrulha e seu alinhamento visual específicos.

`enemy.py` passou de 2.304 para 1.850 linhas. As classes de chefes, DarkWraith e SmallSlime foram conferidas por comparação da árvore sintática e permanecem iguais. Não houve alteração de velocidades, vida, tempos, regras de dano ou seleção de animações.

Validação desta etapa:

- Suíte completa: 18 testes aprovados.
- Referências capturadas no commit `4553e8e`: 16 cenários, 14.080 quadros de simulação e 1.328 desenhos amostrados idênticos. Incluem bordas, plataformas estreitas e deslocadas, invulnerabilidade após dano, pisão, morte e respawn.
- Comparação dos sete mapas: 4.200 quadros; imagens iniciais, posições finais, vidas e estados preservados. Relatório local em `.test-output/enemies-final.json`.
- Ponto de entrada desktop: 120 quadros com validação dos hooks do Pygame Zero.

A referência e seus critérios de manutenção estão em `tests/fixtures/README.md`. Esta extração reduz duplicação; não representa uma medição de ganho de FPS. As limitações de validação de áudio, WASM e partida completa da primeira etapa continuam aplicáveis.

## Terceira etapa — combate (12/09/2026)

`CombatSystem`, em `combat.py`, passou a concentrar nove rotinas: atualização de ataque e combo, pose do ataque, disparo, movimento/colisão dos projéteis, pisão, perigos lançados por inimigos, parry, contato/espada e cálculo do alcance. Os temporizadores de ataque e a lista de projéteis pertencem a `game.combat`.

A sessão é fornecida ao sistema como contexto. `Game` continua responsável por vidas, invulnerabilidade, respawn, drops e efeitos de tela, também usados por quedas e perigos ambientais. A posição das chamadas no ciclo permanece a mesma: parry antes dos perigos de chefes, contato/espada antes dos projéteis, pausas de impacto antes dos temporizadores de combate. Inventário, puzzles, colisões do terreno e comportamento dos inimigos não foram alterados.

`game.py` passou de 2.675 para 2.432 linhas. Não foram alterados dano, alcance, duração de combo ou intervalos de disparo. Esta etapa organiza responsabilidades; não promete ganho de FPS.

Validação:

- 13 testes novos de combate, executados primeiro na versão original e depois na extraída; 31 testes aprovados na suíte completa.
- Referência de 240 quadros no commit `aacce7c`, incluindo os sons solicitados, combo, direção, cooldown e trajetória dos projéteis, preservada em `tests/fixtures/combat_sequence.json`.
- Casos de ataque durante cooldown, finalizador do combo, projétil rejeitado pela invulnerabilidade, expiração antes da colisão, derrota comunicada uma vez, múltiplos inimigos no mesmo golpe, imunidade do chefe à espada, pisão, parry e pausa de impacto.
- Sete mapas, 4.200 quadros: mesmos pixels iniciais, posições finais, vidas e estados da referência anterior. Relatório local em `.test-output/combat-final.json`.
- 124 métodos restantes de Game comparados por AST, normalizando apenas o novo caminho das chamadas/atributos; fluxo preservado. Desktop validado com 120 quadros e os hooks do Pygame Zero.

A ampliação da suíte revelou que o cache de fontes do HUD sobrevivia a `pygame.quit()` entre grupos de testes, causando falha nativa no Windows ao reutilizar uma fonte. `test_support.shutdown_pygame()` agora limpa esse cache antes do encerramento; a alteração é exclusiva do suporte a testes.

As limitações de áudio audível, WASM e partida completa permanecem. O save do jogador foi preservado. As alterações desta etapa ficaram locais, conforme a orientação de não fazer commit ou push.

## Quarta etapa — pasta do jogo (12/09/2026)

O código de execução, `requirements.txt`, mapas, imagens, fontes, músicas, sons e o save local agora ficam em `jogo/`. O site, os testes, as ferramentas de verificação, o ambiente virtual e a documentação continuam fora dessa pasta. Os nomes de módulos nas etapas anteriores referem-se agora a arquivos dentro de `jogo/`.

Os caminhos internos dos recursos continuam relativos aos próprios módulos e mapas. As ferramentas da raiz e os testes usam `test_support.configure_game_imports()` para localizar os módulos. O site passou a buscar imagens e fontes em `../jogo/`; seus comandos e a árvore de arquivos foram atualizados, assim como o README e o diretório usado pelo script de compressão de PNGs. Os documentos e o script legado de remoção de órfãos permanecem históricos; esse script não foi executado nesta organização.

Validação da mudança de pastas:

- 31 testes aprovados e entrada desktop exercitada durante 120 quadros.
- Sete cenários, 4.200 quadros: pixels iniciais, posições finais, vidas e estados idênticos à referência da etapa de combate (`.test-output/layout-final.json`).
- 55 referências de mapas/tilesets e 30 referências locais do site conferidas, sem arquivos ausentes.
- Sintaxe dos módulos Python e do JavaScript verificada; save preservado byte a byte.

A mudança foi mantida local, sem commit ou push. Não foi gerado nem validado um novo build WASM no navegador.

## Quinta etapa — inventário e coleta de itens (12/09/2026)

`jogo/inventory.py` concentra seis rotinas antes presentes em `Game`: leitura das teclas de consumo, uso de itens, recompensa pela derrota de inimigos, criação e coleta de drops e coleta de ferramentas. `game.items`, uma instância de `InventorySystem`, mantém `counts` (quantidades), `drops` (itens no chão) e `key_was_down` (controle de tecla segurada).

`Game` continua coordenando fases, salas, persistência, interface e os sistemas da sessão, além de manter vidas e escudo. O combate comunica as derrotas a `game.items.on_enemy_defeated`. A ordem de consumo, combate, coleta e avanço de fase foi preservada. O JSON continua na versão 1, com a mesma chave `inventory` contendo um dicionário de quantidades.

Contagens e escudo atravessam fases e salas; drops são descartados nas trocas de mapa. O comportamento de reinício foi caracterizado: após derrota, o inventário permanece; após conclusão, ele é zerado. Os índices de ferramentas coletadas continuam no estado da sessão em `Game`, com as mesmas regras anteriores.

A coleta agora cria um único retângulo de detecção por chamada e reposiciona esse retângulo para cada drop, reduzindo alocações sem mudar a área de coleta. Não foi medida uma porcentagem de ganho de FPS. `game.py` passou de 2.432 para 2.337 linhas.

Validação:

- 12 contratos de inventário executados antes e depois da extração: cura limitada, vida fracionária, escudo cumulativo, teclas simultâneas/seguradas, itens não consumíveis, probabilidades de drop, limites de colisão, ferramentas, transições, reinício e roundtrip de save.
- Suíte completa: 43 testes aprovados. Desktop: 120 quadros com validação dos hooks.
- Sete cenários, 4.200 quadros: mesmos pixels iniciais, posições finais, vidas e estados da etapa anterior. Relatório local em `.test-output/inventory-final.json`.
- Comparação de AST dos 119 métodos restantes de Game, exceto o construtor, normalizando apenas os novos caminhos e chamadas de reset. As seis rotinas extraídas também foram comparadas, considerando o deslocamento deliberado da criação do retângulo para fora do loop.
- SHA-256 do save do jogador preservado. Sem commit ou push. Áudio audível, partida completa e execução WASM no navegador não foram validados nesta etapa.

## Sexta etapa — puzzles e interações (12/09/2026)

`PuzzleSystem`, em `jogo/puzzles.py`, concentra 13 rotinas antes presentes em `Game`: atualização e conclusão dos minigames, coleta das peças dos dois microscópios, uso e abertura das duas bancadas, preparação dos sprites, caixa de energia, alavanca e sequência de botões. `game.puzzles` mantém os estados desses puzzles; `game.minigame` continua sendo o mesmo `MinigameManager`, para preservar os pontos de entrada usados pelo desktop e pela versão web.

O estado dos puzzles atravessa entradas e saídas de salas secundárias e é reiniciado por `load_level`, como antes. Os dicionários de encaixes dos microscópios e de fios da caixa de energia continuam sendo passados por referência aos minigames, portanto fechar e reabrir uma atividade preserva o progresso da sessão. A bancada do laboratório escondido usa um dicionário independente da bancada antiga.

`InteractionSystem`, em `jogo/interactions.py`, concentra seis rotinas: despacho das interações, portas, elevador secreto, consulta da barreira, conversa com NPC e avanço de diálogo. `game.interactions` mantém a fila das conversas com várias falas. A prioridade permanece portas, elevador, NPC, caixa de energia, bancada do laboratório escondido e, por último, alavanca, sequência e bancada do corredor subterrâneo. As transições do elevador continuam ocorrendo apenas no callback de término da cutscene.

`game.py` passou de 2.337 para 1.921 linhas. A extração não modifica regras, balanceamento, controles, imagens nem o formato v1 do save. Persistir puzzles após fechar o jogo continua sendo uma evolução separada, que exigirá uma decisão de formato e migração.

Validação:

- 18 testes de caracterização de interações e puzzles foram executados antes e depois da extração; a suíte completa tem 62 testes aprovados.
- Um teste de integração confirma que o estado dos puzzles sobrevive à troca de sala e reinicia ao carregar outra fase. Também há contratos para prioridade, callbacks do elevador, filas de diálogo, debounce de ESC e identidade dos dicionários entregues aos minigames.
- As 19 rotas movidas foram comparadas por AST com `.test-output/interactions-before-game.py`, normalizando apenas os novos caminhos e nomes; os corpos e a ordem das operações permaneceram iguais.
- Sete cenários, 4.200 quadros: mesmos pixels iniciais, posições finais, vidas e estados da etapa de inventário. Relatório local em `.test-output/puzzles-final.json`.
- Entrada desktop exercitada durante 120 quadros depois das duas extrações, incluindo os hooks do Pygame Zero. `git diff --check` não apontou erros.
- SHA-256 do save do jogador preservado. Sem commit ou push. Áudio audível, partida completa e execução WASM no navegador não foram validados nesta etapa.

## Sétima etapa — inimigos com estados específicos (12/09/2026)

Antes de mover novas classes, foi criada uma referência determinística para `DarkWraith`, `SmallSlime`, `Librarian`, `Specimen` e `SlimeKing`. Quatro cenários em `tests/special_enemy_scenarios.py` percorrem 6.600 quadros e registram hashes do estado a cada quadro, transições explícitas, ataques, hazards, objetos lançados, dano, morte, respawn e invocações. Os resultados anteriores à extração ficam em `tests/fixtures/special_enemies.json`.

`DarkWraith` foi movido sem alteração para `jogo/enemy_wraith.py`; seu balanço vertical, antecipação, investida, recuperação, dano, morte, respawn e desenho continuam independentes da patrulha dos inimigos de chão. `SmallSlime` foi movido para `jogo/enemy_summons.py` e também não foi encaixado numa classe-base de inimigo permanente: ele conserva a patrulha, a morte terminal e a ausência de respawn próprias.

Os chefes permaneceram independentes entre si: `Librarian` foi movido para `jogo/enemy_librarian.py`, `Specimen` para `jogo/enemy_specimen.py` e `SlimeKing` para `jogo/enemy_slime_king.py`. Não foi criada uma classe-base que misturasse seus estados ou ataques. `enemy.py` reexporta as cinco classes específicas, preservando os imports de `Level`, combate e testes, e agora concentra apenas os quatro inimigos de chão; o arquivo passou de 1.850 para 136 linhas.

A comparação das árvores sintáticas completas produziu os mesmos hashes antes e depois da movimentação para as 124 rotinas das cinco classes específicas: 19 de `DarkWraith`, 11 de `SmallSlime`, 34 de `Librarian`, 34 de `Specimen` e 26 de `SlimeKing`. Os seis testes de inimigos passaram depois de cada extração. A suíte completa tem 65 testes aprovados; o benchmark dos sete cenários preservou pixels iniciais, posições finais, vidas e estados em relação a `.test-output/special-enemies-final.json`, com relatório em `.test-output/bosses-final.json`. O smoke desktop continuou passando por 120 quadros.

A caracterização confirmou dois comportamentos existentes que foram preservados, não corrigidos por suposição: `Librarian` entra em `ERRATA_ORBIT` com timer 15, mas transita para o mergulho depois de um único update nesse estado; e um `SmallSlime` morto permanece em `Level.enemies`, embora deixe de atualizar comportamento e de desenhar. Qualquer mudança nesses dois pontos deve ser tratada separadamente como decisão de balanceamento ou de ciclo de vida.

O save v1 e os recursos do jogo não foram alterados. Áudio audível, partida completa e execução WASM no navegador continuam sem validação.

## Oitava etapa — desenho dos mapas (12/09/2026)

Antes da otimização, foram congeladas 13 referências RGBA em pontos de
câmera distribuídos por todos os mapas TMX. Os casos incluem coordenadas
fracionárias, animações, bordas de chunks, casas e props maiores que o grid
e a camada `Frente`. Para esta última, uma faixa opaca é desenhada entre
`draw()` e `draw_foreground()`, protegendo também a ordem de sobreposição.

Tiles grandes continuam indexados em todos os chunks que sua imagem cruza,
para não desaparecerem nas bordas da câmera. `TiledMap` agora identifica
quais dessas entradas usam somente pixels totalmente opacos ou totalmente
transparentes e desenha apenas sua última ocorrência na travessia visível.
Essa posição preserva a composição histórica quando há outros tiles entre
as repetições. Imagens com alpha parcial ou modulação de alpha continuam
sendo desenhadas em todos os chunks, pois acumular transparência altera o
resultado.

Nos mapas atuais, 18 tiles seguros atravessam chunks e geravam 22 blits
redundantes no índice completo: sete tiles estáticos e um animado na vila,
oito tiles normais e dois da camada `Frente` na escola. Os outros mapas não
têm entradas cruzando chunks. A análise de alpha ocorre uma vez durante o
carregamento e fica em cache; não há varredura de pixels no laço de desenho.

Validação:

- As 13 capturas anteriores à mudança permaneceram byte a byte idênticas.
- Dois contratos sintéticos confirmam a remoção segura e preservam
  explicitamente as repetições de uma imagem semitransparente.
- Suíte completa: 68 testes aprovados. Desktop: 120 quadros com os hooks do
  Pygame Zero.
- Sete cenários, 4.200 quadros: pixels iniciais, posições finais, vidas e
  estados idênticos à etapa dos chefes. Relatório local em
  `.test-output/map-chunks-final.json`.

Esta etapa remove trabalho redundante, mas a variação das medições não
sustenta uma porcentagem de ganho de FPS. Nenhuma arte, regra, controle,
balanceamento ou formato de save foi alterado.

## Nona etapa — áudio e empacotamento web (13/09/2026)

`audio.py` deixou de procurar os objetos globais que o Pygame Zero injeta no
script principal. A fachada de preferências agora recebe uma implementação
explícita de `audio_backend.py`: começa com um backend silencioso e seguro, e
`main.py` e `main_web.py` configuram `pygame.mixer` quando a plataforma já está
pronta. Foram preservados os volumes, a persistência das preferências, a troca
de trilha, a proteção contra reinício da mesma música e o comportamento
silencioso quando um recurso ainda não existe.

Os três MP3 de música e os sete efeitos MP3/WAV existentes ganharam cópias OGG
para o navegador. Os originais permanecem intactos e são preferidos no
desktop. `pygbag.ini` exclui do arquivo web esses originais e também `save.json`
e `audio_settings.json`; no pacote, o mesmo resolvedor encontra as cópias OGG.

O pygbag sempre inicia `assets/main.py`, então executar o empacotador diretamente
com `main_web.py` ainda incluía a entrada desktop. `build_web.py` resolve isso
numa cópia temporária: substitui apenas o `main.py` preparado para o pacote,
gera `jogo/build/web` e valida o destino antes de trocar o build anterior. O
`jogo/main.py` real não é renomeado nem reescrito.

Validação:

- Sete testes novos caracterizam a fachada e o backend de mixer, incluindo
  resolução de extensões, cache de efeitos, loop e volumes.
- Os dez arquivos OGG foram abertos pelo mixer real com o driver de áudio
  dummy. Os formatos reportados pelo mixer permaneceram em 44,1 kHz, 16 bits e
  dois canais.
- O arquivo `jogo.apk` gerado contém a versão de `main_web.py` como
  `assets/main.py`, dez recursos de áudio — todos OGG — e nenhum dado local de
  save ou preferências.
- O build foi servido por HTTP e executado no navegador com CPython 3.12/WASM:
  chegou à tela de título e o comando **Jogar** abriu a introdução animada com
  diálogo e recursos gráficos. Não houve traceback do jogo nem erro de recurso.
- Suíte completa: 75 testes aprovados. Desktop: 120 quadros. O benchmark dos
  sete cenários preservou pixels iniciais, posições finais, vidas e estados em
  relação à etapa dos mapas, com relatório em `.test-output/audio-final.json`.

O teste confirma decodificação, chamadas do mixer e execução no navegador, mas
não substitui uma avaliação humana do áudio audível nem uma partida completa.

Nenhum nome lógico de música ou efeito, chamada de gameplay, controle, regra de
balanceamento ou formato de save foi alterado. O save v1 permaneceu intacto.

## Décima etapa — colisão pixel a pixel das rampas (13/09/2026)

O SAT anterior tratava cada sequência de rampas como um triângulo ideal. Ao
subir, seu menor vetor de translação apontava na normal da diagonal: além de
elevar a Lia, também a empurrava para trás. Em penetrações maiores, o SAT podia
escolher a aresta vertical e bloquear a subida completamente. A arte real ainda
tem uma borda em degraus de 2×2 pixels e duas colunas transparentes nas pontas,
detalhes que o triângulo não representava.

`TiledMap` agora cria e armazena uma máscara a partir do alpha do próprio tile,
respeitando sua orientação. `Level` une as máscaras dos tiles diagonais junto
com a geometria da rampa, portanto as costuras internas continuam ausentes.
`Ramp` calcula uma vez o primeiro pixel sólido de cada coluna e acompanha essa
superfície apenas no eixo vertical. A tolerância para subir acompanha a
velocidade do quadro, sem transformar a lateral alta numa escada; ao descer, o
snap só ocorre se a personagem já estava apoiada. Laterais e parte inferior
continuam sólidas e são separadas pela própria máscara, pixel a pixel. O
triângulo SAT permanece somente como fallback para uma rampa criada por código
sem máscara.

Cinco regressões novas cobrem subida sem recuo horizontal, descida contínua,
lateral/parte inferior sólidas, as máscaras reais da vila combinadas sem
emendas e uma travessia completa pelo `Game.move_player` até o platô. A suíte
completa passou com 80 testes e o smoke desktop com 120
quadros. No benchmark de 600 quadros, o roteiro da vila deixou de ficar preso
na primeira rampa: o ponto final passou de `(675, 368,65)` para
`(1997,35, 400)`. Imagem inicial, vidas e estados ficaram iguais, e os outros
seis cenários não mudaram. O novo relatório está em
`.test-output/ramp-final.json`.

## Décima primeira etapa — caminho de renderização e legado (13/09/2026)

As quatro camadas transparentes do parallax da vila continham grandes margens
sem pixels visíveis. `Assets` agora recorta essas margens uma vez no
carregamento, mas guarda a largura lógica e o deslocamento do conteúdo.
`Game._draw_repeating_background` continua repetindo cada camada no período
original e aplica o deslocamento no desenho. Uma regressão reconstrói as
camadas completas e confirma o mesmo RGBA pixel a pixel.

Com `CAMERA_ZOOM = 1`, que é a configuração normal, `Game.draw` passou a
desenhar o mundo diretamente na superfície lógica. O buffer de 1920×1080 e o
blit de tela cheia permanecem disponíveis somente quando o zoom é diferente de
1. A captura usada por cutscenes segue a mesma regra. As três superfícies
semitransparentes do rastro de dash também passaram a ser criadas uma vez em
`Assets`, em vez de serem alocadas em cada quadro. O método privado
`Assets._load_scaled_background`, sem chamadas, foi removido.

No benchmark determinístico, a troca do buffer intermediário pelo caminho
direto preservou pixels iniciais, posições finais, vidas e estados nos sete
cenários. Nesta máquina, uma amostra de 600 quadros por cenário passou de
9,99 para 8,73 ms/quadro na vila e de 8,99 para 7,79 ms/quadro na Fase 1;
as outras cinco cenas ficaram entre 3,40 e 5,58 ms/quadro. Esses valores são
amostras locais, não uma promessa de FPS em outro computador. O relatório está
em `.test-output/render-direct-final.json`.

A referência `vila/right_house_boundary` foi atualizada porque `vila.tmx`
recebeu uma edição intencional depois da captura anterior. As imagens base e de
primeiro plano foram inspecionadas antes da troca das duas hashes; os outros 12
pontos de câmera não mudaram.

Os documentos de auditoria e propostas receberam avisos de registro histórico.
O antigo `remover_orfaos.sh`, cuja lista antecedia a migração para `jogo/`, foi
transformado em inventário somente leitura: ele mostra candidatos existentes e
nunca apaga arte, backups ou builds. Recursos possivelmente úteis para conteúdo
futuro foram preservados.

Validação final desta etapa:

- suíte completa: 83 testes aprovados;
- entrada desktop: 120 quadros com os hooks do Pygame Zero;
- sete cenários, 4.200 quadros: estados e pixels de referência idênticos;
- `git diff --check` sem erros e save local preservado byte a byte.

## Décima segunda etapa — diálogos com falantes alternados (13/09/2026)

A conversa do hospital passou de seis para 12 beats e termina com “Você também
não”, no mesmo ponto em que surge o brilho coral. Lia agora participa das
conversas com os seis moradores e as cinco cientistas. As falas deixam de ser
apresentações isoladas, constroem gradualmente o assunto da mãe e reservam para
Sra. Amélia e Jaqueline as duas vezes em que Lia diz “câncer” em voz alta.

`InteractionSystem` ganhou uma sequência genérica de pares `(falante, texto)`.
Ela também normaliza strings e as antigas tuplas de strings, evitando quebrar
conteúdo anterior. NPCs, fragmentos de pesquisa, achados de salas e diálogos
automáticos usam a mesma fila. Depois da conversa principal, cada NPC oferece
um lembrete curto; esse histórico é apenas da fase atual e não altera o save.

O tutorial foi alinhado aos controles reais. Cadu saiu de depois do primeiro
slime e foi colocado no platô anterior, apoiado no terreno. Ele ensina que o
ataque funciona por `F` **ou clique esquerdo do mouse** e que pode ser repetido
se o inimigo continuar avançando. Zeca ensina a olhar para a direção desejada e
apertar `Q`; correr antes não é requisito do código.

Os créditos do site agora deixam explícito que as conversas atribuídas às
cientistas são dramatizações ficcionais baseadas em informações públicas, não
citações, opiniões ou aconselhamento médico. Nenhuma sprite foi substituída.

Validação:

- 88 testes aprovados, incluindo os três formatos de dados, troca de falante,
  repetição, posição do Cadu e as sequências de pesquisa e achados;
- todas as falas cabem na caixa no tamanho padrão de 17 px;
- entrada desktop exercitada durante 120 quadros;
- sete cenários, 4.200 quadros: pixels iniciais e estado final idênticos à
  referência anterior. Relatório em `.test-output/dialogues-final.json`.

## Estado da refatoração neutra

As etapas estruturais e as otimizações comprovadamente neutras desta rodada
estão concluídas. Não ficaram remoções automáticas de assets nem alterações de
arte, controles ou balanceamento pendentes.

## Evoluções futuras que exigem decisão

1. **Persistência ampliada.** Modelar o estado persistente de cada mapa e
   definir uma migração posterior do save se puzzles, ferramentas e chefes
   também precisarem sobreviver ao fechamento do jogo. Isso altera o contrato
   de dados; o formato v1 permanece intacto nesta rodada.
2. **Conteúdo e direção visual.** Repinturas de mapa, substituição da Lia e
   novas animações devem ser tratadas depois que os sprites finais forem
   aprovados, sem misturá-las com a refatoração neutra.

A temporização da órbita do Bibliotecário e a retenção de invocações mortas agora têm contratos específicos. Os parâmetros de balanceamento e os estados dos inimigos não foram modificados nesta etapa; qualquer mudança nesses contratos deve ficar separada das extrações estruturais.
