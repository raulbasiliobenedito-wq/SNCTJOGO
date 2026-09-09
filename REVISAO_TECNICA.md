# Echoes of Life — Revisão técnica completa
**Data:** 08/09/2026 · **Escopo:** 25 arquivos `.py` (11.629 linhas), 204 PNGs, 7 mapas `.tmx` + 8 `.tsx`, docs e site.
**Método:** leitura integral do código + execução real do jogo (pygame 2.6.1, SDL dummy, 1920×1080) com `cProfile`, medição de RSS, `pyflakes`/`radon`/`vulture`, e parsing dos `.tmx`/`.tsx`/cabeçalhos PNG.

> Tudo abaixo foi **medido ou reproduzido**, não estimado. Onde a medição foi feita num container Linux headless (blits por software), os números absolutos podem diferir da sua máquina, mas as **proporções entre as opções** se mantêm.

---

## 1. Diagnóstico geral

O projeto está num estado bem melhor do que o tamanho sugere. A arquitetura tem decisões maduras: canvas lógico fixo com o mesmo código rodando desktop e WASM, parser TMX próprio sem dependência externa, indexação espacial por chunks (tanto no desenho quanto na colisão), sistema de áudio à prova de arquivo faltando, e um padrão consistente de "asset opcional" (`if path.exists()` → cai num desenho por código). Só **5 funções** em 11.629 linhas estão genuinamente mortas, e os mapas estão estruturalmente íntegros — nenhum objeto do Tiled sem as propriedades que o código espera. Isso é raro num projeto solo de muitas sessões.

O problema não é a arquitetura. São três outras coisas:

**(a) Valores de depuração ficaram no código e desligaram o jogo como jogo.** `STARTING_LIVES = 1000` e `STANDARD_ATTACK_POWER = 100` estão em `game.py`. Com isso, a Lia é matematicamente invencível (2.000 toques de mob para morrer) e **todos os chefes morrem em um único golpe** — Rei Slime, Bibliotecário e Espécime têm 12 de vida, o Dragão 16. Todo o trabalho de máquina de estados de chefe, telégrafo de ataque, parry, fase de imunidade a corpo a corpo e barra de vida está tecnicamente correto e **nunca é exercido em jogo**. Este é, de longe, o item mais importante da lista.

**(b) O gargalo de performance não é o que a documentação supõe.** Medido com `cProfile`: **68% do tempo de quadro são blits**, e a maior parte deles não é cenário — são **três operações de tela cheia que produzem sempre o mesmo resultado**. Removendo-as, o tempo por quadro cai de 11,7 ms para 5,5 ms na Fase 3 e de 10,6 ms para 4,8 ms na Fase 1. É um ganho de **53–61%** com cerca de 30 linhas mexidas.

**(c) O consumo de memória está fora de escala.** O processo fica em **600 MB de RSS** logo depois do `Game()`. **380 MB (63%) são os 48 quadros de neblina**, redimensionados para 1920×1080 no carregamento — e a neblina só existe na Fase 1. Mantidos no tamanho nativo (480×270), seriam 23,7 MB.

Um quarto tema atravessa tudo: **duas linguagens visuais convivem no jogo**. Metade dos assets é pixel art limpa (0,1–0,3 bytes/pixel comprimido: `village/`, `fog/`, `enemies/`, tilesets de `maps/`); a outra metade é arte renderizada com anti-aliasing e gradiente (>1,0 byte/pixel: `dialogue_box.png`, `escola_sheet.png`, `hospital.png`, `tiles/platform*.png`, `microscope_*.png`, `door.png`). O `dialogue_box.png` (2,2 MB, 1536×1024) ainda é **esticado com distorção de 52%** ao ser desenhado — exatamente a classe de bug visual que você já pegou antes, e que continua viva aqui.

E uma observação de conteúdo que muda a leitura da Fase 1: no `fase1_escola.tmx`, a camada `Colisão` tem **774 tiles de grama da vila contra 200 tiles do tileset da escola**, e o `Fundo` tem 1.076 contra 596. Hoje a "Fase 1 — Escola" é, visualmente, um campo de grama com pedaços de escola. O `PLANO_FASE1.md` marca a repintura como pendente; o guia de apresentação supõe que ela avançou. Ela avançou pela metade, e com o tileset errado.

---

## 2. Problemas concretos, por prioridade

### P0 — Quebram o jogo como jogo

#### 2.1 `game.py:44-45,125` — valores de depuração de vida e dano
```python
STARTING_LIVES = 1000
MAX_LIVES = 1000
STANDARD_ATTACK_POWER = 100
```
Consequências medidas:
- Nenhum inimigo sobrevive a um golpe. `Slime.HEALTH=2` … `Dragon.HEALTH=16`, todos < 100.
- `DASH_ATTACK_POWER = 2`, `COMBO_FINISHER_POWER = 2` e `PARRY_DAMAGE = 3` são **menores** que o golpe padrão. O 4º hit do combo e o parry são **punições**, não recompensas.
- `_attack_box()` decide o alcance com `reach = DASH_ATTACK_REACH if self.attack_power > STANDARD_ATTACK_POWER` → com 100 isso nunca é verdade; o golpe de dash sai com 46 px em vez dos 60 px pretendidos (**medido**).
- `hud._draw_hearts` desenha um coração por vida: **1.000 corações por quadro, ocupando 50.000 px numa tela de 1920 px**.
- O menu de fim de jogo, a pose de morte, o `death_sound`, a mensagem `MOTIVATION` — todo o fluxo de derrota é inalcançável.

#### 2.2 `game.py` — `message_timer = 0` torna a caixa de mensagem invisível
`hud.draw_hud` só desenha a mensagem com `if message_timer:`. Oito pontos de `game.py` setam `self.message` junto com `self.message_timer = 0`:

| Linha | O que deveria aparecer | Aparece? |
|---|---|---|
| 1245 (`load_level`) | subtítulo da fase ("A primeira pergunta pode mudar o mundo.") | **não** |
| 2110 (`_collect_drops`) | "Item obtido: Gororoba" | **não** |
| 2214 (`_collect_artifacts`) | "Achado: …" | **não** |
| 2357 (`_collect_research`) | "Parte da pesquisa obtida: …" | **não** |
| 2444/2449 (`_advance_level_if_ready`) | "Encontre todas as partes da pesquisa antes de avançar." | **não** |

O caso 2444 é o pior: o jogador chega no fim da fase, é **empurrado 60 px para trás sem nenhuma explicação na tela**, repetidamente. Verificado por instrumentação: `hud._draw_message` nunca é chamado num playthrough automatizado das 4 fases. Outros pontos do mesmo arquivo usam `90` ou `130` — é inconsistência, não intenção.

#### 2.3 `elevator_cutscene.py:57` — nome de arquivo errado
```python
FRAME_PATH = ASSET_DIR / "cutscenes" / "elevador_lab_moldura.png"
```
O arquivo no disco é `elevador_la**v**_moldura.png` (1920×1080, 18 KB). Como o carregamento é opcional (`if path.exists()`), falha em silêncio: **a moldura do elevador nunca é desenhada** e a arte fica órfã. É a única referência realmente quebrada do projeto inteiro.

#### 2.4 `maps/escola_tileset_64x64.tsx` — `tilecount` errado
```xml
<tileset ... tilecount="480" columns="8">
  <image source="escola_tileset_TILED_64x64_FINAL.png" width="256" height="480"/>
```
256×480 com tiles de 32×32 = **120 tiles**, não 480. `TiledMap._load_tileset` calcula `last_gid = first_gid + tilecount - 1` → esse tileset declara possuir os GIDs **1..480**, invadindo as faixas de `fase3_pesquisa.tsx` (121–280), `aderecos_vila.tsx` (281–292) e `chao_vila.tsx` (293–308).

Hoje não quebra por acidente: `_tileset_for_gid` itera `reversed(self.tilesets)` e encontra o tileset certo primeiro. Mas **qualquer tileset novo importado depois** cairá na faixa 309–480 e será resolvido para o tileset da escola, com `local_id` até 479 num atlas de 120 tiles → `subsurface()` fora dos limites → **crash no carregamento do mapa**. Conserto: `tilecount="120"`.

---

### P1 — Performance e memória (todos medidos)

#### 2.5 `game.py:2758-2790` — três operações de tela cheia por quadro

Perfil da Fase 3, 300 quadros: 642.924 blits (**2.143 por quadro**), 2,84 s dos 4,18 s totais.

