# Echoes of Life — guia para entender e defender o código

Este material foi escrito para a apresentação de quarta-feira. Ele não tenta ensinar
Python do zero. O objetivo é dar um modelo mental do projeto inteiro, mostrar como as
partes conversam e preparar respostas que demonstrem compreensão real.

## 1. O resumo que você deve conseguir falar sem olhar

> Echoes of Life é um jogo de plataforma 2D feito em Python com Pygame. A entrada
> desktop usa Pygame Zero, enquanto a versão web usa um loop assíncrono do Pygame
> compatível com pygbag. A classe `Game` coordena a sessão, mas delega responsabilidades:
> `Player` controla movimento e animação, `Level` constrói o mundo a partir de mapas
> TMX do Tiled, `CombatSystem` resolve ataques, `InventorySystem` controla itens,
> `PuzzleSystem` controla puzzles e `InteractionSystem` trata portas, NPCs e diálogos.
> O jogo funciona como uma máquina de estados e, a cada quadro, primeiro atualiza a
> lógica e depois desenha o estado atual. A física usa hitboxes separadas da arte, os
> mapas usam culling por chunks para desempenho, e o save JSON é validado e gravado
> atomicamente.

Essa resposta já contém as decisões arquiteturais mais importantes. O resto do guia
explica por que cada frase é verdadeira.

## 2. O tamanho real do projeto

No estado analisado em 19/09/2026:

- 38 módulos Python diretamente em `jogo/`;
- 13.646 linhas nesses módulos;
- 15 arquivos de testes e 2.894 linhas de testes;
- 118 testes executados: 115 passaram e 3 falharam;
- os mapas `.tmx` são dados executáveis do jogo: eles determinam cenário, colisão,
  spawn, entidades, NPCs, portas, água, perigos e vários outros elementos.

Portanto, “entender cada parte” não significa decorar 13 mil linhas. Significa saber:

1. quem é responsável por cada dado;
2. qual é o fluxo de execução;
3. quais interfaces ligam os módulos;
4. quais estados e invariantes protegem as regras;
5. onde procurar quando uma pergunta for específica.

## 3. Arquitetura em uma imagem mental

```text
main.py / main_web.py
        |
        | teclado, mouse, dt e superfície
        v
      Game  ---------------------------------------------------+
        |                                                      |
        +--> Player          posição, velocidade, animação     |
        +--> Level           mapa, chão, entidades, inimigos   |
        +--> CombatSystem    combo, parry, projéteis, dano      |
        +--> InventorySystem itens, drops, consumo              |
        +--> PuzzleSystem    microscópio, painel, caixa         |
        +--> InteractionSystem portas, elevador, NPC, diálogo  |
        +--> Assets/VFX      imagens e efeitos                  |
        +--> audio           música, SFX e preferências         |
        +--> progress        validação e escrita do save        |
        |                                                      |
        +---------------------- draw --------------------------> tela
```

O padrão principal é **composição**: `Game` contém objetos especializados. Isso é
preferível a colocar todas as regras dentro de `Game`, porque cada sistema tem um motivo
diferente para mudar. Alterar a chance de drop pertence ao inventário; alterar gravidade
pertence à personagem; alterar leitura de TMX pertence ao leitor de mapa.

## 4. O ciclo de vida de um quadro

### 4.1 Entrada desktop

`jogo/main.py` é o ponto de entrada do Pygame Zero.

1. Configura o backend de áudio.
2. Cria uma única instância de `Game`.
3. Cria `LogicalScreen`, uma superfície de 1920 × 1080.
4. O Pygame Zero chama `update(dt)` repetidamente.
5. `update(dt)` chama `game.update(keyboard, dt)`.
6. O Pygame Zero chama `draw()`.
7. `draw()` pede a `Game` que desenhe na tela lógica e copia o resultado para a janela.

A tela cheia é aplicada uma vez no primeiro quadro. Recriar a janela a cada quadro seria
caro e poderia causar `pygame.error: failed to create renderer`.

### 4.2 Entrada web

`jogo/main_web.py` executa o mesmo núcleo sem Pygame Zero:

- inicializa Pygame diretamente;
- lê eventos em `pygame.event.get()`;
- atualiza um `KeyboardState` compatível com os atributos esperados pelo jogo;
- chama os mesmos `game.update(...)` e `game.draw(...)`;
- chama `pygame.display.flip()`;
- usa `await asyncio.sleep(0)` para devolver o controle ao navegador a cada quadro.

Essa separação é um exemplo de **adaptação de plataforma**: o núcleo não sabe se está no
desktop ou no navegador. Ele só exige objetos com as interfaces necessárias.

### 4.3 O dispatcher de `Game.update`

`Game.update` lê as teclas e escolhe exatamente um ramo principal:

```text
TITLE       -> atualiza menu inicial
SETTINGS    -> atualiza configurações
INTRO       -> atualiza prólogo
PAUSED      -> atualiza menu de pausa
GAME_OVER   -> atualiza tela de derrota
COMPLETE    -> atualiza tela de conclusão
minigame    -> pausa mundo e atualiza minigame
elevador    -> pausa mundo e atualiza cutscene
dialogue    -> pausa mundo e atualiza diálogo
hint        -> pausa mundo e atualiza dica
senão       -> atualiza gameplay normal
```

A ordem é importante. Um minigame ativo tem prioridade sobre diálogo e gameplay. Isso
evita que o mesmo clique arraste uma peça e também ataque, ou que Lia continue andando
atrás de uma tela modal.

