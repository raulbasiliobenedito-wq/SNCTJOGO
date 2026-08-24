# Ideias futuras (ainda não implementadas)

Lista viva de pedidos do Raul que ficaram pra depois — cada um vira uma
tarefa quando ele disser "vamos fazer X".

## Acordar do chefe: tremor de tela + poeira do teto

Pedido do Raul (guardado pra usar mais tarde, ainda não implementado):
quando o chefe acorda (ver `enemy.py` DORMANT/`wake_up` e
`Game._maybe_wake_bosses`), a tela deveria tremer e partículas de poeira
deveriam cair do teto — clima de masmorra desabando, reforçando o "a luta
começou pra valer" do momento em que ele sai do estado dormente.

Ideia de implementação (não decidida ainda): screen shake de curta duração
(uns 12-20 quadros, decaindo) disparado dentro de `wake_up()`/no ponto em
que `Game._maybe_wake_bosses` chama `wake_up()`, mais um novo tipo de
partícula na VFXManager (`vfx.py`) — "dust_fall" ou parecido — spawnada em
vários pontos aleatórios ao longo do topo da arena, caindo devagar com
leve variação de x (poeira/entulho, não um efeito de impacto).

## Outras ideias já sugeridas, ainda sem dono

- Fase de fúria abaixo de 50% de vida do chefe (ataques mais rápidos/
  frequentes).
- Segunda habilidade depois da Fase 2 (Raul disse "talvez" em algum
  momento, nunca confirmou).
- Reformular a morte da Lia: cair no vazio derruba ela no chão por ~5s,
  levanta com ~5s de invulnerabilidade piscando, e o respawn passa a ser
  na última plataforma pisada em vez do checkpoint fixo.

## Concluído recentemente

- **Sprite nova da Lia + combo + pulo de 3 fases + morte animada**: troca
  completa (pedido do Raul, sheet desenhada por ele no Aseprite a partir de
  uma referência gerada por IA) — `images/player/player_sheet.png` agora
  tem 14 quadros de 64x96 (o dobro do 32x48 antigo, `settings.py` ajustado
  junto: `PLAYER_WIDTH/HEIGHT/HITBOX_WIDTH/HITBOX_OFFSET_X` todos
  dobraram). Como a arte nova já vem com contorno desenhado à mão,
  `Player` não gera mais contorno em tempo real (removido
  `_make_outline`/`OUTLINE_COLOR`/`OUTLINE_OFFSETS`, dobraria a borda).
  Novo em `Player.animate()`: pulo de 3 fases (subindo/no ar/caindo,
  frames 5-7) usando o novo `Player.grounded` (espelhado por
  `Game.move_player` a cada quadro, ver comentário lá) em vez de só o sinal
  de `vy`. Novo em `game.py`: combo de 4 hits corpo a corpo
  (`combo_count`/`combo_timer`, frames 8-11 — `Game._apply_attack_frame`
  sobrepõe o frame calculado por `animate()` enquanto `attack_timer` tá
  ativo) que reseta se ficar mais que `COMBO_RESET_WINDOW` sem atacar de
  novo (pedido do Raul, era a opção "recomendada" nas 3 que perguntei); o
  4º hit da `COMBO_FINISHER_POWER = 2` de dano, igual o ataque de dash. O
  círculo genérico que representava o ataque (`draw_attack`) foi removido
  — os frames de verdade já mostram o golpe. Morte também ganhou pose:
  `Game.death_pose_timer` (`DEATH_POSE_DURATION = 24` quadros) congela a
  simulação — mesmo padrão do hit-stop do parry — mostrando os frames
  12-13 parada no lugar onde ela morreu, só reposicionando (checkpoint ou
  saída de sala) depois, via `Game._finish_respawn` (a parte antiga de
  `respawn()` que fazia isso na hora).
  **Não verificado ainda (preciso rodar o jogo, que não dá daqui):** a
  cutscene de abertura (`cutscene.py`) escala o frame da Lia por 3x
  dinamicamente a partir do tamanho real do frame — com o dobro do tamanho
  de sprite, ela deve aparecer bem maior lá agora; se ficar grande demais,
  o ajuste é só trocar esse `* 3` por algo menor. Também vale playtestar o
  tamanho da hitbox nova (48px) contra vãos/inimigos apertados que foram
  calibrados pro hitbox antigo de 24px.