| Operação | Custo | Por quê é desperdício |
|---|---|---|
| `real_surface.fill((6,14,29))` | ~0,8 ms | `_blit_zoomed_world` cobre a tela inteira logo depois |
| `surface.fill((6,14,29))` | ~0,8 ms | `_draw_background` cobre a tela inteira logo depois |
| `surface.blit(overlay, (0,0))` (SRCALPHA 1920×1080) | ~4,7 ms | é sempre a **mesma cor constante** sobre um fundo opaco |

Medição controlada (250 quadros cada, mesmo hardware):

| | Fase 1 | Fase 2 | Fase 3 |
|---|---|---|---|
| baseline | 10,58 ms | 9,99 ms | 11,67 ms |
| removendo os 2 `fill()` | 8,65 ms | 6,00 ms | 7,21 ms |
| **+ fundo pré-tingido** | **4,79 ms** | **3,87 ms** | **5,52 ms** |
| ganho total | **−54,7%** | **−61,3%** | **−52,7%** |

O overlay é matematicamente eliminável: como o fundo é opaco e cobre a tela toda, e nada é desenhado entre o fundo e o overlay, compor a cor no próprio `Surface` de fundo **no carregamento** produz um resultado pixel-a-pixel idêntico. Você já fez essa conta uma vez em `_combine_overlay_colors` — falta dar o último passo e aplicar a cor no fundo em vez de num overlay por quadro.

#### 2.6 `game.py:_load_fog_frame_sequence` — 380 MB de RAM

Distribuição real medida (RSS total: **600 MB**):

| grupo | MB | superfícies |
|---|---:|---:|
| `fog_frames` (24 × 1920×1080) | 189,8 | 24 |
| `fog_frames_corpo` (24 × 1920×1080) | 189,8 | 24 |
| overlays de cor | 55,4 | 7 |
| espelhos de fundo | 32,5 | 6 |
| backgrounds | 17,3 | 3 |
| dragon_sprites | 11,9 | 19 |
| vinheta do Hint | 7,9 | 1 |
| *todo o resto (inimigos, chefes, VFX, HUD…)* | *~11* | *~600* |

Três coisas de uma vez: **(a)** os quadros nascem em 480×270 e são ampliados 4× no carregamento — guardá-los nativos custa 23,7 MB e `pygame.transform.scale` na hora de desenhar é 1 chamada por quadro; **(b)** a neblina só existe na Fase 1, mas é carregada sempre (candidato óbvio a *lazy loading*); **(c)** dos 7 overlays de cor, três (`background_filter`, `university_filter`, `underground_filter`) estão comentados como "mantidas apenas como referência/compat" — são **24 MB de superfícies mortas**.

`Game()` leva **2,68 s** só carregando assets, com tudo de todas as fases carregado de uma vez.

#### 2.7 Alocação de `Surface` dentro do laço de desenho
Cada um destes cria superfícies novas **todo quadro** (pressão de GC + custo de alocação):

- `fog.py:_draw_procedural` — `pygame.Surface(visible.size, SRCALPHA)` até 1920×1080, mais um `transform.scale` + `.copy()` **por mancha** (dezenas por quadro).
- `level.py:_draw_enemy_attack_hazards` — uma `Surface` SRCALPHA por hazard ativo (o Bibliotecário chega a 11 entre tomos e lâminas).
- `level.py:_draw_lab` — `image.copy()` + `fill()` para as 4 peças do microscópio, todo quadro, enquanto a sequência não é resolvida (**medido: 1.200 cópias em 300 quadros**).
- `level.py:_draw_secret_elevators` — `pygame.transform.scale(sprite, rect.size)` por quadro, por elevador.
- `level.py:_draw_shadow` — `Surface` + `draw.ellipse` por plataforma, por quadro.
- `game.py:draw_dash_trail` — 3 `Surface` por quadro durante o dash.
- `enemy.py:Dragon._draw_sopro_fire` — `transform.scale(flame, (360,30))` por quadro durante o Sopro.
- `enemy.py` (todos) — `pygame.transform.flip(frame, True, False)` por inimigo, por quadro. Barato individualmente, mas é um `Surface` novo por inimigo por quadro; cachear os quadros espelhados no carregamento elimina isso de vez.

#### 2.8 `tiled_map.py:402` — culling errado para tiles maiores que o grid
```python
def visible(x, y):
    if y + self.tile_height < camera_y: return False
```
`self.tile_height` é o grid do **mapa** (32 px), não a altura real da imagem. As casas da vila são 128×128 e os adereços 64×64 (**35 tiles assim na vila, 15 na Fase 1**). Reproduzido: um tile desenhado em `y=352` com 64 px de altura é descartado com `camera_y=389`, apesar de ainda cobrir 27 px dentro da tela. Sintoma em jogo: **casas e árvores sumindo/piscando na borda superior da câmera**.

O mesmo vale para `_build_chunks`, que indexa pela posição de desenho sem considerar o tamanho real — hoje a margem de ±1 chunk salva, mas por sorte.

#### 2.9 `visible()` é uma closure recriada e chamada demais
`_draw_chunks` define `visible()` a cada chamada e a invoca **412.770 vezes em 300 quadros (1.376/quadro)** na Fase 3. É a 4ª linha mais cara do perfil em `tottime`. Com o tamanho real do tile guardado na tupla, o teste vira comparação inline sem função Python.

#### 2.10 Tela de título renderiza o mundo inteiro atrás
`Game.draw` executa `_draw_background` + `_draw_world` + tudo em qualquer estado, e só então `_draw_state_overlay` cobre com um `_dim_background(alpha=210)`. No TÍTULO e nas CONFIGURAÇÕES isso são ~10 ms/quadro simulando e desenhando a Fase 1 debaixo de uma camada quase opaca.

#### 2.11 Compressão de PNG
Rodando `optipng -o2 -strip all` (o nível **mais fraco**, sem perda nenhuma) nos 93 PNGs acima de 4 KB: **10,17 MB → 8,43 MB (−17,2%)**. Com `-o5` ou `oxipng -o4` a diferença é bem maior. Destaques:

| arquivo | antes | depois | redução |
|---|---:|---:|---:|
| `maps/university_tileset_32x32.png` | 33 KB | 14 KB | **−56%** |
| `maps/fase3_cave_tileset_v2_32x32.png` | 41 KB | 18 KB | **−55%** |
| `maps/library_tileset_32x32.png` | 46 KB | 21 KB | **−54%** |
| `images/cutscenes/elevador_lab_fundo.png` | 42 KB | 20 KB | **−53%** |
| `images/fog/quadros/*.png` (24 arquivos) | ~27 KB cada | ~13 KB | **−50%** |
| `images/enemies/slime_king.png` | 39 KB | 24 KB | −39% |
| `images/ui/dialogue_box.png` | 2,24 MB | 1,91 MB | −15% |

---

### P2 — Correção e arquitetura

#### 2.12 `level.py:1269` — `Level.draw()` com 34 parâmetros
`radon` classifica como **D (27)** — a função mais complexa do projeto. `Game._draw_world` passa 34 argumentos posicionais/nomeados, e a assinatura tem parâmetros como `_checkpoint` que nem são usados. Isso é acoplamento máximo: qualquer sprite nova exige tocar em `game.py`, `level.py` e na assinatura. O padrão certo já existe no próprio projeto (`Level` recebe `puzzle_sprites` como dicionário) — falta generalizar para **um único objeto `Assets`** passado uma vez.

Sintoma disso: o despacho de desenho de inimigo é uma escada de 9 `isinstance()` em `Level.draw`, quando cada classe de inimigo já tem o método `draw(surface, cx, cy, sprites)`. Bastaria cada inimigo expor `SPRITE_KEY = "slime_king"` e o laço virar duas linhas.

#### 2.13 `enemy.py` — ~1.100 linhas de duplicação estrutural
`Slime`, `CrystalStag`, `PossessedStudent`, `JanitorGuardian` e `SmallSlime` são **cinco cópias literais** do mesmo esqueleto: mesmos atributos (`WIDTH/HEIGHT/GROUND_LIFT/HEALTH/SPEED/PLATFORM_MARGIN/RESPAWN_TIME/HURT_DURATION/DEATH_FRAME_TIME/DEATH_FRAMES`), mesmos `rect`, `alive`, `update`, `_update_death`, `_update_respawn`, `_update_hurt`, `_patrol`, `take_hit`, `stomp`, `_start_dying`, `draw`, `_animation_frame`. As diferenças reais são os números e se existe estado `IDLE`. Os 4 chefes repetem outro esqueleto (`_next_attack_delay`, `_update_phase`, `wake_up`, `_start_attack`, `_update_attack_recover`, `_sprite_key`, `_phase_frame`, `face_player`, `melee_vulnerable`).