### 4.4 O gameplay normal, na ordem real

`Game._update_playing` faz, resumidamente:

1. atualiza tremor da câmera;
2. respeita hit-stop ou pose de morte e pode encerrar o quadro cedo;
3. reduz os temporizadores das habilidades da Lia;
4. inicia dash se Q foi pressionado;
5. lê movimento;
6. atualiza ataque corpo a corpo;
7. trava direção e movimento durante o combo;
8. atualiza ataque à distância;
9. acorda chefes próximos e orienta chefes para a Lia;
10. atualiza plataformas, inimigos e tiles animados;
11. carrega Lia junto com plataforma móvel;
12. move Lia e resolve colisões;
13. limita Lia à arena de chefe, se houver;
14. escolhe quadro de animação;
15. sobrepõe o quadro de ataque, quando necessário;
16. atualiza efeitos visuais;
17. atualiza câmera;
18. reduz tempo da mensagem da HUD;
19. trata interações;
20. verifica queda, oxigênio, perigos, parry, dano, coleta e progresso.

Se o professor perguntar “o que acontece quando aperto uma tecla?”, descreva essa cadeia.

### 4.5 O fluxo de desenho

`Game.draw` é separado de `update`: desenho não deve decidir regras do jogo.

No gameplay, a ordem visual é:

1. fundo/parallax;
2. mapa e elementos de mundo;
3. prompts de porta/NPC e luz;
4. rastro do dash;
5. personagem;
6. camada de primeiro plano do Tiled;
7. VFX e projéteis;
8. filtro subaquático;
9. HUD;
10. overlays de estado, dicas, minigame e fade.

Essa ordem cria profundidade. A camada `Frente` é desenhada depois da personagem para que
uma coluna ou bancada possa ocultá-la parcialmente.

## 5. Estados: a ideia mais importante do projeto

Há estados em níveis diferentes.

### Estado global da sessão

Definido em `game_data.py`:

- `TITLE`
- `SETTINGS`
- `INTRO`
- `PLAYING`
- `GAME_OVER`
- `COMPLETE`
- `PAUSED`

`Game.state` decide o ramo principal de atualização e desenho.

### Estados modais dentro de `PLAYING`

Diálogo, dica, minigame e cutscene do elevador usam `active` em vez de criar mais estados
globais. Eles acontecem apenas durante a partida e temporariamente bloqueiam o mundo.

### Estados da personagem

`Player` não guarda uma única string de estado. A pose é derivada de fatos como:

- `hurt_timer > 0`;
- `ranged_timer > 0`;
- `dashing`;
- `swimming`;
- `grounded`;
- sinal e módulo de `vy`;
- módulo de `vx`;
- `landing_tick`.

Essa é uma máquina de estados implícita com prioridade em `Player.animate`.

### Estados dos inimigos

Inimigos usam máquinas explícitas: `WALK`, `HURT`, `DYING`, `DEAD`, além de estados de
preparação, execução e recuperação de ataque. Cada `update` consulta `self.state` e chama
o método correspondente.

Um ataque de chefe normalmente segue:

```text
telegraph/preparação -> active/execução -> recover/recuperação -> patrulha
```

Isso dá legibilidade: o jogador vê o aviso antes da área perigosa existir.

## 6. Entrada e debounce

Entrada “segurada” e entrada “pressionada agora” não são a mesma coisa.

`Game._read_input` compara o valor atual com `*_was_down`:

```python
pressed = down and not was_down
was_down = down
```

Isso é **detecção de borda** ou **debounce**. Sem ela, segurar E por 20 quadros abriria e
fecharia uma porta várias vezes. O mesmo raciocínio vale para ataque, dash, tiro, ESC e
consumo de itens.

O movimento é diferente: esquerda/direita precisam ser lidas continuamente enquanto a
tecla estiver segurada.

O mouse passa primeiro por `input_adapter.py`:

- minigame ativo recebe o clique primeiro;
- menus recebem depois;
- gameplay transforma o clique em pedido de ataque.

Isso centraliza a prioridade e evita comportamento duplo.

## 7. Personagem: física, hitbox e animação

### 7.1 Posição e velocidade

`Player` guarda `x`, `y`, `vx` e `vy` como números possivelmente fracionários. O `Rect`
de colisão é criado sob demanda com valores arredondados.

- horizontal: velocidade se aproxima gradualmente do alvo;
- sem tecla: desaceleração leva `vx` de volta a zero;
- vertical: `vy = min(vy + GRAVITY, MAX_FALL_SPEED)`;
- depois a posição recebe a velocidade.

Essa integração é simples e baseada em quadros.

### 7.2 Arte não é hitbox

A spritesheet tem quadros 48 × 48, desenhados a 1,25×. A física continua usando corpo
lógico 32 × 48 e hitbox horizontal de 24 pixels, deslocada 4 pixels.

Separar arte e colisão permite aumentar visualmente Lia sem fazê-la bater em paredes
distantes ou deixar de passar por corredores projetados para a hitbox antiga.

### 7.3 Coyote time

Quando Lia toca o chão, `coyote_time` recebe 7. Ao sair da borda, ainda há alguns quadros
em que o pulo é aceito. Isso deixa o controle mais justo porque compensa atraso humano.

### 7.4 Jump buffer

Ao apertar pulo, `jump_buffer` recebe 7. Se o jogador apertar pouco antes de tocar o chão,
o pedido continua vivo e o pulo ocorre assim que `coyote_time` volta a existir.

