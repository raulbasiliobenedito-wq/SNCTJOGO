# Echoes of Life — o que ficou de fora desta rodada (propostas para aprovação)

Estes quatro itens foram deliberadamente **não implementados**: risco de
regressão ou de decisão errada sem supervisão visual. Abaixo, o que eu
faria em cada um, para você aprovar antes.

---

## 1. Repintura da Fase 1 no Tiled

### O diagnóstico, agora com números

`fase1_escola.tmx` tem 242×46 tiles de 32px (7744×1472 px). O que está pintado hoje:

| camada | tiles do `escola_tileset_64x64` | tiles de `chao_vila` (grama) | tiles de `aderecos_vila` |
|---|---:|---:|---:|
| `Fundo` | 596 | **1.076** | 10 |
| `Colisão` | 200 | **774** | 0 |
| `Decoração` | 10 | 0 | 5 |
| `Frente` | 15 | 99 | 9 |
| `Perigos` | 0 | 0 | 0 |

Ou seja: **79% do chão da "escola" é grama de vila**. Isso não é um erro de
digitação — é o que acontece quando se pinta terreno de teste pra validar
colisão e ele acaba virando o mapa final. O tileset da escola
(`escola_tileset_TILED_64x64_FINAL.png`, 256×480 = 120 tiles de 32px) está
importado e mal usado.

### Por que eu não faço isso sozinho