Isso já custou caro: `Slime.GROUND_LIFT` foi corrigido de 3 para 9 e as outras quatro classes ficaram com o valor antigo; `Dragon` é o único com `DEATH_FRAMES=14` sem quadros de morte de verdade. Duas classes-base (`GroundEnemy` e `Boss`) cortariam ~700 linhas e fariam correções valerem para todos de uma vez.

#### 2.14 `level.py:1476` — mutação de lista durante iteração
```python
for enemy in self.enemies:
    enemy.update()
    self._drain_pending_spawns(enemy)   # faz self.enemies.append(...)
```
Os slimes nascidos da Cisão entram na lista enquanto ela está sendo percorrida — recebem `update()` no mesmo quadro em que nascem. Hoje é inofensivo porque `SmallSlime` não gera spawns, mas é exatamente o tipo de coisa que vira loop infinito quando alguém der `pending_spawns` a outro inimigo. Colete os spawns e insira depois do laço.

#### 2.15 `game.py:2469 check_enemies` — `return` dentro do laço
Ao tomar dano de contato o método retorna, então **os inimigos seguintes na lista não são testados para dano de espada naquele quadro**. Com vários mobs juntos, acertar quem está atrás fica probabilístico. Deveria acumular o dano de contato e continuar o laço (ou tratar contato num passe separado).

#### 2.16 `audio.py:_main()` — áudio morto no build web
`_main()` devolve `sys.modules["__main__"]` e busca `.music`/`.sounds` nele. No desktop isso é `main.py`, onde o Pygame Zero injeta esses globais. No build WASM o `__main__` é `main_web.py`, que **não tem nenhum dos dois** — todas as chamadas caem no `except Exception: pass`. A versão web do jogo é **100% muda, silenciosamente**. O `except` genérico também esconde erros reais: um nome de faixa digitado errado nunca reclama.

#### 2.17 Duas formas diferentes de carregar asset opcional
- `Game._load_optional_object_sprite` / `_load_energy_box_sprites` / `_load_fog_frame_sequence`: checam `path.exists()` antes.
- `VFXManager.__init__`: checa `Path(path).exists()` e simplesmente pula a entrada.
- `cutscene.IntroCutscene` / `elevator_cutscene`: checam `self.BACKGROUND_PATH.exists()`.
- `audio.play_sfx`: `try/except` genérico.

Quatro estilos para o mesmo problema. Um único helper `load_optional(path) -> Surface | None` (e `load_optional_sheet`) unificaria — e teria pego o bug 2.3, porque um `load_optional` bem feito registra num log o que não achou em vez de sumir.

#### 2.18 `_configure_world_dimensions` roda antes de `_make_boss_arenas`
`_make_fog_barriers` monta o retângulo da neblina até `self.world_width` (7744). Depois, `_make_boss_arenas` estende `world_width` para `zone_rect.right + 300` = 7772. Sobram **28 px de fresta** à direita da barreira na Fase 1. Calcule as arenas antes das barreiras, ou use `world_width + margem` na barreira.

#### 2.19 Código morto de verdade
- `tiled_map._image_for_gid`, `level.elevator_lever_active`, `level.upper_lever_active`, `audio.stop_music` — definidos, nunca chamados.
- `dialogue.LINE_HEIGHT` e `player.WALK_FRAMES` — constantes nunca lidas.
- `main.py:124` — parâmetro `rel` não usado.
- `images/village/aderecos/fonte/_vila_mock.py:4` — `import os` não usado; `houses_back.py:22` importa `STONE`/`STONED` sem usar.
- **O caminho inteiro "sem Tiled"**: `_build_generated_course`, `_build_school_course`, `_build_university_course`, `_build_default_underground_lab`, `_append_platform_layout`, `_platform_with_motion`, `_university_platform_skin`, `_make_university_decor`, `_draw_university_backdrop`, `_draw_university_platform_props`, `_draw_shadow`, `ENEMY_PLATFORM_SPAWNS`, e as chaves `layout`/`step`/`widths`/`heights`/`moving`/`decor_*` de `PHASES`. Como os 7 `.tmx` existem, **nada disso executa**. São ~350 linhas + os dados de `PHASES`.
- **`plataform.Platform.draw` e `Platform._tile_image` nunca executam** (verificado por instrumentação num playthrough completo): a Fase 1 desenha as duas plataformas de elevador por `_draw_school_platform`, e Fases 2/3 têm o grupo "Plataformas" vazio. Logo `images/tiles/platform1-4.png` e `images/tiles/university_sheet.png` são carregados e nunca aparecem em tela.
- `SCHOOL_SPRITE_RECTS` (11 recortes: `chalkboard`, `whiteboard`, `clock`, `bulletin`, `exit`, `plant`, `desk_row`, `locker`, `bookshelf`, `door`, `lab_table`) — **nenhum é usado**. O único uso de `school_sprites` no projeto inteiro é `school_sprites[floor_name]`. Ou seja: **`escola_sheet.png` (2,56 MB) é carregado para recortar 4 tiles de 32×32.**

#### 2.20 `settings.CAMERA_ZOOM = 1`
O zoom de câmera pedido pelo professor está implementado (`_blit_zoomed_world`) e **desligado**. Se a decisão foi voltar atrás, vale remover ou documentar; do jeito que está, é uma feature invisível que ninguém sabe que existe.

---

### P3 — Mapas

| Achado | Onde |
|---|---|
| `escola_tileset_64x64.tsx` declara `tilecount=480`, imagem comporta 120 (ver 2.4) | `maps/` |
| `fase1_escola.tmx` importa `fase3_pesquisa.tsx` (GIDs 121–280) e **não usa nenhum tile dele** — carrega um PNG de 41 KB à toa e cria o buraco de GID | `fase1_escola.tmx` |
| `fase2_biblioteca_sala.tmx` importa `fase2_laboratorio_sala.tsx` (GIDs 161–320); o GID máximo usado é 155 → **tileset inteiro carregado e não usado** (30 KB) | `fase2_biblioteca_sala.tmx` |
| Camada `decoração2` vazia (0 tiles) | `fase2_universidade.tmx` |
| Camada `Perigos` vazia (0 tiles) | `fase1_escola.tmx` |
| `Colisão` da Fase 1: **774 tiles de grama da vila vs 200 do tileset da escola** | `fase1_escola.tmx` |
| Só **2 checkpoints** (`PLANO_FASE1.md` pede 3) e **5 livros** (o plano pede 7) | `fase1_escola.tmx` |
| Só **3 alavancas**; falta `elevador=principal, posicao=topo` → cai no fallback `_fixed_lever` | `fase1_escola.tmx` |
| Objeto `neblina` em x=6800 e `rei_slime` em x=6891–7472 → **o chefe nasce atrás da parede opaca** | `fase1_escola.tmx` |
| `fase1_laboratorio_secreto.tmx`: `Fundo`, `Perigos` e `Decoração` **completamente vazias**; só 180 tiles de colisão numa faixa de y=544..640. Mundo declarado 1920×1760 mas usado só 1920×640 — uma queda da borda leva 1.400 px até a morte | `fase1_laboratorio_secreto.tmx` |
| `Plataformas` vazio em **todos** os 7 mapas (por isso 2.19 / `Platform.draw` morto) | todos |
| Nenhum mapa usa flip horizontal/vertical de tile — mas o parser **descarta os bits de flip** (`FLIPPED_GID_MASK`) sem aplicá-los. No dia em que você espelhar um tile no Tiled, ele aparecerá sem espelho, silenciosamente | `tiled_map.py` |
| O parser lê só `root.findall("layer")` e `root.findall("objectgroup")` — **não desce em `<group>`**. Se você agrupar camadas no Tiled, elas somem do jogo sem erro | `tiled_map.py` |

---

## 3. Patches para o que traz mais ganho

### 3.1 Valores de combate (`game.py`)

```python
# --- ANTES ---
STARTING_LIVES = 1000
MAX_LIVES = 1000
STANDARD_ATTACK_POWER = 100

# --- DEPOIS ---
# Vida em corações fracionários (mob = 0.5, chefe = 1.0 — ver
# MOB_CONTACT_DAMAGE/BOSS_CONTACT_DAMAGE). 5 corações dá ~10 toques de
# mob antes do game over, margem confortável pra uma primeira jogada
# sem tornar a luta de chefe irrelevante.
STARTING_LIVES = 5
MAX_LIVES = 5
# Dano base do golpe corpo a corpo. Calibrado contra enemy.HEALTH:
# Slime(2)=2 golpes, CrystalStag(3)=3, JanitorGuardian(4)=4,
# chefes(12)=12 golpes normais ou 6 finalizadores de combo.
STANDARD_ATTACK_POWER = 1
```