Coyote time perdoa apertar **depois** da borda; jump buffer perdoa apertar **antes** do
chão.

### 7.5 Dash

Ao iniciar, a direção atual fica congelada em `dash_direction`, o temporizador recebe 8
quadros e `vx` vira ±12. O cooldown impede reinício imediato. Natação cancela dash.

### 7.6 Natação e oxigênio

Dentro de `Level.water_zones`:

- gravidade normal é substituída por afundamento suave;
- segurar subida aplica aceleração para cima;
- a cabeça usa um `head_rect` separado de 10 pixels;
- só cabeça submersa consome oxigênio;
- cabeça fora da água recarrega;
- oxigênio zero causa dano ambiental respeitando invencibilidade.

O mesmo método `_player_head_submerged` governa lógica de oxigênio e filtro azul. Isso
evita discrepância entre o que o jogador vê e o que a regra considera submerso.

### 7.7 Animação

A spritesheet contém 97 quadros. Constantes como `IDLE_FRAMES`, `WALK_START_FRAMES` e
`ATTACK_FRAMES` mapeiam intervalos. `_timed_frame` toca uma sequência uma vez;
`_loop_frame` usa módulo (`%`) para repetir.

A prioridade principal é:

```text
hurt > ranged > dash > swim > jump/fall > landing > walk > idle
```

O ataque corpo a corpo é aplicado depois por `CombatSystem.apply_attack_frame`, porque o
sistema de combate conhece o progresso exato do combo.

## 8. Colisões

### 8.1 Broad phase e resolução por eixo

Antes de testar colisões, `Level.solids_near` devolve apenas sólidos próximos usando um
índice espacial em chunks. Esse filtro é a broad phase.

O movimento é resolvido separadamente:

1. soma `vx` em X;
2. resolve paredes horizontais;
3. aplica gravidade;
4. soma `vy` em Y;
5. resolve teto e chão;
6. resolve rampas.

Separar eixos torna claro qual componente da velocidade zerar e para qual borda reposicionar
o corpo.

### 8.2 AABB

A maior parte das colisões usa `pygame.Rect.colliderect`, ou AABB: dois retângulos colidem
quando suas projeções horizontal e vertical se sobrepõem. É rápido e apropriado para tiles,
portas, pickups, inimigos e hitboxes.

### 8.3 Rampas por máscara

Uma rampa não pode ser aproximada por seu retângulo inteiro, porque o canto transparente
viraria parede. Tiles marcados com propriedade `rampa` fornecem uma máscara criada do canal
alpha da imagem. `Ramp` calcula o primeiro pixel sólido de cada coluna uma vez e usa esse
perfil para acompanhar a superfície.

Rampas sem máscara têm fallback com SAT, o **Separating Axis Theorem**. O algoritmo projeta
os polígonos nos eixos normais das arestas. Se algum eixo separar as projeções, não há
colisão. Se nenhum separar, o eixo de menor sobreposição fornece o MTV, menor vetor que
separa os corpos.

## 9. Combate

### 9.1 Interface comum dos inimigos

`CombatSystem` não precisa conhecer a classe concreta de cada inimigo. Ele usa uma interface
por comportamento:

- `enemy.alive`
- `enemy.rect`
- `enemy.take_hit(damage, ...)`
- opcionalmente `melee_vulnerable`
- opcionalmente `active_hazards()`
- opcionalmente `parryable_hazards()`

Isso é **polimorfismo por duck typing**: se o objeto oferece a interface esperada, o sistema
funciona com ele.

### 9.2 Combo corpo a corpo

Um clique inicia 16 quadros de animação, cada um mantido por 4 updates. Quatro índices são
janelas de impacto. Fora dessas janelas, `attack_box()` devolve `None`.

Para impedir dano repetido em todos os updates do mesmo soco, existe um conjunto de alvos
atingidos para cada hit: `_hit_targets[hit_index]`. A identidade do inimigo (`id(enemy)`)
é registrada após o primeiro dano.

O último golpe dá dano 2; os anteriores dão 1. Se o combo começou durante dash, o primeiro
impacto também ganha dano e alcance maiores.

### 9.3 Hitbox do ataque

`attack_box()` move e amplia o `Rect` da personagem na direção em que ela olha. O alcance
vem do tipo do impacto, não de comparar valores de dano. Isso desacopla “dano” de “distância”.

### 9.4 Ataque à distância

Depois da fase 1, R cria um `Projectile` na frente do peito da Lia. Ele guarda direção,
velocidade, poder e distância máxima. A cada quadro:

1. move;
2. reduz o alcance restante;
3. testa inimigos vivos;
4. ao colidir, tenta `take_hit`;
5. morre mesmo se o alvo rejeitar o dano;
6. se matou o inimigo, informa o inventário para gerar drop.

### 9.5 Parry

Parry reutiliza a hitbox do ataque normal. Antes de aplicar dano de hazards, o jogo consulta
`parryable_hazards`. Cada entrada fornece `(rect, cancel)`. Ao acertar:

- chama `cancel()` no projétil/ataque específico;
- cria clarão;
- dá invencibilidade;
- aplica hit-stop;
- inicia shake;
- devolve dano ao chefe.

A ordem “parry antes de dano” é essencial. Invertê-la faria Lia aparar e sofrer no mesmo
quadro.

### 9.6 Dano, escudo e morte

`Game._lose_life` é o núcleo comum:

