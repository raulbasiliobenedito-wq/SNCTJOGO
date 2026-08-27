# Plano da Fase 1 — Escola (refazendo no Tiled)

## Status atual

- ✅ Tileset (`escola_tileset_64x64.tsx`, o nome do arquivo não importa)
  reconfigurado pra 32x32 de verdade — `tilewidth`/`tileheight` corretos,
  `columns` recalculado a partir da imagem redimensionada no Aseprite.
- ✅ `fase1_escola.tmx` redimensionado pra grade de 32x32 mantendo o
  mesmo tamanho físico de mundo (232x46 tiles = mesmos 7424x1472px de
  antes, só com grade mais fina).
- ✅ Camadas de tile criadas (ainda todas VAZIAS, prontas pra pintar):
  `Fundo`, `Perigos`, `Colisão` (já com `colisao=true`), `Decoração`,
  `Frente`.
- ✅ Suporte de código pra `Frente` pronto: qualquer camada chamada
  "Frente" (ou com propriedade `frente=true`) desenha DEPOIS da Lia (ver
  `TiledMap.draw_foreground`/`Game._draw_world_foreground`) — pinte
  livremente ali qualquer cenário que deva ficar na frente dela (moldura
  de porta, bancada em primeiro plano, etc.).
- ✅ Todos os objetos antigos (`Plataformas`, `Paredes`, `Rota Retorno`,
  `Entidades` — spawn/checkpoints/livros/slimes/elevadores/painel/
  botões/microscópio/bancada/cientista) sobreviveram intactos, com as
  mesmas coordenadas de pixel de antes (o mundo físico não mudou de
  tamanho, só a grade).
- ✅ Fundo trocado: `draw_school_background` (desenho procedural de sala
  em sala) foi removido — a Fase 1 agora usa a mesma imagem única com
  parallax que Fases 2/3 usam (`images/backgrounds/background_school.png`,
  céu/montanhas ao longe, visível pelas janelas dos corredores).
- ✅ Mecânica de pulo na parede removida do jogo inteiro (não só da Fase
  1): sem wall slide, sem wall jump, sem o indicador "PULO PAREDE" no
  painel de habilidades. `wall_blocks`/objetos "Paredes" também saíram do
  código — não têm mais efeito nenhum, então o trecho de wall-jump saiu
  do plano espacial abaixo (era o único motivo de "Paredes" existir). Se
  o `.tmx` ainda tiver esse objectgroup, pode apagar em Tiled à vontade,
  é só um objeto morto agora.
- ⏳ Ainda falta: pintar terreno de verdade em Fundo/Perigos/Colisão/
  Decoração seguindo a planta espacial abaixo (as `Plataformas` objeto
  antigas continuam funcionando como estão, mas a ideia é a Fase 1 ganhar
  chão de verdade como as Fases 2/3).
- ✅ Rei Slime virou objeto do Tiled: crie um objeto tipo `rei_slime` na
  camada Entidades, do tamanho da plataforma/chão onde ele deve patrulhar
  (retângulo = área de patrulha dele, igual a `especime`/`bibliotecario`).
  Não precisa mais nascer sozinho no fim do percurso — o código lê a
  posição/tamanho direto do objeto (ver `Level._make_boss_arenas`). Só
  lembre de pintar chão de verdade (Colisão) por baixo dele, do mesmo
  jeito que a arena do Dragão na Fase 3 já depende de `column_tops`
  (sem chão pintado ali, ele fica sem piso).
- ⏳ Só falta o ajuste do threshold do fundo subterrâneo (item 1 no fim
  deste documento) — esperando o layout de verdade existir.


Planta de referência pra desenhar `maps/fase1_escola.tmx` do zero, no
mesmo padrão das Fases 2 e 3: tiles de 32x32, camadas `Fundo` / `Perigos`
/ `Colisão` (com a propriedade `colisao=true`) / `Decoração`, objetos
tipados na camada `Entidades` (mesmo esquema que o jogo já lê de
qualquer mapa — nada disso é código novo, é só posicionar os objetos
certos no lugar certo).

Escala alvo: grande, no estilo da Fase 3 (~10000px de largura). Altura
sugerida ~1600-2000px (bem menor que os 3200px da Fase 3 — aqui não tem
uma descida diagonal contínua, só um corredor principal com dois desvios
verticais curtos: a sala de controle em cima e o laboratório embaixo).

## O que TEM que existir no mapa novo (lido genericamente do Tiled, nenhuma mudança de código necessária pra isso)

- `spawn` (objeto único)
- `checkpoint` x3
- `livro` x7 (5 na superfície, 2 no laboratório)
- `slime` x4 (ou mais, à vontade — não há limite fixo)
- `cientista` com propriedade `nome="Rosalind Franklin"`, perto do spawn
- `elevador_principal` e `elevador_superior`, cada um com propriedades
  `top` e `bottom` (os dois extremos do curso vertical dele)