E, ainda em `game.py`, torne a hierarquia de dano explícita para nunca mais inverter:

```python
DASH_ATTACK_POWER = 2
COMBO_FINISHER_POWER = 2
PARRY_DAMAGE = 3
RANGED_ATTACK_POWER = 1

# Trava de sanidade: se alguém mexer nos números acima sem pensar, o jogo
# reclama no import em vez de silenciosamente virar um sandbox.
assert STANDARD_ATTACK_POWER < DASH_ATTACK_POWER <= PARRY_DAMAGE, (
    "O golpe de dash e o parry precisam causar MAIS dano que o golpe padrão"
)
assert MAX_LIVES <= 12, "Vidas acima disso estouram a barra de corações do HUD"
```

E conserte o teste de alcance, que hoje depende de comparar poderes:

```python
    def _attack_box(self):
        if not self.attack_timer:
            return None
        # ANTES: reach = DASH_ATTACK_REACH if self.attack_power > STANDARD_ATTACK_POWER else ...
        # Comparar poderes acopla "alcance" a "dano" — bastou STANDARD virar 100
        # pra o golpe de dash perder o alcance estendido sem ninguém notar.
        # Agora o alcance vem do que está acontecendo de fato.
        reach = DASH_ATTACK_REACH if self.player.dashing else STANDARD_ATTACK_REACH
        offset = PLAYER_HITBOX_WIDTH if self.player.facing_right else -(24 + reach)
        return self.player.rect.move(offset, 4).inflate(reach, 10)
```

### 3.2 Mensagem da HUD (`game.py` + `hud.py`)

Torne "duração padrão" explícita em vez de repetir números mágicos:

```python
# game.py, junto das outras constantes
MESSAGE_DURATION = 150          # 2,5 s — avisos comuns (item, pesquisa, achado)
MESSAGE_DURATION_LONG = 240     # 4 s   — desbloqueios e bloqueios de progresso

    def show_message(self, text, duration=MESSAGE_DURATION):
        """Único ponto de entrada da caixa de mensagem da HUD. Existe porque
        oito lugares diferentes setavam self.message junto com
        message_timer = 0, e hud.draw_hud só desenha com `if message_timer`
        — ou seja, a mensagem era escrita e nunca aparecia."""
        self.message = text
        self.message_timer = duration
```

Depois troque **todos** os pares `self.message = ...; self.message_timer = ...` por `self.show_message(...)`. Os oito casos com `= 0` (linhas 1073, 1093, 1245, 2110, 2214, 2357, 2444, 2449) passam a funcionar. Exemplo do mais crítico:

```python
        if len(self.collected) < len(self.level.research) or needs_microscope:
            self.show_message(
                "Encontre todas as partes da pesquisa antes de avançar.",
                MESSAGE_DURATION_LONG,
            )
            player.x = self.level.world_width - 160
```

E, em `hud.py`, uma barreira contra a mesma armadilha:

```python
def draw_hud(..., message, message_timer, ...):
    ...
    # `message_timer` é a duração restante; 0 significa "sem mensagem".
    # Se houver texto mas o timer for 0, é bug de quem chamou — mostre
    # assim mesmo por 1 quadro em vez de engolir em silêncio.
    if message and message_timer:
        _draw_message(surface, message)
```

### 3.3 Fundo pré-tingido + fim dos `fill()` — o maior ganho de performance

Em `game.py`, substitua `_load_backgrounds` / `_create_scene_filters` / `_draw_background` / `draw`:

```python
    def _load_backgrounds(self):
        """Cada fundo é guardado em DUAS variantes já com a cor de cena
        composta: a normal e a "subterrânea". Antes, essa cor era um
        Surface SRCALPHA de 1920x1080 blitado por cima do fundo TODO
        QUADRO — medido em ~4,7 ms/quadro, o item mais caro do jogo. Como
        a cor é constante e o fundo é opaco e cobre a tela inteira, compor
        no carregamento dá um resultado pixel a pixel idêntico por 0 ms.
        A composição é feita na imagem PEQUENA (256x224), antes do
        redimensionamento, então o custo de memória é o mesmo de antes."""
        self.backgrounds = {}
        for key, path in (
            ("school", "backgrounds/background_school.png"),
            ("university", "backgrounds/university_background.png"),
            ("cave", "backgrounds/cave_background_v2.png"),
            ("lab", "backgrounds/lab_background.png"),
            ("library", "backgrounds/library_background.png"),
            ("village", "backgrounds/ceu.png"),
        ):
            if not (ASSET_DIR / path).exists():
                continue
            raw = self._load_image(path, alpha=False)
            self.backgrounds[key] = {
                variant: self._scale_to_screen(self._tinted(raw, color))
                for variant, color in self._scene_tints(key).items()
            }
        self.background_mirror = {
            variant: pygame.transform.flip(image, True, False)
            for variant, image in self.backgrounds.get("university", {}).items()
        }

    # Cores de cena (as mesmas de antes, agora só como dados).
    BG_TINT = (38, 53, 76, 72)
    UNIVERSITY_TINT = (55, 65, 80, 85)
    UNDERGROUND_TINT = (8, 12, 27, 155)

    def _scene_tints(self, key):
        """Quais combinações de filtro cada fundo pode precisar. Só a
        universidade usa o filtro extra dela, então os outros fundos
        guardam duas variantes em vez de quatro."""
        if key == "university":
            return {
                "normal": self._combine_overlay_colors(self.BG_TINT, self.UNIVERSITY_TINT),
                "underground": self._combine_overlay_colors(
                    self.BG_TINT, self.UNIVERSITY_TINT, self.UNDERGROUND_TINT
                ),
            }
        return {
            "normal": self.BG_TINT,
            "underground": self._combine_overlay_colors(self.BG_TINT, self.UNDERGROUND_TINT),
        }

    @staticmethod
    def _tinted(raw, rgba):
        """Compõe uma cor RGBA sólida sobre uma cópia opaca da imagem —
        mesmo resultado de blitar um overlay SRCALPHA por cima, só que
        uma vez, na imagem pequena."""
        base = raw.convert()
        layer = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        layer.fill(rgba)
        base.blit(layer, (0, 0))
        return base

    def _scale_to_screen(self, image):
        scale = HEIGHT / image.get_height()
        return pygame.transform.scale(
            image, (round(image.get_width() * scale), HEIGHT)
        ).convert()

    def _draw_background(self, surface):
        """Um único blit opaco por ladrilho, sem overlay nenhum depois."""
        variant = "underground" if self.player.y > self.UNDERGROUND_Y else "normal"
        key = self._background_key()
        images = self.backgrounds.get(key)
        if images is None:
            surface.fill(self.VILLAGE_PLACEHOLDER_SKY)
            return
        if key == "university":
            self._draw_mirrored_background(surface, images[variant], variant)
        else:
            self._draw_repeating_background(
                surface, images[variant], parallax=self.PARALLAX.get(key, 1.0)
            )

    def _background_key(self):
        if self.level.room == "laboratorio":
            return "lab"
        if self.level.room == "biblioteca":
            return "library"
        if self.level.index == VILLAGE:
            return "village" if "village" in self.backgrounds else None
        return ("school", "university", "cave")[self.level.index]

    PARALLAX = {"school": 0.3, "village": 0.3, "cave": 0.35, "university": 1.0,
                "lab": 1.0, "library": 1.0}
    # Y a partir do qual o cenário conta como "subterrâneo". Calibrado pro
    # mapa antigo da Fase 1 — reajuste quando o laboratório novo existir
    # de verdade no .tmx (ver PLANO_FASE1.md, item 1).
    UNDERGROUND_Y = 780
```

E, em `draw()`, os dois `fill()`:

```python
    def draw(self, screen):
        real_surface = screen.surface
        # Os dois fill((6,14,29)) que ficavam aqui saíram: _draw_background
        # sempre cobre a superfície inteira (ladrilha ou preenche), e
        # _blit_zoomed_world sempre cobre a tela inteira. Eram ~1,6 ms por
        # quadro pintando pixels que seriam sobrescritos no blit seguinte.
        if self.state == INTRO:
            self.intro.draw(real_surface, draw_text)
            return
        ...
```

> **Cuidado ao aplicar:** se um dia algum estado desenhar sem cobrir a tela toda, o lixo do quadro anterior aparece. Os únicos caminhos hoje são INTRO (a cutscene preenche), a cutscene do elevador (preenche) e PLAYING (`_draw_background` preenche). Se adicionar um estado novo, ele precisa preencher.