1. escudo absorve primeiro;
2. escolhe VFX conforme o local;
3. reduz vida sem deixá-la negativa;
4. aplica invencibilidade;
5. cancela combo;
6. se vida chegou a zero, entra em `GAME_OVER`;
7. senão, inicia animação de dano.

Contato comum causa 0,5 coração; chefe causa 1. Cair no vazio usa `respawn`, mostra a pose
de morte e só depois reposiciona no checkpoint. Dano comum não teleporta Lia.

## 10. Inimigos e chefes

### 10.1 Herança nos inimigos comuns

`GroundEnemy` implementa posição, vida, dano, morte e respawn. `PausingGroundEnemy` adiciona
patrulha com pausa nas bordas e desenho compartilhado.

Classes concretas configuram constantes:

- `Slime`: patrulha contínua;
- `CrystalStag`: patrulha com pausas;
- `PossessedStudent`: mesma estrutura, outros números/arte;
- `JanitorGuardian`: maior, mais lento e resistente.

Isso é herança usada para compartilhar algoritmo e permitir parâmetros diferentes.

### 10.2 Chefes especializados

Chefes maiores têm máquinas próprias porque ataques e animações são muito diferentes.

- `AncientGolem`: slam com ondas sequenciais, investida e pedregulho balístico;
- `SlimeKing`: esmagar/onda e cisão que invoca `SmallSlime`;
- `Librarian`: ataques de silêncio, tomos/lâminas e escudo;
- `Specimen`: jato, investida e casulo/esporos;
- `DarkWraith`: flutuação, antecipação e avanço.

O Golem, por exemplo, começa `DORMANT`. Ao acordar, patrulha. Seu padrão de ataque é uma
tupla determinística, mas os intervalos têm aleatoriedade. No slam, o impacto nasce em um
quadro específico da arte e alimenta uma fila de ondas com atrasos. No arremesso, a pedra
usa velocidade horizontal, velocidade vertical e gravidade, formando uma parábola.

### 10.3 Por que `getattr` aparece tanto

Nem todo inimigo possui escudo, hazard ou capacidade de virar para o jogador. Em vez de
forçar métodos vazios em todos, o código consulta capacidades opcionais:

```python
face_player = getattr(enemy, "face_player", None)
if face_player:
    face_player(player_x)
```

Essa decisão reduz acoplamento, mas exige nomes de interface bem estáveis e bons testes.

## 11. Level e mapas do Tiled

### 11.1 Divisão de responsabilidade

- `TiledMap` entende XML/TMX, tilesets, GIDs, camadas e objetos.
- `Level` interpreta esses dados como conceitos do jogo.
- `Game` executa as regras da sessão usando o `Level` pronto.

Exemplo: `TiledMap` devolve um objeto cujo tipo normalizado é `porta`. `Level._make_doors`
o converte para `{"rect": ..., "target": ...}`. `InteractionSystem.use_doors` decide o que
acontece quando E é pressionado perto dele.

### 11.2 Pipeline do mapa

```text
arquivo .tmx
  -> XML ElementTree
  -> tilesets .tsx e imagens
  -> camadas de tiles
  -> colisões / rampas / foreground / tiles animados
  -> grupos de objetos
  -> entidades por tipo
  -> Level cria portas, inimigos, NPCs, perigos, água etc.
```

### 11.3 GID e flags

No Tiled, um GID pode carregar bits altos indicando espelhamento horizontal, vertical ou
diagonal. O leitor mascara os bits para achar o tile real e usa os bits restantes para
gerar/cachar a imagem orientada.

### 11.4 Formatos de camada

O leitor aceita:

- CSV;
- Base64 sem compressão;
- Base64 + zlib;
- Base64 + gzip;
- elementos `<tile>` sem encoding.

Base64 comprimido é decodificado, descompactado e interpretado como inteiros unsigned de
32 bits little-endian.

### 11.5 Objetos do Tiled

Objetos da camada `Entidades` usam tipo/classe e propriedades. Exemplos:

- `spawn`
- `checkpoint`
- `inimigo`
- `porta`
- `cientista`
- `pesquisa`
- `artefato`
- `agua`
- `perigo`
- `lago_lava`
- `elevador_lab`
- `neblina`
- `caixa_energia`

Essa abordagem é **data-driven**: muitos ajustes de conteúdo não exigem alterar Python,
apenas mover ou configurar objetos no editor.

### 11.6 Chunks e culling

Desenhar ou testar cada tile de um mapa grande em todos os 60 quadros desperdiçaria tempo.
O mapa distribui tiles em chunks. Na hora de desenhar, calcula quais chunks cruzam a câmera
e visita apenas esses.

O chão tem índice semelhante para colisão. Assim a Fase 3 não compara Lia com mais de mil
retângulos duas vezes por quadro.

**Culling** significa ignorar o que não pode afetar a imagem/entidade atual.

### 11.7 Tiles maiores que a grade

Uma casa pode ter imagem 128 × 128 em grade 32 × 32. O leitor ancora a arte na base esquerda,
como o Tiled, e guarda o tamanho real para não descartá-la cedo na borda da câmera.

## 12. Câmera e renderização

A câmera guarda deslocamentos `camera_x` e `camera_y`. Para converter mundo em tela:

```text
screen_x = world_x - camera_x
screen_y = world_y - camera_y
```

O alvo horizontal inclui `CAMERA_LOOK_AHEAD`, dando visão à frente. A câmera não salta para
o alvo; interpola uma fração da diferença, produzindo suavização.

