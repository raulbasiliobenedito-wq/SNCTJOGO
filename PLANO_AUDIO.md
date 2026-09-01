# Plano de áudio — Echoes of Life

## Como funciona (já está tudo pronto no código)

O jogo já sabe tocar tudo isso — só falta os arquivos. Coloque cada
música em `music/<nome>.mp3` (pode ser o .mp3 exportado direto do Suno,
sem converter nada — `ogg`/`wav` também funcionam se preferir) e cada
efeito em `sounds/<nome>.wav` ou `.mp3` (esses dois nomes de pasta são
fixos, o Pygame Zero carrega neles sozinho, sem precisar registrar em
lugar nenhum do código).

Convenção de nome (a que o Raul já começou a usar): música
`<nome>_music`, efeito `<nome>_sound` — com algumas exceções curtas
(`jump`, e a pasta `punch/` com 4 variações, ver abaixo).

Enquanto um nome não tiver arquivo, o jogo simplesmente não toca nada
ali — sem travar, sem erro (ver `audio.py`). Dá pra ir soltando os
arquivos aos poucos, um de cada vez, e testando.

`music/` troca sozinho conforme o estado do jogo (fase atual, sala,
chefe acordado, vitória/derrota — ver `Game._desired_music_track` em
game.py). `sounds/` toca pontualmente a cada ação (pulo, dano, item
etc.) — já está todo plugado nos lugares certos do código.

## ✅ Já adicionados

- `music/fase_1_music.mp3`
- `music/rei_slime_music.mp3`
- `sounds/jump.wav`
- `sounds/projectile_sound.wav`
- `sounds/punch/punch_1.mp3` … `punch_4.mp3` (uma pra cada hit do combo
  corpo a corpo — `Game._update_attack` já escolhe a certa sozinho pelo
  número do golpe)
- `sounds/earthquake_dragon_sound.mp3` — já ligado! Toca no instante em
  que o Dragão bate no chão no ataque Terremoto (junto com o shake de
  câmera, ver `Game._check_boss_shake_events` em game.py)
- `music/vila_music.mp3` — já ligado! Toca assim que a Lia entra na vila
  (ver PLANO_VILA.md)

## Trilhas (music/) — Suno

Todas devem ser **instrumentais** (sem letra) — no Suno, ative a opção
"Instrumental" antes de gerar, ou inclua `[Instrumental]` no prompt.
Duração ideal: 1-2 minutos, já que elas tocam em loop automático
(`music.play`, ver audio.py) — não precisa ser longa.

Pedido do Raul: nada de synth cinematográfico/sombrio — o som tem que
"parecer de um jogo de pixel art", chiptune de verdade (8/16-bit, NES/
SNES), mesmo nas cenas mais tensas. Prompts abaixo já ajustados nessa
linha.

| Arquivo | Cena | Prompt sugerido pro Suno |
|---|---|---|
| `menu_music.mp3` | Título/menu principal | `[Instrumental] Upbeat retro chiptune title screen theme, cheerful square-wave melody, bright arpeggiated synth backing, light punchy percussion, mid tempo, welcoming and hopeful, classic 16-bit platformer menu music, catchy and loopable` |
| `intro_music.mp3` | Cutscene inicial (mãe de Lia no hospital) | `[Instrumental] Gentle 8-bit chiptune, soft melancholic but tender melody, simple sine/triangle wave lead, slow tempo, quiet hospital scene, nostalgic SNES-era RPG emotional theme, minimal percussion, warm and hopeful undertone` |
| ✅ `fase_1_music.mp3` | Fase 1 — Escola (exploração) | — |
| `fase_2_music.mp3` | Fase 2 — Universidade (exploração) | `[Instrumental] Energetic retro chiptune platformer theme, confident square-wave melody, driving arpeggio bassline, punchy drums, mid-fast tempo, university/campus adventure feel, classic 16-bit exploration music, catchy and loopable` |
| `fase_3_music.mp3` | Fase 3 — Caverna (exploração) | `[Instrumental] Upbeat retro chiptune platformer theme, catchy 8-bit melody with bouncy square-wave lead, playful arpeggiated synth bassline, light punchy percussion, mid-fast tempo around 130 BPM, adventurous and curious mood, cave/underground exploration but fun and energetic, classic 16-bit era game soundtrack, NES/SNES style, memorable hook that repeats` |
| `laboratorio_music.mp3` | Sala do laboratório velho (Fase 2) | `[Instrumental] Quirky retro chiptune, sci-fi laboratory theme, playful but slightly unsettling arpeggiated synth, bouncy bassline, light mechanical percussion, mid tempo, curious and mysterious, classic 16-bit game soundtrack, not scary — mischievous tension` |
| `biblioteca_music.mp3` | Sala da biblioteca (Fase 2) | `[Instrumental] Quiet mysterious chiptune, soft melodic square-wave lead, gentle arpeggio backing, slow tempo, ancient library atmosphere, classic 16-bit RPG exploration theme, subtle wonder rather than dread` |
| ✅ `rei_slime_music.mp3` | Luta: Rei Slime (Fase 1) | — |
| `bibliotecario_music.mp3` | Luta: Bibliotecário (Fase 2) | `[Instrumental] Intense retro chiptune boss battle theme, driving square-wave melody, fast arpeggiated bassline, punchy energetic percussion, dramatic but playful, classic 16-bit platformer boss fight music, exciting not scary` |
| `especime_music.mp3` | Luta: Espécime (Fase 2) | `[Instrumental] Fast erratic retro chiptune boss battle, aggressive square-wave stabs, glitchy playful arpeggios, energetic percussion, body-horror unease but still classic 8-bit game style, tense and exciting, not dark or cinematic` |
| `dragao_music.mp3` | Luta: Dragão (Fase 3) | `[Instrumental] Epic but bright retro chiptune final boss battle, powerful square-wave lead melody, fast driving arpeggiated bassline, heavy punchy percussion, triumphant and climactic energy, classic 16-bit era platformer final boss music, intense and exciting, not dark or orchestral` |
| `vila_music.mp3` | Vila (prólogo antes da Fase 1, ver PLANO_VILA.md) | `[Instrumental] Warm cozy 8-bit chiptune village theme, gentle bouncy square-wave melody, simple friendly arpeggio backing, light percussion, relaxed mid tempo, homely and safe feeling, classic 16-bit RPG town music, welcoming before an adventure, catchy and loopable` |
| `vitoria_music.mp3` | Tela de conclusão | `[Instrumental] Triumphant upbeat chiptune fanfare, bright square-wave melody, warm and joyful, mid tempo, classic 16-bit victory theme, satisfying and celebratory, short loopable` |
| `derrota_music.mp3` | Tela de game over | `[Instrumental] Classic 8-bit NES-style game over jingle, simple descending square-wave melody, sad but short, triangle-wave bass, no reverb or cinematic effects, dry chiptune sound, reminiscent of old Mega Man/Mario game over themes, slow tempo, brief and reflective, loopable` |