### 3.4 Neblina no tamanho nativo + carregamento sob demanda (`game.py`, `fog.py`)

```python
    @staticmethod
    def _load_fog_frame_sequence(subfolder, prefix, count=24):
        """Guarda os quadros NO TAMANHO NATIVO (480x270). Antes cada um era
        ampliado pra 1920x1080 no carregamento: 48 quadros x 8,3 MB =
        380 MB — 63% dos 600 MB de RSS do processo, para um efeito que só
        existe na Fase 1. Nativos são 23,7 MB. O redimensionamento passa
        pra hora de desenhar (1 chamada por quadro, só quando a neblina
        está de fato na tela)."""
        folder = ASSET_DIR / "fog" / subfolder
        if not folder.exists():
            return None
        frames = []
        for i in range(count):
            path = folder / f"{prefix}_{i:02d}.png"
            if not path.exists():
                return None
            frames.append(pygame.image.load(path).convert_alpha())
        return frames
```

Em `fog.py`, um cache de um quadro só (o índice muda ~12x/s, não 60x/s):

```python
    def _scaled_frame(self, frame, size):
        """Cache de UM quadro: a animação roda a FRAME_FPS=12, então o
        mesmo quadro é pedido ~5 vezes seguidas a 60fps. Sem isso seria um
        transform.scale de tela cheia por quadro; com isso, ~12 por segundo."""
        if getattr(self, "_scaled_key", None) != (id(frame), size):
            self._scaled_key = (id(frame), size)
            self._scaled_cache = pygame.transform.scale(frame, size)
        return self._scaled_cache
```

E o carregamento sob demanda em `Game._apply_fog_sprite`:

```python
    def _apply_fog_sprite(self, level):
        """Só carrega os 48 quadros de neblina se a fase realmente tiver
        alguma barreira — hoje só a Fase 1 tem. Antes eram carregados no
        Game() e ficavam residentes o jogo inteiro."""
        if not level.fog_barriers:
            return
        if self.fog_frames is None:
            self.fog_frames = self._load_fog_frame_sequence("quadros", "quadro")
            self.fog_frames_corpo = self._load_fog_frame_sequence("quadros_corpo", "corpo")
        for barrier in level.fog_barriers:
            barrier.sprite = self.fog_sprite
            barrier.frames = self.fog_frames
            barrier.frames_corpo = self.fog_frames_corpo
```

(Inicialize `self.fog_frames = self.fog_frames_corpo = None` em `_load_assets` e remova as duas chamadas de lá.)

Aproveite e **apague** os três overlays mortos, que são 24 MB:

```python
    def _create_scene_filters(self):
        # background_filter / university_filter / underground_filter foram
        # removidos: estavam comentados como "mantidos apenas como
        # referência/compat", ninguém os lia, e eram 3 Surfaces SRCALPHA de
        # tela cheia (24 MB). As cores viraram as constantes BG_TINT /
        # UNIVERSITY_TINT / UNDERGROUND_TINT usadas por _load_backgrounds.
        pass   # (ou simplesmente delete o método e a chamada)
```

### 3.5 Culling correto para tiles maiores que o grid (`tiled_map.py`)

Guarde o tamanho real na própria tupla, no carregamento, e faça o teste sem closure:

```python
            if local_id in tileset["animations"]:
                animated_tiles.append((draw_x, draw_y, tileset, local_id))
            else:
                image = self._tile_image(tileset, local_id)
                # Guarda o tamanho REAL da imagem junto: as casas da vila são
                # 128x128 num grid de 32x32, e o culling comparava contra
                # self.tile_height (32). Um tile de 128px cujo topo saía pela
                # borda de cima da câmera era descartado enquanto ainda cobria
                # ~100px dentro da tela — casas e árvores piscando na borda.
                tiles.append((draw_x, draw_y, image, image.get_width(), image.get_height()))
```

```python
    def _draw_chunks(self, surface, camera_x, camera_y, tile_chunks, animated_chunks):
        right = camera_x + surface.get_width()
        bottom = camera_y + surface.get_height()
        chunk_w = self.CHUNK_TILES * self.tile_width
        chunk_h = self.CHUNK_TILES * self.tile_height
        first_col = int(camera_x // chunk_w) - 1
        last_col = int(right // chunk_w) + 1
        first_row = int(camera_y // chunk_h) - 1
        last_row = int(bottom // chunk_h) + 1
        blit = surface.blit   # o laço roda ~1400x por quadro; evita o lookup

        for chunk_row in range(first_row, last_row + 1):
            for chunk_col in range(first_col, last_col + 1):
                # Teste inline em vez da closure visible(): o perfil mostrou
                # 412.770 chamadas dela em 300 quadros (1.376/quadro), a 4ª
                # linha mais cara do jogo em tempo próprio.
                for x, y, image, w, h in tile_chunks.get((chunk_col, chunk_row), ()):
                    if x + w < camera_x or x > right or y + h < camera_y or y > bottom:
                        continue
                    blit(image, (x - camera_x, y - camera_y))
                for x, y, tileset, local_id in animated_chunks.get((chunk_col, chunk_row), ()):
                    image = self._current_frames[(id(tileset), local_id)]
                    if (x + image.get_width() < camera_x or x > right
                            or y + image.get_height() < camera_y or y > bottom):
                        continue
                    blit(image, (x - camera_x, y - camera_y))
```

E `_build_chunks` deve indexar considerando a altura real, para o tile grande entrar em todos os chunks que ele cruza:

```python
    def _build_chunks(self, entries):
        """Um tile maior que o grid cruza mais de um chunk — registre-o em
        todos. Antes só o chunk do canto superior esquerdo era usado, e a
        margem de +-1 chunk em _draw_chunks salvava por acidente."""
        chunk_w = self.CHUNK_TILES * self.tile_width
        chunk_h = self.CHUNK_TILES * self.tile_height
        chunks = {}
        for entry in entries:
            x, y = entry[0], entry[1]
            w = entry[3] if len(entry) > 3 else self.tile_width
            h = entry[4] if len(entry) > 4 else self.tile_height
            for row in range(int(y // chunk_h), int((y + h) // chunk_h) + 1):
                for col in range(int(x // chunk_w), int((x + w) // chunk_w) + 1):
                    chunks.setdefault((col, row), []).append(entry)
        return chunks
```

### 3.6 Caixa de diálogo sem distorção (`dialogue.py`)

```python
        raw_background = pygame.image.load(
            ASSET_DIR / "ui" / "dialogue_box.png"
        ).convert_alpha()
        # A arte é 1536x1024 (proporção 1.500) e era esticada pra 1228x540
        # (proporção 2.274) com pygame.transform.scale — 52% de distorção,
        # a moldura ornamentada saía achatada. Agora a LARGURA manda e a
        # altura acompanha a proporção real do arquivo; a caixa fica mais
        # alta, então o rodapé (BOTTOM_MARGIN) e as faixas de texto
        # (BODY_TOP/BODY_BOTTOM) precisam ser reconferidos em jogo.
        self.overlay_width = int(WIDTH * self.WIDTH_RATIO)
        aspect = raw_background.get_height() / raw_background.get_width()
        self.overlay_height = round(self.overlay_width * aspect)
        self.overlay_x = (WIDTH - self.overlay_width) // 2
        self.overlay_y = HEIGHT - self.overlay_height - self.BOTTOM_MARGIN
        self.background = pygame.transform.smoothscale(
            raw_background, (self.overlay_width, self.overlay_height)
        )
```

> `BODY_TOP=225` / `BODY_BOTTOM=280` e o `y=210` do nome do locutor foram medidos sobre a caixa achatada — precisam ser recalibrados como **frações** da nova `overlay_height`, não em pixels absolutos. Isso exige ver rodando; vale fazer junto.

### 3.7 Nome do arquivo da moldura (`elevator_cutscene.py`)

```python
    # O arquivo salvo tem "lav" em vez de "lab" — mantido assim pra não
    # exigir renomear no disco. Se você renomear, troque aqui também.
    FRAME_PATH = ASSET_DIR / "cutscenes" / "elevador_lav_moldura.png"
```

*(Renomear o arquivo para `elevador_lab_moldura.png` é a solução mais limpa; escolha uma.)*

### 3.8 Alocações por quadro — os três casos mais caros