Em arena de chefe, a câmera tenta enquadrar a arena, e a posição da Lia também é limitada
às bordas enquanto o chefe vive.

Parallax multiplica o deslocamento por fator menor que 1; fundos distantes parecem mover
mais devagar. Shake soma um deslocamento aleatório temporário apenas durante o desenho do
mundo e o remove antes da HUD, mantendo a interface legível.

Quando `CAMERA_ZOOM == 1`, o mundo é desenhado diretamente no destino. Um buffer adicional
só existe quando há zoom real. Menus usam um snapshot escurecido, evitando redesenhar um
mundo congelado 60 vezes por segundo.

## 13. Inventário e progressão

`game_data.ITEM_DEFS` é a fonte de verdade dos itens. Há três categorias:

- `consumable`: usa por tecla e altera vida/escudo;
- `quest`: drop garantido de chefe e requisito de fase;
- `tool`: ferramenta persistente, não consumida pelas teclas.

O inventário guarda contagens entre fases e salas. Drops no chão pertencem ao mapa atual e
são apagados em transições.

Chefes em `BOSS_DROP_TABLE` geram item garantido. Inimigos comuns consultam
`ENEMY_DROP_TABLE` e sorteiam com `random.random()`.

O fim da fase verifica, nesta ordem:

1. todas as pesquisas coletadas;
2. microscópio montado quando exigido;
3. itens de chefe obrigatórios;
4. transição de vila, conclusão total ou próxima fase.

Ao terminar a escola, o ataque à distância é desbloqueado antes do save.

## 14. Interações, diálogos e puzzles

### 14.1 Prioridade das interações

Ao apertar E, `InteractionSystem.handle_interactions` tenta uma sequência e para no primeiro
sucesso:

```text
porta -> elevador secreto -> NPC -> caixa de energia -> bancada -> painel -> botão
```

Isso evita duas ações no mesmo quadro quando áreas se sobrepõem.

### 14.2 Salas secundárias

Ao entrar em uma sala, `Game` preserva:

- o objeto `Level` principal;
- posição da Lia;
- posição da câmera.

Cria um novo `Level` para a sala. Ao sair, restaura o objeto original, então inimigos,
pesquisas e estado do corredor continuam como estavam.

### 14.3 Diálogos

Uma sequência é normalizada para pares `(falante, texto)`. A primeira fala abre a caixa;
as demais ficam numa fila. Ao pressionar avanço:

- se o texto ainda está surgindo, revela tudo;
- se já terminou e há fila, abre a próxima fala;
- se acabou a fila, fecha.

### 14.4 Puzzles

`PuzzleSystem` mantém o progresso canônico. `MinigameManager` apenas hospeda a tela ativa
e devolve resultados.

Os dicionários de slots e fios são passados por referência. Fechar com ESC não precisa
copiar o estado: o minigame já alterou o mesmo objeto possuído pelo `PuzzleSystem`.

O microscópio exige coleta das peças, montagem por arraste e marca
`microscope_assembled`. A caixa de energia exige chave de fenda antes de remover parafusos
e conectar fios.

## 15. Save e persistência

O save é JSON versão 1. Ele inclui:

- fase;
- checkpoint;
- vidas;
- escudo;
- inventário;
- ataque à distância desbloqueado;
- pesquisas coletadas.

`decode_progress` valida tudo antes de `Game` alterar a sessão:

- versão exata;
- fase permitida;
- coordenadas numéricas e finitas;
- limites seguros;
- itens conhecidos;
- contagens inteiras não negativas;
- booleano real para habilidade.

A escrita é **atômica**:

1. serializa os dados;
2. escreve em arquivo temporário na mesma pasta;
3. fecha e descarrega;
4. substitui o save antigo;
5. remove temporário restante.

Se houver falha antes da substituição, o save antigo não fica pela metade.

O save não guarda tudo. Drops no chão, timers de ataque, projéteis e efeitos são transitórios.
Essa distinção reduz formato, acoplamento e bugs de retomada.

## 16. Áudio

`audio.py` é uma fachada; `audio_backend.py` contém implementações.

- `SilentAudioBackend`: permite importar/testar sem áudio real;
- `PygameMixerAudioBackend`: procura arquivos e usa `pygame.mixer`.

O núcleo chama `audio.play_sfx("jump")`, sem saber extensão ou plataforma. Arquivo ausente
não derruba o jogo. A música atual é cacheada para uma chamada por quadro não reiniciar a
faixa sempre.

Volumes, escala de shake e velocidade de texto são limitados a intervalos válidos e salvos
em `audio_settings.json`.

Isso exemplifica **baixo acoplamento** e **injeção de dependência**: o ponto de entrada
escolhe o backend.

## 17. Assets, cache e desempenho

`Assets` carrega e prepara imagens. O objetivo é não fazer I/O, recorte ou escala pesada
dentro do loop principal.

Exemplos de cache:

- sprites viradas por `sprites.flipped`;
- fontes por `hud.get_font` com `lru_cache`;
- brilho de projétil;
- variantes orientadas de tile;
- máscara de rampa;
- superfícies do rastro de dash;
- overlay subaquático;
- snapshot de menu;
- peças de puzzle já escaladas.

O princípio é: calcular uma vez quando o resultado depende apenas de entradas estáveis;
reutilizar nos próximos quadros.

## 18. Para que serve cada módulo

