# Echoes of Life — revisão rápida para a apresentação

## Resposta de 60 segundos

Echoes of Life é um jogo de plataforma 2D em Python/Pygame. O desktop usa os hooks do
Pygame Zero e a web usa um loop assíncrono compatível com pygbag, mas os dois chamam o
mesmo núcleo. `Game` coordena a sessão e delega: `Player` controla movimento/animação,
`Level` monta o mundo a partir de mapas TMX, `CombatSystem` resolve ataques,
`InventorySystem` controla itens, `PuzzleSystem` guarda puzzles e `InteractionSystem`
trata portas, NPCs e diálogos. O código usa máquinas de estados, colisão AABB e máscaras
para rampas, culling por chunks, cache de imagens e save JSON validado com escrita atômica.

## O quadro completo

```text
entrada -> Game.update -> estado/modal -> _update_playing
        -> controles -> combate -> Level.update -> física/colisão
        -> eventos/coletas/progresso -> câmera
        -> Game.draw -> mundo -> Lia -> foreground/VFX -> HUD/overlays
```

## As responsabilidades

| Arquivo | Palavra-chave |
| --- | --- |
| `main.py` / `main_web.py` | plataforma e loop |
| `game.py` | orquestração |
| `player.py` | movimento/animação |
| `level.py` | mundo jogável |
| `tiled_map.py` | parser TMX |
| `combat.py` | ataques/dano/parry |
| `enemy_*.py` | máquinas de estados |
| `inventory.py` | itens/drops |
| `interactions.py` | E, portas e NPCs |
| `puzzles.py` / `minigame.py` | progresso e interface dos puzzles |
| `progress.py` | save validado/atômico |
| `audio.py` | fachada de áudio |
| `assets.py` | recursos e cache |

## Cinco explicações que você precisa dominar

### 1. Tecla até movimento

Teclado fornece booleanos -> `Player.read_controls` calcula direção -> aceleração altera
`vx` -> `Game.move_player` soma posição -> colisão corrige sobreposição -> câmera segue.

### 2. Ataque até morte/drop

F/clique gera pulso -> combo inicia -> apenas frames de impacto criam `attack_box` ->
`enemy.take_hit` -> estado `HURT` ou `DYING` -> inventário recebe notificação -> cria drop ->
colisão da Lia com pickup aumenta contagem.

### 3. Tiled até objeto interativo

TMX -> `TiledMap` lê XML/camadas/objetos -> `Level` converte tipo `porta` em rect + destino
-> E chama `InteractionSystem.use_doors` -> `Game.enter_room` preserva fase e carrega sala.

### 4. Estado até animação de chefe

Chefe começa dormente -> proximidade chama `wake_up` -> patrulha reduz cooldown -> padrão
escolhe ataque -> preparação avisa -> estado ativo cria hazard -> recuperação -> patrulha.

### 5. Save seguro

`Game` monta dicionário -> JSON é escrito em temporário -> temporário substitui original.
Na leitura, `decode_progress` valida tudo antes de alterar a sessão.

## Termos que podem perguntar

- **Game loop:** repetição de update e draw.
- **Máquina de estados:** comportamento escolhido pelo estado atual.
- **Composição:** `Game` contém sistemas especializados.
- **Herança:** inimigos comuns compartilham `GroundEnemy`.
- **Polimorfismo/duck typing:** combate aceita qualquer objeto com `alive`, `rect`, `take_hit`.
- **Debounce:** uma ação só na transição solta -> pressionada.
- **AABB:** colisão por retângulos alinhados aos eixos.
- **SAT:** detecta/separa polígonos por projeções nos eixos das arestas.
- **Culling:** ignora objetos fora da área relevante.
- **Chunk:** região espacial usada para agrupar tiles/sólidos.
- **Parallax:** fundo se move em velocidade diferente da câmera.
- **Cache:** reutiliza resultado caro já calculado.
- **Facade:** API simples de áudio escondendo o backend.
- **Escrita atômica:** o arquivo antigo só é trocado quando o novo está completo.
- **Data-driven:** conteúdo configurado nos mapas/tabelas em vez de código específico.

## Números úteis

- resolução lógica: 1920 × 1080;
- alvo: 60 FPS;
- 38 módulos Python principais;
- 13.646 linhas nos módulos de `jogo/`;
- 118 testes executados;
- 115 passando no estado atual;
- 3 falhas relacionadas a mapas/referências atuais;
- spritesheet da Lia: 97 quadros de 48 × 48;
- corpo lógico: 32 × 48; hitbox horizontal: 24 px;
- coyote time: 7 quadros; jump buffer: 7;
- combo: 16 quadros visuais, 4 janelas de impacto;
- vida: 5 corações; mob tira 0,5; chefe tira 1.

## Estado atual dos testes

Não diga que tudo passa. As falhas atuais são:

1. arena/plataforma do Golem mudou no mapa da vila;
2. Cadu não está antes do primeiro slime conforme a referência do teste;
3. hashes visuais dos mapas não correspondem às referências antigas.

Isso é compatível com os mapas atualmente modificados. A decisão correta depende de saber
se o layout novo é intencional; não se atualiza teste visual cegamente.

## Respostas curtas para armadilhas

**“Por que não está tudo em `Game`?”**  
Porque combate, itens, puzzles e interações têm responsabilidades e ritmos de mudança
diferentes. `Game` coordena, os sistemas executam suas regras.

**“`dt` controla toda a física?”**  
Não. Alguns elementos usam tempo real, mas muitas regras de gameplay usam timers em quadros
e pressupõem 60 FPS. É uma limitação/evolução possível que eu sei identificar.

**“A imagem da personagem é a colisão?”**  
Não. A arte é maior; a hitbox lógica é menor e acompanha o corpo.

**“O mapa é imagem?”**  
Não. TMX contém camadas, colisão, propriedades e entidades.

**“Como o jogo aceita inimigos diferentes?”**  
Por interface comum: `alive`, `rect`, `take_hit`, mais capacidades opcionais via `getattr`.

**“Por que parry vem antes do dano?”**  
Para cancelar o hazard antes que a checagem seguinte possa ferir Lia no mesmo quadro.

**“Qual melhoria você faria?”**  
Dividir mais `Game`/`Level`, padronizar timers em segundos quando apropriado e versionar
mais progresso de puzzles no save.

## Checklist final

- [ ] Consigo explicar onde o programa começa.
- [ ] Consigo narrar um quadro completo.
- [ ] Consigo explicar coyote time e jump buffer.
- [ ] Consigo explicar ataque, parry, dano e drop.
- [ ] Consigo desenhar estados de um chefe.
- [ ] Consigo seguir uma porta do TMX até a troca de sala.
- [ ] Consigo diferenciar dado persistente de transitório.
- [ ] Consigo explicar chunks, cache e snapshot de menu.
- [ ] Sei falar honestamente sobre os três testes atuais.
- [ ] Consigo responder sem repetir nomes decorados: explico causa e efeito.

Para aprofundar qualquer item, use `GUIA_ESTUDO_CODIGO.md`.