**`level.py:_draw_enemy_attack_hazards`** — cache de overlays por tamanho:
```python
    _HAZARD_OVERLAYS = {}

    def _hazard_overlay(self, size, color):
        """Antes: um pygame.Surface SRCALPHA novo por hazard, por quadro
        (o Bibliotecário chega a 11 simultâneos). Como as cores são
        constantes por classe de chefe e os tamanhos se repetem, um cache
        elimina a alocação inteira."""
        key = (size, color)
        overlay = self._HAZARD_OVERLAYS.get(key)
        if overlay is None:
            overlay = pygame.Surface(size, pygame.SRCALPHA)
            overlay.fill(color)
            self._HAZARD_OVERLAYS[key] = overlay
        return overlay
```

**`level.py:_draw_lab`** — as peças esmaecidas do microscópio:
```python
        # Cache das versões esmaecidas: antes era image.copy() + fill()
        # nas 4 peças, TODO QUADRO, enquanto a sequência do painel não
        # fosse resolvida (medido: 1.200 cópias em 300 quadros).
        if not sequence_solved:
            if not hasattr(self, "_dim_parts"):
                self._dim_parts = []
                for image in puzzle_sprites["microscope_parts"]:
                    dim = image.copy()
                    dim.fill((105, 105, 105, 145), special_flags=pygame.BLEND_RGBA_MULT)
                    self._dim_parts.append(dim)
            source = self._dim_parts
        else:
            source = puzzle_sprites["microscope_parts"]
```

**`enemy.py`** — quadros espelhados cacheados no carregamento. Em `game._load_grid_sheet`, devolva pares `(normal, espelhado)` ou um segundo dicionário `sprites["<chave>_flip"]`, e troque cada `pygame.transform.flip(frame, True, False)` do `draw()` por um lookup. São ~10 chamadas de `flip` por quadro hoje (uma por inimigo vivo), cada uma alocando um `Surface`.

### 3.9 Não simular/desenhar o mundo no menu (`game.py`)

```python
    def draw(self, screen):
        real_surface = screen.surface
        if self.state == INTRO:
            self.intro.draw(real_surface, draw_text); return
        if self.elevator_cutscene.active:
            self.elevator_cutscene.draw(real_surface, draw_text); return
        # No TÍTULO/CONFIGURAÇÕES o mundo inteiro era desenhado (~10 ms) só
        # pra ficar sob um _dim_background(alpha=210) quase opaco. Um
        # instantâneo do primeiro quadro dá o mesmo visual de graça.
        if self.state in (TITLE, SETTINGS):
            if self._menu_snapshot is None:
                self._menu_snapshot = self._render_world_snapshot()
            real_surface.blit(self._menu_snapshot, (0, 0))
            self._draw_state_overlay(real_surface)
            return
        ...
```

### 3.10 `escola_tileset_64x64.tsx`
```xml
<!-- 256x480 com tiles de 32x32 = 8 colunas x 15 linhas = 120 tiles.
     tilecount="480" fazia o tileset declarar os GIDs 1..480, invadindo as
     faixas de fase3_pesquisa (121-280), aderecos_vila (281-292) e
     chao_vila (293-308). -->
<tileset version="1.10" tiledversion="1.12.2" name="escola_tileset_64x64"
         tilewidth="32" tileheight="32" tilecount="120" columns="8">
  <image source="escola_tileset_TILED_64x64_FINAL.png" width="256" height="480"/>
</tileset>
```

E, como cinto de segurança em `tiled_map._load_tileset`:
```python
        image = pygame.image.load(image_path).convert_alpha()
        columns = int(tileset_root.get("columns", 1))
        tile_w = int(tileset_root.get("tilewidth", self.tile_width))
        tile_h = int(tileset_root.get("tileheight", self.tile_height))
        declared = int(tileset_root.get("tilecount", 0))
        # O Tiled às vezes fica com um tilecount desatualizado depois de
        # trocar o tamanho do tile (aconteceu com escola_tileset_64x64.tsx:
        # declarava 480 numa imagem de 120). Confiar no declarado faz o
        # tileset "reivindicar" GIDs de outros e leva a subsurface fora dos
        # limites — usar o menor entre declarado e o que a imagem comporta.
        real = (image.get_width() // tile_w) * (image.get_height() // tile_h)
        if declared != real:
            print(f"[TiledMap] aviso: {source} declara tilecount={declared} "
                  f"mas a imagem comporta {real} tiles — usando {real}.")
        tile_count = min(declared, real) if declared else real
```

### 3.11 Áudio no build web (`audio.py`)

```python
def _main():
    module = sys.modules["__main__"]
    if not hasattr(module, "music"):
        # main_web.py (pygbag) não recebe os globais que o Pygame Zero
        # injeta em main.py, então TODO o áudio caía silenciosamente no
        # except das funções abaixo. Avisa uma vez em vez de nunca.
        global _warned_no_audio
        if not _warned_no_audio:
            _warned_no_audio = True
            print("[audio] música/efeitos indisponíveis neste ponto de entrada "
                  "(sem os globais do Pygame Zero) — build web roda mudo.")
    return module
```
A solução de verdade é um `_Backend` fino que, no `main_web`, use `pygame.mixer` direto. Mas o aviso já tira o problema do escuro.

---

## 4. Auditoria dos assets de imagem

**Números:** 204 PNGs, 47,9 MB no total (com `music/` e `sounds/`), sendo **~11 MB só de imagens**. Todos os 143 PNGs que consegui inspecionar estão em RGBA/RGB de 8 bits, com alpha correto onde deveria — não achei nenhum sprite com fundo sobrando nem grade de sheet inconsistente.

### 4.1 As spritesheets estão todas corretas
Verifiquei uma a uma contra o que `_load_grid_sheet` recorta. **Nenhuma divergência**:

| arquivo | dimensão | grade esperada pelo código | ok |
|---|---|---|:--:|
| `crystal_stag.png` | 560×136 | 40×34, linhas [8,8,4,14] | ✓ |
| `dark_wraith.png` | 672×192 | 48×48, [8,7,4,14] | ✓ |
| `possessed_student.png` | 576×240 | 48×48, [8,8,6,4,12] | ✓ |
| `janitor_guardian.png` | 768×384 | 64×64, [8,8,8,8,4,12] | ✓ |
| `lab_specimen.png` | 672×288 | 56×48, [8,8,7,8,4,12] | ✓ |
| `librarian_boss.png` | 896×384 | 64×64, [8,8,9,10,4,14] | ✓ |
| `slime_king.png` | 768×384 | 64×64, [8,8,9,10,4,12] | ✓ |
| `slime_common.png` | 256×128 | 32×32, [6,8,3,6] | ✓ |
| `cientistas_idle.png` | 384×240 | 48×48, 5 linhas de 8 | ✓ |
| `vfx.png` / `vfx_lab.png` | 256×160 | 32×32, 5 linhas | ✓ |
| `vfx_university.png` / `vfx_library.png` | 192×160 | 32×32, 5 linhas | ✓ |

### 4.2 Duas linguagens visuais misturadas
Usando bytes-por-pixel comprimido como proxy de "quantas cores/quanto anti-aliasing":

**Pixel art limpa (0,01–0,3 bpp)** — `village/*` (0,05–0,20), `fog/*` (0,18–0,21), a maioria de `enemies/*` (0,11–0,18), `maps/*_tileset` (0,18–0,28), `props/*`, `vfx/*` (0,08–0,14).

**Arte renderizada com gradiente/AA (>1,0 bpp)** — `escola_sheet.png` (1,71), `dialogue_box.png` (1,42), `hospital.png` (1,02), `ifsp_background.png` (1,06), `cave_background.png` (1,23), `tiles/platform1-4.png` (1,98–2,46), `university_sheet.png` (1,71), `door.png` (2,79), `microscope_*.png` (1,11–1,65).

Ou seja: **o HUD/diálogo, a cutscene do hospital, o tileset da escola e as peças do microscópio não pertencem ao mesmo mundo visual dos inimigos, da vila e da caverna.** O `door.png` com 2,79 bytes/pixel num sprite de 48×64 é o caso mais claro: é uma porta desenhada com sombreado suave num jogo cujas casas são pixel art de 4 cores.

### 4.3 Redimensionamento em tempo real / escala não-inteira