| Módulo | Responsabilidade que você deve saber explicar |
| --- | --- |
| `main.py` | Adapta hooks do Pygame Zero ao núcleo desktop. |
| `main_web.py` | Reproduz o loop em Pygame assíncrono para WASM. |
| `settings.py` | Constantes físicas, resolução e caminhos absolutos. |
| `game_data.py` | Estados, balanceamento, itens, diálogos e tabelas estáticas. |
| `game.py` | Orquestra sessão, ordem de update/draw, câmera, dano e progresso. |
| `input_adapter.py` | Tela lógica, teclado web e prioridade do mouse. |
| `player.py` | Movimento, habilidades, hitbox e animação da Lia. |
| `combat.py` | Combo, hitboxes, projéteis, stomp, parry e contato. |
| `projectile.py` | Entidade simples do tiro da Lia. |
| `level.py` | Converte mapa em mundo jogável e atualiza entidades. |
| `tiled_map.py` | Lê TMX/TSX, imagens, camadas, objetos e chunks. |
| `ramp.py` | Colisão de rampas por máscara e fallback SAT. |
| `plataform.py` | Plataforma fixa/móvel e seu deslocamento por período. |
| `enemy_common.py` | Base de dano, morte, respawn e patrulha compartilhada. |
| `enemy.py` | Tipos comuns e ponto único de importação dos inimigos. |
| `enemy_slime_king.py` | Máquina de estados do Rei Slime. |
| `enemy_librarian.py` | Máquina de estados do Bibliotecário. |
| `enemy_specimen.py` | Máquina de estados do Espécime. |
| `enemy_ancient_golem.py` | Máquina de estados e VFX do Golem. |
| `enemy_wraith.py` | Movimento flutuante e ataque da entidade sombria. |
| `enemy_summons.py` | Slimes temporários invocados pelo chefe. |
| `inventory.py` | Contagens, uso, drops e ferramentas. |
| `interactions.py` | Portas, elevador, NPCs e fila de diálogo. |
| `puzzles.py` | Estado persistente dos puzzles e integração dos minigames. |
| `minigame.py` | UI e regras de arraste do microscópio/caixa de energia. |
| `dialogue.py` | Caixa, retrato, quebra e revelação gradual do texto. |
| `hint.py` | Dica modal com foco visual. |
| `cutscene.py` | Prólogo ilustrado e transições entre imagens. |
| `elevator_cutscene.py` | Animação modal antes da troca de sala. |
| `progress.py` | Validação e gravação atômica do save. |
| `audio.py` | Fachada, volumes e preferências. |
| `audio_backend.py` | Implementações silenciosa e Pygame Mixer. |
| `assets.py` | Carregamento e preparação de imagens. |
| `sprites.py` | Helpers compartilhados e caches de sprites. |
| `vfx.py` | Instâncias efêmeras de efeitos visuais. |
| `hud.py` | Vidas, inventário, oxigênio, habilidades e mensagens. |
| `fog.py` | Barreira visual/colisível liberada por evento externo. |
| `render_state.py` | Snapshot tipado dos dados que `Level.draw` precisa. |

## 19. Conceitos de programação presentes

| Conceito | Exemplo real |
| --- | --- |
| Encapsulamento | `InventorySystem.use_item` protege regras de consumo. |
| Composição | `Game` possui sistemas especializados. |
| Herança | inimigos comuns herdam `GroundEnemy`. |
| Polimorfismo | combate usa `alive`, `rect` e `take_hit` em classes diferentes. |
| Máquina de estados | estados globais, personagem e chefes. |
| Data-driven design | objetos do Tiled e tabelas em `game_data`. |
| Adapter | `KeyboardState`, `LogicalScreen`, entradas desktop/web. |
| Facade | módulo `audio` simplifica backends. |
| Dependency injection | entrada escolhe backend; sistemas recebem `game`. |
| Cache/memoization | `lru_cache`, surfaces e chunks reutilizados. |
| Early return | dispatcher e validações encerram trabalho desnecessário. |
| Invariante | asserts de balanceamento em `game_data`. |
| Validação defensiva | save rejeitado antes de alterar sessão. |
| Broad/narrow phase | chunks filtram; Rect/máscara confirmam colisão. |
| Separação update/draw | regra muda em update, draw apenas representa. |

## 20. Estado persistente versus transitório

Esta distinção é uma excelente resposta de prova oral.

| Dado | Sobrevive a fase? | Vai para save? | Motivo |
| --- | --- | --- | --- |
| inventário | sim | sim | progresso do jogador |
| vida/escudo | sim | sim | estado relevante de retomada |
| ranged desbloqueado | sim | sim | habilidade permanente |
| checkpoint | sim | sim | ponto de retomada |
| pesquisas | na fase | sim | requisito de avanço |
| drops no chão | não | não | pertencem à instância do mapa |
| projéteis | não | não | existem poucos quadros |
| combo/timers | não | não | ação em andamento não precisa retomar |
| VFX | não | não | apenas apresentação |
| posição da câmera | preservada em sala | não | conforto local, não progresso |
| estado do puzzle | entre salas da fase | atualmente não | sessão da fase, não schema v1 |

## 21. Perguntas prováveis do professor — com respostas fortes

### 1. Qual biblioteca foi usada?

Pygame 2.6.1 para janela, superfícies, áudio, teclado e colisões. Pygame Zero fornece o
loop e hooks no desktop. pygbag empacota a entrada Pygame assíncrona para WebAssembly.

### 2. Onde fica o loop principal?