- Opcional: `alavanca` x4, cada uma com propriedades `elevador`
  (`principal`/`superior`) e `posicao` (`topo`/`base`) — controla onde
  cada alavanca fica plantada (uma por andar de cada elevador). Sem
  esses objetos o jogo calcula uma posição automática encostada na
  borda do poço (ver `Level._fixed_lever`), então não é bloqueante —
  só use se quiser ajustar a posição exata em cima de um tile
  específico.
- `painel` (único)
- `botao` x4, cada um com propriedade `ordem` (1 a 4 — a sequência certa
  de aperto)
- `parte_microscopio` x4, cada um com propriedades `nome` (Lente/Base/
  Luz/Ocular) e `ordem` (1 a 4)
- `bancada` (única)
- `rei_slime`: um único objeto, retângulo do tamanho da área de patrulha
  do chefe, sobre chão de verdade (Colisão) já pintado
- Grupo de objetos chamado **"Rota Retorno"**: plataformas que só faria
  sentido a Lia usar depois de montar o microscópio — a lógica de só
  liberar depois já existe no código, aqui é só desenhar o caminho
  físico
- Opcional: `retorno_superficie` (ponto exato onde ela reaparece ao subir
  de volta pro corredor principal — se não existir, o jogo usa um padrão)

## Planta espacial (esboço aprovado: entrada → escada → wall-jump → laboratório no porão → volta → ginásio do chefe)

Coordenadas abaixo são um PONTO DE PARTIDA, não regra fixa — ajuste
livremente enquanto desenha; o importante é a ordem/proporção.

**1. Entrada (x ≈ 0–1200)**
Corredor/hall térreo, chão simples, sem inimigo ainda — zona de
aquecimento. `spawn` em x≈100. `cientista` Rosalind Franklin perto dali,
parada num canto do hall.

**2. Átrio/escadaria principal (x ≈ 1200–2900)**
Sobe em degraus — primeira exposição a plataforma+pulo de verdade.
1–2 `slime` aparecem aqui. `checkpoint` #1 perto do topo (≈ x=2350,
mesma posição relativa de hoje). Alguns `livro` espalhados pelos degraus.

**3. Átrio dos elevadores (x ≈ 2900–3400)**
Um patamar só, com os dois elevadores lado a lado:
`elevador_superior` (leva pra cima, pra sala de controle) e
`elevador_principal` (leva pra baixo, pro laboratório).

**3a. Sala de controle (acima, y baixo — perto do teto do mapa)**
Sala pequena e fechada com os 4 `botao` em sequência (`ordem` 1-4).
Puzzle isolado, sem inimigo — o desafio é achar a ordem certa, não
plataforma.

**3b. Laboratório de ciências (abaixo, y alto — perto do "porão")**
Corredor mais longo e horizontal. `painel` reage à sequência acertada lá
em cima. As 4 `parte_microscopio` espalhadas pelo corredor, `bancada` no
fim pra montar. 2 `livro` extras aqui. Depois de montado, a "Rota
Retorno" abre — um atalho de volta pra cima que reconecta ao corredor
principal MAIS À FRENTE (não de volta pro átrio dos elevadores — é um
atalho pra economizar o caminho de volta inteiro).

**4. Corredor principal, trecho 2 (x ≈ 3400–5800)**
Continua a escola (salas de aula passando ao fundo — isso é só
Decoração, não afeta colisão). Sem wall-jump (mecânica removida do
jogo) — se quiser um desafio vertical aqui, usar plataformas normais
(inclusive móveis, ver `_platform_from_object`/propriedades
`percurso`/`periodo`) em vez de paredes encaradas. Mais 1–2 `slime`
neste trecho. `checkpoint` #2 no fim.

**5. Corredor final (x ≈ 5800–9000)**
Reta final antes do ginásio. Resto dos `livro`/`slime` restantes.
`checkpoint` #3 perto do fim.

**6. Ginásio — arena do Rei Slime (x ≈ 9000–10000+)**
Pinte o chão de verdade do ginásio (Colisão) sem buraco, e coloque o
objeto `rei_slime` sobre ele — um retângulo do tamanho da área onde ele
deve andar (largura maior = mais espaço pra Lia manter distância e usar
o ataque à distância). Posição e tamanho são 100% controlados por você
agora, direto no Tiled.

## Coisa de código que ainda vai precisar de ajuste (eu cuido, só avisando pra não esquecer)

1. **Threshold "subterrâneo" do fundo** (`player.y > 780` em
   `Game._draw_background`): decide quando trocar o visual de fundo pra
   versão "subterrâneo". Esse número foi calibrado pro mapa antigo — vai
   precisar de um novo valor baseado no Y real do laboratório no mapa
   novo.

Só dá pra ajustar direito depois que as coordenadas Y de verdade do
laboratório/sala de controle existirem no `.tmx` — me chama quando tiver
uma versão jogável (nem que seja só a colisão, sem arte final) que eu
calibro isso.