## Efeitos (sounds/) — atenção, Suno NÃO é a ferramenta certa aqui

Suno gera **músicas**, não efeitos curtos de ação (pulo, hit, clique de
UI) — ele tende a devolver algo que ainda soa como um trecho de música,
não um "blip" seco de jogo. Pra esses eu recomendo:

- **jsfxr** (https://sfxr.me) ou **bfxr** (https://www.bfxr.net) — geradores
  gratuitos de efeito estilo 8-bit direto no navegador, encaixam perfeito
  no visual pixel art do jogo, e exportam `.wav` já pronto.
- **freesound.org** — banco de efeitos prontos (checar licença de cada um).

Uma exceção: `correct_sequence_sound`, `microscope_sound`,
`boss_death_sound` e "stings" curtos tipo `vitoria_music` (2-3 segundos,
um acorde/fanfarra rápida) o Suno consegue gerar razoavelmente bem — é
só pedir um trecho curto e cortar.

| Arquivo | Quando toca | Sugestão |
|---|---|---|
| ✅ `jump.wav` | Lia pula | — |
| `dash_sound.wav` | Dash | jsfxr — preset "Random"/whoosh curto |
| ✅ `punch/punch_1.mp3` a `punch_4.mp3` | Cada hit do combo corpo a corpo (1º ao 4º) | — |
| ✅ `projectile_sound.wav` | Disparo do ataque à distância | — |
| `damage_sound.wav` | Lia toma dano | jsfxr — "Hit/Hurt" |
| `shield_sound.wav` | Escudo absorve o dano | jsfxr — "Blip/Select" mais metálico |
| `death_sound.wav` | Lia morre (vida chega a 0) | jsfxr — "Explosion" curto e abafado |
| `parry_sound.wav` | Parry bem-sucedido | jsfxr — "Hit/Hurt" agudo e nítido |
| `item_sound.wav` | Pega item/pesquisa/achado/peça do microscópio | jsfxr — preset "Pickup/Coin" |
| `checkpoint_sound.wav` | Novo checkpoint ativado | jsfxr — "Powerup" curto |
| `door_sound.wav` | Entra/sai de uma porta | jsfxr — "Blip/Select" grave |
| `lever_sound.wav` | Puxa qualquer alavanca (elevador ou painel) | jsfxr — "Click/mechanical" |
| `button_sound.wav` | Aperta um botão certo da sequência | jsfxr — "Blip/Select" |
| `correct_sequence_sound.wav` | Sequência do painel concluída | Suno (sting curto) ou jsfxr "Powerup" |
| `wrong_sequence_sound.wav` | Sequência errada, painel reinicia | jsfxr — "Hit/Hurt" descendente |
| `microscope_sound.wav` | Microscópio montado na bancada | Suno (sting curto) ou jsfxr "Powerup" longo |
| `enemy_hit_sound.wav` | Inimigo comum toma hit e sobrevive | jsfxr — "Hit/Hurt" curto |
| `enemy_death_sound.wav` | Inimigo comum morre | jsfxr — "Explosion" curto |
| `boss_hit_sound.wav` | Chefe toma hit e sobrevive | jsfxr — "Hit/Hurt" mais grave/pesado |
| `boss_death_sound.wav` | Chefe morre | Suno (sting curto) ou jsfxr "Explosion" grande |
| `boss_wake_sound.wav` | Chefe acorda (Lia se aproxima) | jsfxr — "Powerup"/rugido curto |
| `dialogue_sound.wav` | Cada avanço de texto no diálogo | jsfxr — "Blip/Select" bem curto e discreto |
| `select_sound.wav` | Começar jogo / reiniciar (tela de título e fim de jogo) | jsfxr — "Blip/Select" |
| ✅ `earthquake_dragon_sound.mp3` | (reservado — Dragão será refeito) | — |

## Prioridade sugerida (se quiser continuar por menos)

1. ~~`menu`, `fase1`, `chefe_rei_slime`~~ → já tem `fase_1_music` e
   `rei_slime_music`; falta só `menu_music`, `vitoria_music` e
   `derrota_music` pra fechar o ciclo completo de jogar a Fase 1 do
   início ao fim com música.
2. ~~`pulo`~~/`ataque` → já tem `jump` e os 4 `punch`; falta
   `damage_sound` e `item_sound`, os 2 efeitos mais frequentes que
   restam.
3. O resto, aos poucos, na ordem que preferir — nada quebra por faltar.