No desktop, o loop pertence ao Pygame Zero, que chama `update` e `draw` de `main.py`. Na
web, ele está explícito em `main_web.main`. Ambos chamam a mesma instância de `Game`.

### 3. Por que separar update e draw?

`update` muda estado e executa regras; `draw` representa o estado. A separação evita que
quantidade de desenhos altere a jogabilidade e facilita testes sem tela.

### 4. O que `dt` representa?

É o tempo desde o quadro anterior, em segundos. O projeto o usa em elementos como animação
de tiles e tempo visual de fundo. Vários timers de gameplay ainda são contados em quadros,
assumindo 60 FPS. Isso é simples e determinístico, mas uma evolução seria converter mais
regras para segundos se fosse necessário suportar FPS muito variável.

### 5. Como uma tecla vira movimento?

O adaptador fornece atributos booleanos. `Game` chama `Player.read_controls`, que calcula
direção como direita menos esquerda, atualiza `vx` por aceleração, define direção visual,
registra pedido de pulo; depois `Game.move_player` soma velocidades e resolve colisões.

### 6. Como vocês evitam múltiplas ações ao segurar uma tecla?

Guardando o estado do quadro anterior. A ação ocorre apenas quando a tecla está pressionada
agora e não estava antes. Movimento é a exceção intencional porque precisa ser contínuo.

### 7. Como funciona a colisão?

Tiles e entidades usam AABB com `pygame.Rect`; o movimento é resolvido por eixo. Antes,
chunks filtram sólidos próximos. Rampas usam máscara de pixels, com SAT como fallback.

### 8. Por que a hitbox da Lia é menor que a imagem?

Transparência e escala visual não devem ampliar o corpo físico. A hitbox acompanha o corpo,
enquanto a imagem é ancorada pelo centro e pelos pés.

### 9. Como o combo não acerta 4 vezes no mesmo frame visual?

Só quatro índices específicos da animação geram hitbox. Para cada impacto, um conjunto
registra cada inimigo já atingido e bloqueia repetição durante aquela janela.

### 10. Como o parry não causa dano e recebe dano ao mesmo tempo?

A checagem de parry roda antes da checagem de hazards. Ao acertar, o callback cancela o
hazard, então a etapa seguinte já não encontra a ameaça ativa.

### 11. Como um inimigo novo entra no combate?

Ele precisa expor `rect`, `alive` e `take_hit`; opcionalmente `active_hazards`,
`parryable_hazards`, `melee_vulnerable` e `face_player`. Depois o `Level` precisa criá-lo a
partir do tipo correspondente no mapa ou de uma arena.

### 12. Por que usar máquina de estados nos chefes?

Cada estado tem regra, duração e animação claras. Preparação, ataque e recuperação ficam
sincronizados e testáveis, sem dezenas de booleanos incompatíveis.

### 13. O mapa é só uma imagem?

Não. O TMX contém camadas visuais, colisão, tiles animados e objetos tipados. O leitor
transforma isso em dados; `Level` transforma os dados em entidades do jogo.

### 14. O que é culling?

Ignorar tiles/objetos fora da região relevante. O desenho visita só chunks visíveis, e a
física consulta sólidos próximos. Isso reduz custo conforme o mapa cresce.

### 15. Como a câmera funciona?

Ela segue um alvo com look-ahead e suavização, limitada ao mundo. Coordenadas de tela são
coordenadas do mundo menos câmera. Em chefes, muda o alvo para enquadrar a arena.

### 16. O que persiste ao entrar numa sala?

O `Level` principal e a posição/câmera ficam guardados. Um novo `Level` representa a sala.
Ao sair, o original é restaurado, mantendo inimigos e coletas como estavam.

### 17. Como o save evita corrupção?

Valida todo o conteúdo antes de aplicar. Na escrita, gera um temporário e só depois o
substitui atomicamente no lugar do save anterior.

### 18. Por que o áudio tem backend?

Para o núcleo depender de uma API estável, não do Pygame Zero ou da plataforma. Nos testes
pode usar backend silencioso; desktop e web configuram Pygame Mixer.

### 19. Onde há herança e onde há composição?

Herança nos inimigos comuns. Composição em `Game`, que contém sistemas. Composição é a
estrutura dominante porque combate, inventário e puzzles não são “tipos de Game”; são
partes colaboradoras.

### 20. Como vocês testam?

Há testes unitários de regras (combate, save, inventário), testes de caracterização para
preservar comportamento, testes de mapas reais, hashes/pixels para renderização e um
benchmark determinístico que percorre cenários.

### 21. O que você melhoraria?

Uma resposta honesta: reduzir `Game` e `Level`, que ainda concentram muita coordenação;
padronizar timers entre quadros e segundos; tornar o schema de save evolutivo para puzzles;
e alinhar as referências de testes sempre que mapas forem alterados intencionalmente.

### 22. Por que há `TYPE_CHECKING`?

Permite anotações de tipo referindo-se a `Game` sem importar `Game` em tempo de execução,
evitando importação circular: `Game` importa o sistema, e o sistema só precisa do tipo para
ferramentas estáticas.

### 23. Por que usar propriedades como `rect`, `alive` e `dashing`?

Elas apresentam valores derivados como atributos simples. `rect` sempre reflete `x/y`;
`alive` deriva do estado; `dashing` deriva do timer. Isso evita duplicar dados que poderiam
ficar inconsistentes.

### 24. Por que alguns métodos começam com `_`?