| asset | arquivo | como é desenhado | problema |
|---|---|---|---|
| `dialogue_box.png` | 1536×1024 (1,50:1) | 1228×540 (2,27:1) | **distorção de 52%** — 0,80× na horizontal, 0,53× na vertical |
| `university_background.png`, `cave_background_v2.png`, `lab_background.png`, `library_background.png` | 256×224 | altura 1080 | escala **4,821×** — não-inteira, pixels de larguras diferentes na mesma imagem |
| `background_school.png`, `ceu.png` | 512×320 | altura 1080 | escala **3,375×** — idem |
| `hospital.png` | 1536×1024 | cobre 1920×1080 | `smoothscale` 1,25× para cima → borrado; ainda perde 200 px na vertical no corte |
| `elevador_lab.png` | — | `transform.scale(sprite, rect.size)` **por quadro** | deveria ser escalado uma vez no carregamento |
| `dragon_fire.png` (chama) | — | `transform.scale(flame, (360,30))` **por quadro** durante o Sopro | idem |

**Recomendação para os fundos:** ou redesenhe em 384×216 (escala 5× exata = 1920×1080) / 480×270 (4× exata), ou escale por fator inteiro (4× → 1024×896) e centralize verticalmente com o resto preenchido pela cor de céu. A escala 4,821× é a causa da textura "irregular" — alguns pixels do desenho viram 4 pixels de tela e outros viram 5.

### 4.4 Órfãos confirmados (existem no disco, nenhum código os alcança)

| arquivo | tamanho | observação |
|---|---:|---|
| `images/backgrounds/ifsp_background.png` | **1,66 MB** | maior órfão do projeto |
| `images/backgrounds/cave_background.png` | 70 KB | substituído por `cave_background_v2.png` |
| `images/backgrounds/cave_background_underwater.png` | 32 KB | nunca referenciado |
| `images/player/background.png` | **493 KB** | 1920×700, nenhuma referência |
| `images/cutscenes/elevador_lav_moldura.png` | 18 KB | órfão **por causa do typo** (ver 2.3) — a arte existe e é boa |
| `images/npcs/seu_joaquim_idle.png` | 3,3 KB | **288×48 = 6 quadros de 48×48, arte pronta e nunca carregada** |
| `images/lava_lake.png` | 20 KB | a lava é 100% tiles do Tiled hoje |
| `images/enemies/crystal_crab.png` | 5,6 KB | inimigo que não existe no jogo |
| `images/enemies/dark_hand.png` | 4,4 KB | idem |
| `images/enemies/slime_king_attack.png` | 1,4 KB | substituído pela sheet `slime_king.png` |
| `images/objects/activated_lever.png`, `lever.png` | 1,3 KB | substituídos por `alavanca_animation1-5.png` |
| `images/vfx/boss_attacks/indicador_perigo.png`, `meteoro.png` | 0,9 KB | do "Voo da Fúria" removido |
| `images/fase3_tileset/crystal cave tiles.png` | 18 KB | o tileset em uso é `maps/fase3_cave_tileset_v2_32x32.png` |
| `maps/fase3_cave_tileset_32x32.png` | 40 KB | v1, o `.tsx` aponta para o v2 |
| `fonts/ThaleahFat.ttf` | 10 KB | o jogo usa `minha_fonte.ttf` |
| `images/tiles/platform1-4.png` | 9,1 KB | carregados, mas `Platform.draw` **nunca executa** (ver 2.19) |
| `images/tiles/university_sheet.png` | 28 KB | idem |
| `images/props/*.png` (6) | 2,1 KB | só o caminho "sem Tiled", morto |
| `images/village/interior/*.png` (10) | 4,2 KB | reservado, ainda não usado (documentado no `LEIA-ME_interior.md`) |
| `images/village/{casas,chao,aderecos}/*` individuais (~40) | ~25 KB | os `.tsx` usam só os atlas `chao.png`, `vila_casas_completo.png`, `aderecos.png` |
| `maps/*.bak_v3`, `*.bak_v1`, `images/player/player.ase` | 208 KB | backups/fonte |

**Também na pasta:** `build/web/snctjogo.apk` (9,98 MB) e `build/web/snctjogo.tar.gz` (9,96 MB) — **20 MB de artefatos de build versionados junto com o projeto**. Fora do `.gitignore`, isso pesa cada clone.

**Além disso:** 14 PNGs estão como *hardlinks* no sistema de arquivos (`background_school.png`, `dragon.png`, `dragon_fire.png`, `items.png`, `player_sheet.png`, `parry_flash.png`, `elevador_lab.png`, `fog_cloud.png`, `tomada.png`, `fio_corpo.png`, `chave_fenda_grande.png`, `chave_desparafusando.png`, `parafuso_caindo_anim.png`, `escola_tileset_TILED_64x64_FINAL.png`). Não é bug, mas indica que existem cópias duplicadas desses arquivos em outro lugar do disco compartilhando os mesmos blocos — vale conferir se não há uma pasta antiga do projeto por aí.

### 4.5 Documentação desatualizada
- `IDEIAS_FUTURAS.md` diz que `parry_flash.png` "ainda não existe no disco" — **existe** (613 bytes).
- `PLANO_VILA.md` e `LEIA-ME_vila.md` descrevem `vila_casas_completo.png` como "256×128, grade 64×64" — o arquivo real é **512×256, grade 128×128**, e o `casas_vila.tsx` já reflete isso. A doc ficou para trás.
- O guia de apresentação sugere confirmar se a Fase 1 já tem cenário completo. Resposta: tem terreno pintado, mas majoritariamente com o tileset **da vila** (ver P3).

### 4.6 Reorganização sugerida de pastas
A estrutura atual é boa, com dois pontos frouxos:
- `images/lava_lake.png` está solto na raiz de `images/` (deveria estar em `images/objects/` ou ser apagado).
- `images/fase3_tileset/` e `maps/*.png` guardam tilesets em dois lugares. Como o Tiled resolve caminhos relativos ao `.tsx`, o mais simples é **um único `images/tilesets/`** com todos, e os `.tsx` apontando para lá.
- `images/village/*/fonte/*.py` (5 scripts geradores) e os `LEIA-ME_*.md` são fonte, não asset — mereciam um `tools/` na raiz.

---

## 5. Ideias novas de design

Todas partem do que o jogo **já tem construído** e reaproveitam sistemas existentes — nenhuma exige framework novo.

### 5.1 Mecânica: o Caderno de Campo (a mecânica que o tema pede e o jogo ainda não tem)
Hoje "pesquisa" é um coletável que destranca a saída. Mas a tese do jogo — dita pela mãe da Lia — é *"todo experimento pode falhar; levante-se e tente de novo"*. O jogo nunca deixa o jogador **falhar produtivamente**.

Proposta: cada chefe derrotado e cada `livro` coletado escreve uma **anotação** no caderno (tecla `TAB`, mesmo padrão de pausa da `Hint`). O caderno não é só um menu de lore: **anotar um padrão de ataque de chefe o revela permanentemente**. Depois de tomar o Esmagar do Rei Slime três vezes, a anotação aparece sozinha ("*Esmagar: ele infla antes. Onda rasteira dos dois lados — pular*") e, a partir daí, o telégrafo daquele golpe ganha um contorno visível.

*Por que encaixa:* transforma morrer em progresso mensurável, que é literalmente a frase da mãe, e usa três coisas que já existem — `SCIENCE_FACTS`, `Hint`, e as fases de `TELEGRAPH` de cada chefe. Também resolve o problema de dificuldade sem trocar números: o jogo fica mais fácil porque o jogador **aprendeu**, não porque foi nerfado.

### 5.2 Mecânica: o Microscópio como lente de mundo
O microscópio já é montado num minigame e depois vira só um item de progressão. Faça dele um **verbo permanente**: com o microscópio montado, segurar `C` faz a Lia observar — a tela ganha um círculo de foco (a vinheta do `Hint` já faz exatamente esse recorte radial) e, dentro dele, coisas invisíveis aparecem: uma plataforma de esporos na Fase 2, o ponto fraco coral do Dragão, um fragmento de pesquisa escondido numa parede.

*Por que encaixa:* dá payoff ao minigame do microscópio (hoje um beco sem saída narrativo) e materializa a lição da Rosalind Franklin que está no próprio diálogo dela: *"Olhe com atenção para o que os outros ignoram, Lia."* Custo de implementação: um `Surface` de máscara já pronto (`Hint._vignette`) e uma lista de objetos com flag `so_microscopio` lida do Tiled — zero código novo de parsing.

### 5.3 Inimigo: o Erro de Medição (Fase 2)
Um inimigo que **se duplica quando você erra o timing**. Ele fica parado piscando; acertá-lo no ritmo certo (durante o piscar, como um parry) o destrói; acertar fora do ritmo o divide em dois menores, cada um piscando mais rápido. Reaproveita quase 100% do `SlimeKing.CISAO` (fila `pending_spawns` + `Level._drain_pending_spawns`) e a janela de parry já implementada.