- **Feedback do parry**: hit-stop (`Game.hitstop_timer`, 3 quadros — a
  simulação inteira congela em `_update_playing`, ver o `if
  self.hitstop_timer` logo no topo) + screen shake genérico
  (`_trigger_shake`/`_update_shake`/`_shake_offset`, decai de
  `PARRY_SHAKE_MAGNITUDE=6` até 0 em `PARRY_SHAKE_DURATION=14` quadros,
  só desloca o mundo — a HUD nunca treme) + 1s de invencibilidade real
  (`PARRY_INVULN_FRAMES = FPS`, reaproveita `self.invuln_timer`, `max()`
  pra nunca encurtar um invuln maior já em andamento) pra sobreviver ao
  resto de um ataque com vários hits (ex.: as 5 lâminas do Bibliotecário)
  depois de aparar só o primeiro. A mesma infra de shake já fica pronta
  pra a ideia guardada do tremor ao acordar o chefe, logo abaixo.
- **Área de patrulha do Bibliotecário e do Espécime**: bug real (não só
  achismo do Raul) — o objeto "bibliotecario"/"especime" no Tiled definia
  uma faixa bem mais estreita que a sala inteira (320px/288px numa sala de
  2048px/1920px), então fora dessa faixa o chefe simplesmente não tinha
  como alcançar a Lia (`_patrol` trava dentro dos limites do próprio
  objeto — não é um problema de direção/`face_player`, é a área mesmo).
  Alargado direto no `.tmx` (`maps/fase2_biblioteca_sala.tmx` e
  `maps/fase2_laboratorio_sala.tmx`, objeto `bibliotecario`/`especime` na
  camada Entidades): Bibliotecário agora vai de x=800 a x=2016 (perto da
  parede direita); Espécime de x=350 a x=1888. Dois limites por um motivo
  de verdade, não capricho: na biblioteca há um buraco real no chão
  (x=704-768, todas as 3 linhas de colisão vazias) — não dá pra estender
  até a porta sem o chefe "flutuar" sobre o buraco, por isso o lado
  esquerdo para logo depois dele; nos dois casos também parei antes da
  posição da cientista (Ada Lovelace/Marie Curie, x=250) pra ele não
  patrulhar por cima dela. Ainda sobra uma faixa perto da porta/spawn onde
  a Lia consegue ficar fora de alcance — se quiser fechar esse buraco no
  Tiled, dá pra alargar ainda mais depois.
- **Parry/desvio de ataques**: implementado. Timing é o próprio ataque
  corpo a corpo [F] (`Game._attack_box`, sem botão novo) acertando um
  hazard "aparável" (`<Boss>.parryable_hazards` em `enemy.py`,
  `Game._check_parries` em `game.py`) — só projéteis/objetos que voam:
  pedras/meteoros do Dragão (só fase "falling") + Sopro enquanto varre,
  tomos mergulhando + lâminas do Bibliotecário, jato do Espécime (só
  janela de 6 quadros de JET_ACTIVE — o mais apertado do jogo). Ondas no
  chão (Silêncio/Esmagar) e investidas corpo a corpo nunca são aparáveis;
  Rei Slime não tem nenhum hazard aparável. Sucesso: destrói o hazard
  específico e devolve `PARRY_DAMAGE = 3` de dano real no chefe (mais que
  o ataque padrão e o de dash), via `enemy.take_hit` direto — mesma
  interface que o ataque à distância já usa pra furar `melee_vulnerable`.
  VFX: `vfx.py` ganhou a entrada `"parry_flash"` (folha dedicada
  `vfx/parry_flash.png`) — `VFXManager` agora ignora sozinho uma folha
  extra que ainda não existe no disco, então nada quebra enquanto o Raul
  não salvar o arquivo aprovado na conversa (star-burst sem o círculo).

## Em andamento

- Nada no momento.
