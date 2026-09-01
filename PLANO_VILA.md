# Plano da Vila — prólogo antes da Fase 1

## ✅ Já implementado (código + mapa)

O `maps/vila.tmx` (150x20 tiles, 4800x640px) já existe, com chão, 2 casas de
frente + 2 casas de fundo intercaladas, adereços (árvores, poste, banco,
poço, canteiro, placa, cerca) e as 4 NPCs abaixo posicionadas. O código já
está ligado: `TÍTULO → INTRO (hospital) → VILA → Fase 1` funciona, o diálogo
em 3 falas da Sra. Amélia avança sozinho a cada [E], e chegar na ponta
direita da rua leva pra Fase 1 automaticamente (mesmo mecanismo de "fim de
fase" que as outras já usam).

**Falta só isso pra ficar redondo:**
- Arte própria das 4 NPCs da vila — hoje elas são invisíveis (sem sprite
  próprio, só a hitbox/diálogo), porque não existe ainda uma folha de sprite
  pra elas (as cientistas têm `cientistas_idle.png`; a vila não tem
  equivalente). Dá pra jogar e conversar com elas normalmente, só não
  aparecem desenhadas. Quando quiser, eu peço um prompt de sprite sheet
  pra isso.
- `music/vila_music.mp3` (prompt já no PLANO_AUDIO.md) — até lá toca
  silêncio nessa cena, sem travar nada.
- O layout do `.tmx` foi montado por mim direto em XML (sem abrir o Tiled) —
  vale abrir o arquivo no Tiled pelo menos uma vez pra conferir visualmente
  se casas/adereços/chão encaixaram do jeito esperado antes de testar
  in-game, e ajustar posições à vontade (é só editar e salvar).


## Onde ela entra na sequência (proposta — me avisa se quiser diferente)

`TÍTULO → INTRO (mãe revela o câncer, cena que já existe) → VILA (nova) → Fase 1 (Escola)`

Coloquei a vila **depois** da cena do hospital, não antes. Se ela vier antes,
a NPC perguntando "é verdade que sua mãe está com câncer?" estraga a revelação
que a própria cena do hospital entrega com mais força (o brilho coral, a fala
da mãe, `MOTIVATION`). Depois da revelação, a mesma pergunta funciona melhor:
é a vizinhança já sabendo, comentando, te apoiando — e é aí que a vila também
serve de tutorial natural, porque é a primeira vez que a Lia anda livre pelo
mundo (a cena do hospital é estática). No fim da vila, um caminho pra floresta
leva direto pra Fase 1, do jeito que hoje o fim da INTRO leva.

## Assets — conferidos, todos batem com o pedido

Os 4 pacotes que você extraiu em `images/village/{chao,casas,interior,aderecos}/`
foram olhados um por um (imagem final + LEIA-ME técnico de cada). Tudo consistente
entre si — mesma régua de alinhamento em todos:

- **Chão** (`chao/chao.png`, 128×128, grade 4×4 de **32×32**): grama, terra,
  caminho, transições grama↔caminho, variações (flores/pedrinhas/tufo). Topo
  sólido (colisão) é **y 0** de qualquer tile da linha 0 ou 2 — não ondula, de
  propósito, pra não balançar quem anda em cima.
- **Casas** (`casas/vila_casas_completo.png`, 256×128, grade **64×64**, linha 0
  = 4 frentes, linha 1 = os mesmos 4 fundos): tijolo, amarela, azul, creme.
  Base útil (onde encosta no chão) é **y 62** do quadro — sem chão embutido de
  propósito. Frente e fundo compartilham essa mesma base e a mesma linha de
  beiral (y 25), *desenhadas pra serem a mesma casa vista dos dois lados*.
- **Adereços** (`aderecos/aderecos.png`, 256×192, grade 4×3 de **64×64**): 3
  árvores, poste, 2 arbustos, banco, poço, placa, canteiro, cerca + ponta.
  Mesma base y 62 (fórmula do LEIA-ME: `y = topo_do_terreno − 63`).
- **Interior** (`interior/interior.png`, 144×144, grade 3×3 de **48×48**): cama,
  mesa+cadeiras, estante, tapete, janela, luminária, armário, quadro, vaso.
  **Não vou usar isso agora** — é pra quando/se as casas forem entráveis. Nesta
  primeira versão as casas são só cenário (as NPCs ficam do lado de fora),
  então fica reservado pra depois da entrega.

Todos os quatro pedem escala só em múltiplos inteiros + filtro nearest
neighbor — o carregador do jogo (`_load_grid_sheet`) já faz isso.

## Como isso entra no Tiled (o que você precisa montar)

O motor só lê **camadas de tile** pra desenhar cenário (não objetos soltos com
imagem — objetos no Tiled aqui só carregam posição/tamanho/tipo, sem arte).
Então casas, adereços e chão viram **tilesets pintados em camadas**, do mesmo
jeito que o chão da Fase 3. Três tilesets novos pra importar:

1. **`chao_vila`** — de `chao/chao.png`, tile 32×32.
2. **`casas_vila`** — de `casas/vila_casas_completo.png`, tile 64×64 (8 tiles:
   os 4 de cima são frente, os 4 de baixo são fundo).
3. **`aderecos_vila`** — de `aderecos/aderecos.png`, tile 64×64 (12 tiles).

Mapa novo: `maps/vila.tmx`, grade base **32×32** (mesma do chão — as casas e
adereços de 64×64 só ocupam 2×2 células quando pintados, sem problema).

Camadas (mesmos nomes/convenção da Fase 1):

- **`Colisão`** (`colisao=true`) — pinte o chão de verdade aqui (`grama_meio`,
  `caminho_meio`, etc.) numa fileira só, sem buraco. É essa fileira que
  vira o piso onde a Lia anda.
- **`Decoração`** — tudo que fica **atrás** da Lia: as casas de **frente**
  (fachada olhando pra câmera), árvores, poste, poço, placa, cerca. Cole cada
  casa/adereço com o topo do quadro **2 fileiras acima** da fileira de
  `Colisão` (64px = 2 tiles de 32px) — a base (y 62) fica a ~2px do chão,
  imperceptível.
- **`Frente`** — só as casas de **fundo** (viradas de costas). É a camada que
  já desenha depois da Lia (suporte pronto desde a Fase 1) — é isso que faz
  ela "passar por trás" delas, exatamente como você pediu. Mesma régua de
  alinhamento (2 fileiras acima do chão).
- **`Entidades`** (grupo de objetos, sem imagem): `spawn` (chegada vindo da
  cena do hospital) e `npc` × N (ver lista abaixo, cada um com propriedade
  `nome`). Não precisa de objeto de saída: chegar na ponta direita do mapa
  já dispara a transição pra Fase 1 sozinho — é o mesmo mecanismo de "fim de
  fase" que Fase 1/2/3 já usam (`Game._advance_level_if_ready`), só que pra
  vila ele leva pra `Level(0)` em vez de `índice+1`.

Ordem de rua sugerida (intercalando fachada/fundo, como você pediu): comece
com 1-2 casas de frente perto do spawn (pra Lia já ver "isso é uma vila" de
cara), depois alterne frente/fundo a cada 300-500px conforme ela anda —
não precisa ser rígido, o efeito de profundidade funciona mesmo intercalado
de forma solta.

## NPCs e diálogos

O sistema de diálogo de hoje (`NPC_DIALOGUES` em game.py) mostra **um texto
fixo só**, sem múltiplas falas em sequência — dá conta das cientistas, mas as
conversas abaixo (principalmente a da Sra. Amélia) precisam de mais de uma
fala encadeada, tipo a cena do hospital. Vou estender isso quando for
implementar (fica na lista de código no fim). Você só precisa colocar os
objetos `npc` no Tiled com o `nome` certo — o texto eu já deixo pronto aqui:

**1. Tutorial — "Seu Joaquim"** (parado perto do spawn, o primeiro que ela vê)
> "Ei, Lia! Cedo pra andar por aí, hein? Vai com calma: as setas te movem, o
> espaço faz pular. Se precisar bater em alguma coisa — ou em alguém —, é só
> apertar o F. Segurou fôlego demais parada? Aperta Q e sai correndo no
> susto. E qualquer um por aqui que quiser conversar, é só chegar perto e
> apertar E."

**2. Casual — "Dona Marta"** (varrendo a calçada em frente à casa dela)
> "Bom dia, flor! Olha o tanto que você cresceu... Sua mãe tem muito orgulho
> de você, sabia? Ela fala isso toda vez que passo lá em casa."

**3. Casual — "Bento"** (garoto sentado num banco, perto do parquinho)
> "Lia! Depois eu te chamo pra jogar bola, tá? ...Ou você tá com pressa hoje?
> Parece que tá indo em algum lugar importante."

**4. Emocional — "Sra. Amélia"** (perto do fim da rua, antes da saída pra
floresta — a fala-gatilho que você pediu, agora em 3 partes)
> (1) "Lia, filha, vem cá um instantinho."
> (2) "É chato de perguntar, mas... me falaram que sua mãe não anda bem. É
> verdade, isso? Que ela tá com câncer?"
> (3) "Eu sinto muito. Mas você tem uma cara decidida hoje — vai atrás de
> alguma coisa, não vai? Então vai. E volta pra contar pra gente."

Dá pra trocar/ajustar qualquer fala à vontade — é só texto, não trava nada
tecnicamente.

## Código — já feito (ver "✅ Já implementado" no topo)

Tudo que esta seção pedia já está no `level.py`/`game.py`: `VILLAGE` como
índice especial fora de `PHASES` (não conta pra `fase_N_music` nem pro
`COMPLETE` de fim de jogo), `NPC_DIALOGUES` aceitando tupla de falas em
sequência (Sra. Amélia), e a transição INTRO→VILA→Fase 1. Não roda o jogo
localmente pra testar de ponta a ponta (sandbox sem acesso a display), então
vale um play-test seu — qualquer traceback, me manda que eu conserto rápido.