*Por que encaixa:* é a única mecânica do jogo em que **a punição por errar é o problema crescer**, que é exatamente o que acontece com erro sistemático em ciência. E cabe na Universidade, onde o tema é método.

### 5.4 Chefe: a Revisora por Pares (sala nova da Fase 2)
Um chefe que **não tem barra de vida** — tem uma barra de *convencimento*. Ela ataca com contra-argumentos (projéteis) que só podem ser respondidos com o **ataque à distância** (que já existe, e que o Dragão já força), e cada acerto preenche a barra. Mas se a Lia atacar corpo a corpo, a barra **desce**. O contraste com o Dragão (imune a corpo a corpo por força bruta) é temático: aqui você não vence pela espada porque *não se ganha discussão no grito*.

*Por que encaixa:* usa `melee_vulnerable` (já implementado), `active_hazards`/`parryable_hazards` (já implementados) e a barra de chefe do HUD com um rótulo diferente. Zero sistemas novos, e fecha o arco das cientistas com a única etapa do método científico que o jogo ainda não representa: a revisão por pares.

### 5.5 Minigame: a Réplica (Fase 3)
Você já tem dois minigames de arraste (`MicroscopeMinigame`, `EnergyBoxMinigame`) e uma `DragField` genérica. O terceiro fecha o método: **reproduzir um experimento**. A tela mostra o resultado de outra pessoa e uma bancada vazia; a Lia precisa repetir a mesma sequência de passos. Erre e o resultado sai diferente — e o jogo **não te pune**: mostra os dois lado a lado e pergunta "por que deu diferente?". Só depois de duas tentativas você recebe a peça.

*Por que encaixa:* reprodutibilidade é o coração do método científico e é o único pilar que o jogo ainda não jogou. Reaproveita `DragField` inteira.

### 5.6 Game feel — o que dá mais retorno por linha escrita

**(a) O tremor + poeira ao acordar o chefe** (já está no `IDEIAS_FUTURAS.md`). A infra de shake existe (`_trigger_shake`) e o `VFXManager` só precisa de uma entrada nova. É *a* coisa que falta para o momento de "a luta começou" existir. **~20 linhas.**

**(b) Câmera antecipatória.** `_update_camera` centra em `CAMERA_X_FOCUS = 0.42`. Deslocar o alvo mais uns 80 px na direção em que a Lia olha (interpolado, não instantâneo) faz o jogador ver para onde vai antes de chegar. É a mudança de game feel mais barata que existe num platformer: **3 linhas**.
```python
        look_ahead = 80 * (1 if self.player.facing_right else -1)
        target_x = self.player.x + look_ahead - WIDTH * CAMERA_X_FOCUS
```

**(c) Squash & stretch no pulo e no pouso.** Você já cacheia os 14 quadros da Lia; adicione uma escala não-uniforme de 3–5 quadros no instante do pulo (mais alta e fina) e do pouso (mais baixa e larga). Com os quadros pré-escalados no carregamento, custa **zero** por quadro.

**(d) Hit-stop no acerto comum, não só no parry.** `hitstop_timer` já existe e congela tudo. Dois quadros de congelamento em qualquer `take_hit` bem-sucedido transformam a sensação da espada. **1 linha** dentro de `check_enemies`.

**(e) Trilha de pó no dash.** `draw_dash_trail` desenha 3 retângulos azuis. Trocar por 2–3 partículas `dust` do `VFXManager` spawnadas ao longo do dash reaproveita arte que já existe e lê muito melhor.

**(f) Áudio: o que falta não é arquivo, é prioridade.** Do `PLANO_AUDIO.md`, os três efeitos que mais mudam a percepção do jogo com menos trabalho são `damage_sound`, `item_sound` e `boss_wake_sound` — os dois primeiros porque são os mais frequentes, o terceiro porque é o único momento do jogo hoje totalmente mudo em que algo dramático acontece.

### 5.7 Acessibilidade e qualidade de vida
O público é escolar e a apresentação é pública — vai ter gente jogando pela primeira vez, com o professor olhando.

- **Modo Pesquisador** (dificuldade): o dobro de vidas e telégrafos de chefe 50% mais longos. Um multiplicador em `HURT_DURATION`/`*_TELEGRAPH_DURATION` e em `STARTING_LIVES` — as constantes já estão todas nomeadas, é literalmente um dicionário de multiplicadores.
- **Velocidade de texto** nas Configurações: `DialogueBox.CHARACTERS_PER_FRAME` já é um atributo de instância, com opções "lento / normal / instantâneo".
- **Redução de tremor de tela**: um multiplicador global em `_shake_offset`. O Terremoto do Dragão sacode por **5 segundos** (`EARTHQUAKE_SHAKE_DURATION = 300`) — isso é desconfortável para muita gente e um problema real de acessibilidade vestibular. Colocar 0%/50%/100% nas Configurações é ~4 linhas.
- **Remapeamento de teclas**: hoje as teclas estão codificadas em `_read_input` e em `KeyboardState._KEYS`. Um dicionário `ACTION_KEYS` compartilhado pelos dois pontos de entrada resolveria — e é pré-requisito para quem joga só com uma mão.
- **Salvar progresso**: `audio_settings.json` já provou o padrão de persistência. Um `save.json` com `{fase, checkpoint, inventário, ranged_unlocked}` gravado a cada checkpoint transforma a experiência de quem tem 15 minutos por sessão. **É a melhoria de QoL com maior impacto e menor risco de todas.**
- **O menu de Configurações não tem como ser aberto durante o jogo** (`_settings_return_state` sempre é `TITLE`, e não existe menu de pausa). O código já está preparado — o comentário no próprio `game.py` diz isso. Falta o estado `PAUSED`.

---

## 6. As 5 ações de maior prioridade

**1. Restaurar os valores de combate.** `STARTING_LIVES = 5`, `STANDARD_ATTACK_POWER = 1`, e corrigir `_attack_box` para usar `player.dashing` em vez de comparar poderes. Sem isso, todo o resto da revisão é acadêmico: os quatro chefes que você construiu não existem em jogo. **~10 linhas, 15 minutos, impacto máximo.**

**2. Criar `Game.show_message()` e substituir os oito `message_timer = 0`.** Hoje o subtítulo de cada fase, todo item coletado e — o pior — o aviso de "faltam partes da pesquisa" são escritos e nunca desenhados. O jogador é empurrado de volta no fim da fase sem nenhuma explicação na tela. **~20 linhas.**

**3. Eliminar as três operações de tela cheia por quadro** (seção 3.3): remover os dois `fill()` e pré-compor a cor de cena nos fundos. **Medido: −52,7% na Fase 3, −54,7% na Fase 1, −61,3% na Fase 2.** É o único item da lista que resolve o lag de verdade, e não é onde a documentação suspeitava. **~30 linhas.**

**4. Neblina no tamanho nativo + carregamento sob demanda + apagar os 3 overlays mortos.** De 600 MB para cerca de **200 MB de RSS**, e o `Game()` deixa de gastar 2,7 s carregando 380 MB de quadros de um efeito que só a Fase 1 usa. **~25 linhas.**

**5. Repintar a Fase 1 com o tileset da escola** e, junto, os três consertos de mapa que a acompanham: `tilecount="120"` no `escola_tileset_64x64.tsx`, remover o import não usado de `fase3_pesquisa.tsx`, e mover o objeto `neblina` para depois do `rei_slime` (ou o chefe para antes da neblina). Hoje a fase-vitrine do jogo — a primeira que qualquer pessoa vai jogar na apresentação — é um campo de grama com 774 tiles de vila e 200 de escola, com o chefe nascendo atrás de uma parede opaca. **Não é código, é trabalho de Tiled, e é o que mais muda a primeira impressão.**

---

### Correções rápidas que valem entrar junto (< 5 minutos cada)
- `elevator_cutscene.py`: `elevador_lav_moldura.png` (typo) — a moldura existe e nunca foi desenhada.
- `dialogue.py`: calcular `overlay_height` pela proporção real do arquivo — a caixa de diálogo está achatada 52%.
- `game.py`: `_load_scaled_background` com fator inteiro (ou redesenhar os fundos em 480×270) — hoje 4,821×.
- Rodar `oxipng -o4 --strip safe` em `images/` e `maps/` — **−17% no mínimo, −50% nos tilesets, zero perda**.
- Apagar `build/web/snctjogo.apk` e `.tar.gz` do repositório (20 MB) e adicioná-los ao `.gitignore`.
- Carregar `seu_joaquim_idle.png` e dar sprite aos 4 moradores da vila — a arte de um deles já está pronta no disco há tempos.