Trocar 1.850 IDs de tile por regra automática ("todo tile de grama vira
tile de piso") produziria um mapa sintaticamente válido e visualmente
sem sentido: o tileset da escola tem bordas, quinas e transições que só
funcionam se colocadas na orientação certa, e nenhuma regra cega sabe
onde é "quina interna esquerda" contra "meio de parede". Precisa de olho.

### O que eu proponho

**Passo 1 — mapear o tileset (eu faço, 20 min).** Gero uma imagem de
referência com os 120 tiles numerados em grade, pra você (e eu) poder
dizer "tile 37" em vez de "aquele bloco de piso". Sem isso qualquer
conversa sobre repintura é imprecisa.

**Passo 2 — você decide a régua (5 min de conversa).** Preciso de três
respostas:
- A Fase 1 é **corredor interno de escola** (piso + parede + janelas) ou
  **pátio ao ar livre** (a grama fica, e a escola aparece ao fundo)? Hoje
  o mapa está no meio do caminho, e o fundo em uso é o `ceu.png` — o que
  sugere pátio, não corredor.
- O laboratório subterrâneo (y ≈ 950–1180) usa o tileset da escola ou o
  `fase2_laboratorio_sala.tsx`, que já tem cara de laboratório?
- A `Frente` (99 tiles de grama hoje) deve virar o quê — grades, arbustos
  de primeiro plano, moldura de porta?

**Passo 3 — repintura assistida (eu faço, ~1h).** Com a régua definida,
faço a troca por REGIÃO, não por regra global: divido o mapa nos 6
trechos do `PLANO_FASE1.md` (entrada, átrio, elevadores, laboratório,
corredor 2, ginásio) e trato um por vez, gerando um PNG do trecho depois
de cada um pra você aprovar antes de eu seguir. Reverto trecho por trecho
se algum não ficar bom.

**Passo 4 — recalibrar `Game.UNDERGROUND_Y`** (hoje 780, herdado do mapa
antigo) com o Y real do laboratório depois da repintura. Isso é o item 1
da lista "coisa de código que ainda vai precisar de ajuste" do
`PLANO_FASE1.md`, e só dá pra fazer depois do passo 3.

**Antes de tudo isso, um item de 5 minutos que vale mais que a repintura
inteira:** a `Colisão` da Fase 1 tem 974 tiles, e a camada `Perigos` está
vazia. Se a intenção era ter espinhos/queda no corredor, isso nunca foi
pintado — vale conferir antes de investir na parte estética.

---

## 2. As duas refatorações grandes

Não entraram porque, do jeito que você pediu (incrementais, rodando o
jogo entre cada passo), cada uma é uma sessão inteira — e o retorno é de
manutenção, não de jogo. Ordem que eu recomendo:

### 2a. `Level.draw()` 34 parâmetros → objeto `Assets` (~2h, risco baixo)
Hoje `radon` marca **D (27)**. O caminho incremental, sem nenhum passo
que quebre o jogo:
1. Criar `assets.py` com uma dataclass `Assets` que só GUARDA o que
   `Game._load_assets` já carrega (nenhuma lógica nova).
2. `Game` passa a montar um `Assets` no fim de `_load_assets`, mantendo
   os atributos antigos como `property` que apontam pra ele. Nada quebra.
3. `Level.draw` ganha um parâmetro `assets=None`; enquanto for `None`,
   usa os 34 argumentos antigos. Migrar UM consumidor por vez.
4. Quando todos migrarem, apagar os 34 parâmetros e as `property` de
   compatibilidade.

Já fica meio caminho andado: a escada de 9 `isinstance()` em `Level.draw`
vira um laço de 3 linhas se cada classe de inimigo expuser
`SPRITE_KEY = "slime_king"`. Isso dá pra fazer **isolado, em 20 minutos**,
e é o pedaço com melhor relação ganho/risco dos dois.

### 2b. `GroundEnemy` / `Boss` em `enemy.py` (~4h, risco médio)
`Slime`, `CrystalStag`, `PossessedStudent`, `JanitorGuardian` e
`SmallSlime` são cinco cópias do mesmo esqueleto; os 4 chefes repetem
outro. São ~700 linhas de duplicação — e ela já mordeu: `GROUND_LIFT` foi
corrigido de 3 para 9 no `Slime` e as outras quatro classes ficaram com o
valor antigo.

Caminho seguro: criar `GroundEnemy` com o corpo do `Slime`, fazer **só o
`SmallSlime`** herdar dela (é o mais simples), rodar o jogo, e só então
migrar um inimigo por vez. Cada passo é reversível sozinho. Os chefes
depois, na mesma cadência.

**Recomendação honesta:** faça 2a (e principalmente o `SPRITE_KEY`)
antes da apresentação; deixe 2b pra depois. 2b é dívida técnica real,
mas não muda nada que alguém vá ver jogando.

---

## 3. As cinco ideias de design — versão curta

| Ideia | O que muda tecnicamente | Arquivos | Esforço | Depende de arte nova? |
|---|---|---|---|---|
| **Caderno de Campo** | Novo estado `NOTEBOOK` (mesmo padrão de pausa do `Hint`); um dict `padroes_vistos` persistido no `save.json`; contador de quantas vezes cada golpe acertou a Lia, incrementado em `_check_enemy_attack_hazards`; ao chegar a 3, marca o padrão como "anotado" e `<Boss>.draw` passa a desenhar contorno na fase de telégrafo | `game.py`, `enemy.py`, `hud.py` (ou um `notebook.py` novo) | **~6h** | Não — texto + o contorno é `pygame.draw` |
| **Microscópio como lente** | Tecla `C` segura → reaproveita `Hint._build_vignette` como máscara de recorte; objetos do Tiled com propriedade `so_microscopio="true"` só desenham/colidem enquanto a lente está ativa | `game.py`, `level.py`, `tiled_map.py` (nenhum parsing novo — a propriedade já é lida) | **~4h** | Não |
| **Erro de Medição** (inimigo) | Classe nova em `enemy.py`: máquina de estados de 3 estados + fila `pending_spawns` (a infra de spawn já existe e agora é segura, ver correção 2.14) | `enemy.py`, `level.py` (1 linha em `_make_tiled_enemies`), 1 objeto novo no `.tmx` | **~5h** | Sim — 1 folha de sprite (idle + piscar + dividir) |
| **Revisora por Pares** (chefe) | Classe de chefe nova; a "barra de convencimento" é a barra de chefe existente com rótulo trocado; `melee_vulnerable=False` permanente (igual ao Dragão) e `take_hit` com sinal invertido pro corpo a corpo | `enemy.py`, `game.py` (2 linhas em `BOSS_NAMES`/`BOSS_MUSIC`), 1 `.tmx` novo | **~10h** | Sim — folha de chefe + sala nova no Tiled |
| **Minigame Réplica** | Terceira subclasse de `_BaseMinigame` reaproveitando `DragField` inteira; a comparação "seu resultado × o resultado dela" é dois `blit` lado a lado | `minigame.py`, `game.py` (1 handler em `_finish_minigame`) | **~6h** | Parcialmente — reaproveita as peças do microscópio |

**Se eu tivesse que escolher uma:** o **Caderno de Campo**. É a única que
mexe na tese do jogo (a frase da mãe sobre errar e tentar de novo) em vez
de acrescentar conteúdo lateral, não depende de nenhuma arte nova, e
resolve de graça o problema de dificuldade dos chefes — o jogador fica
melhor porque aprendeu, não porque o jogo foi nerfado.

**Se o critério for tempo até a apresentação:** o **Microscópio como
lente** é o mais barato dos cinco e dá payoff a um minigame que hoje é um
beco sem saída narrativo.

---

## 4. Documentação

Corrigi **só os fatos errados** (`IDEIAS_FUTURAS.md` e `PLANO_VILA.md`):
o `parry_flash.png` que já existia, o tamanho real de
`vila_casas_completo.png`, o estado dos NPCs da vila, e uma seção nova
listando o que mudou nesta rodada. **Não toquei em prioridade de trabalho
futuro** — o que o `PLANO_FASE1.md` diz sobre o que fazer primeiro
continua sendo sua decisão.