É convenção Python para detalhe interno. `Game.update` e `Game.draw` são a interface pública;
`_update_camera` e `_check_hazards` são etapas que a própria classe coordena.

### 25. O código está 100% passando nos testes?

No estado atual, não: 115 de 118 passam. As falhas são referências afetadas pelas alterações
atuais dos mapas: plataforma/arena do Golem na vila, posição do tutorial do Cadu em relação
ao primeiro slime e hashes visuais de mapas reais. É melhor responder isso com precisão do
que afirmar que tudo passa.

## 22. Os três testes que falham hoje

Comando executado:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Falhas observadas:

1. `test_village_map_builds_golem_and_locked_arena`
   - o teste esperava plataforma `(5600, 480, 576, 32)`;
   - o mapa atual produz `(6367, 288, 671, 32)`.
2. `test_cadu_teaches_attack_before_the_first_village_slime`
   - a posição/ordem atual dos objetos no mapa não satisfaz a regra testada.
3. `test_real_maps_match_camera_references`
   - hashes de pixels da renderização mudaram com os mapas alterados.

Como os arquivos `vila.tmx`, `fase1_escola.tmx` e testes relacionados estão modificados no
working tree, não se deve “corrigir” automaticamente sem decidir se o mapa novo ou a referência
antiga é a verdade desejada.

## 23. Plano de estudo curto até quarta

### Sábado — 35 minutos: arquitetura

1. Leia as seções 1 a 6.
2. Abra `main.py` e siga até `Game.update`.
3. Fale em voz alta o resumo da seção 1 sem ler.
4. Desenhe de memória o diagrama da seção 3.

Meta: explicar onde começa o programa e quem é responsável por cada regra.

### Domingo — 40 minutos: movimento e desenho

1. Leia as seções 7, 8 e 12.
2. Abra `player.py`: `read_controls`, `apply_gravity`, `try_jump`, `animate`.
3. Abra `game.py`: `_update_playing`, `move_player`, `_update_camera`, `draw`.
4. Explique uma caminhada, um pulo e uma queda quadro a quadro.

Meta: responder física, colisão, animação, câmera e renderização.

### Segunda — 45 minutos: combate e inimigos

1. Leia as seções 9 e 10.
2. Abra `combat.py` na ordem dos métodos.
3. Escolha um chefe, de preferência o Golem, e desenhe seus estados.
4. Responda perguntas 9, 10, 11 e 12 sem consultar.

Meta: explicar combo, parry, dano, polimorfismo e máquina de estados.

### Terça — 50 minutos: mapas, persistência e simulado

1. Leia as seções 11, 13 a 17 e 20.
2. Siga um objeto `porta`: TMX -> `TiledMap` -> `Level` -> `InteractionSystem`.
3. Siga um item de chefe: morte -> drop -> coleta -> requisito -> save.
4. Responda as 25 perguntas como se o professor estivesse na frente.
5. Marque respostas em que travou e releia só essas partes.

Meta: integrar todos os módulos e praticar fala, não leitura passiva.

### Quarta — 15 minutos: revisão antes da apresentação

1. Use `RESUMO_APRESENTACAO.md`.
2. Repita o resumo de 60 segundos.
3. Repita os três fluxos: frame, ataque e mapa.
4. Lembre os números: 38 módulos, 118 testes, 115 passando.

## 24. Exercícios que provam compreensão

Não basta reler. Faça estes exercícios oralmente:

1. Se `GRAVITY` dobrar, quais comportamentos mudam e quais não mudam?
2. Se remover `attack_was_down`, o que acontece ao segurar F?
3. Se `check_enemy_attack_hazards` rodar antes de `check_parries`, qual bug aparece?
4. Se a arte da Lia dobrar sem mudar a hitbox, o que muda visualmente e fisicamente?
5. Se um tile grande for descartado usando apenas o tamanho da grade, que artefato visual aparece?
6. Se o save for aplicado campo por campo antes de terminar a validação, o que um JSON inválido pode causar?
7. Se entrar numa sala sem preservar `_base_level`, o que acontece com os inimigos do corredor?
8. Se desenhar HUD antes do shake e aplicar shake à tela inteira, qual efeito indesejado aparece?
9. Como adicionar um novo consumível de cura e escudo usando a estrutura atual?
10. Como adicionar um novo objeto de Tiled chamado `terminal` e uma interação com E?

Uma resposta forte sempre aponta o módulo, o dado afetado e a cadeia de chamadas.

## 25. Ordem de leitura recomendada do código

Não leia em ordem alfabética. Use esta sequência:

1. `settings.py`
2. `game_data.py` até as regras de combate
3. `main.py`
4. `input_adapter.py`
5. `game.py`: `__init__`, `update`, `_update_playing`, `draw`
6. `player.py`
7. `combat.py`
8. `enemy_common.py` e `enemy.py`
9. um chefe completo
10. `level.py`: `__init__`, fábricas, `update`, `draw`
11. `tiled_map.py`: `__init__`, `_read_layers`, `_read_tile_layer`, `entities`, `draw`
12. `interactions.py`
13. `inventory.py`
14. `puzzles.py` e partes relevantes de `minigame.py`
15. `progress.py`
16. `audio.py` e `audio_backend.py`
17. módulos visuais auxiliares

Ao ler um método, faça quatro perguntas:

1. Quem chama?
2. Que estado ele lê?
3. Que estado ele altera?
4. O que precisa continuar verdadeiro depois dele?

Se você souber essas quatro respostas, entendeu o método; não apenas reconheceu as linhas.
