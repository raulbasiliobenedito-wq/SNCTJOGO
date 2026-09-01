# ECHOES OF LIFE
### Guia completo do jogo e do site — material de apoio para apresentação
*Projeto SNCTJOGO · Python + Pygame Zero*

> "Todo experimento pode falhar. Levante-se e tente novamente!"

---

## Como usar este documento

Este guia tem seis partes: (1) uma visão geral rápida do jogo, (2) a história completa, (3) como o código é organizado por dentro — explicado em linguagem simples, arquivo por arquivo, (4) as mecânicas de jogo explicadas do ponto de vista de quem joga, (5) o site do jogo, e (6) o que já está pronto e o que ainda falta fazer. No final tem uma folha-cola com os pontos mais importantes para citar na apresentação.

---

## 1. Visão geral do jogo

Echoes of Life é um platformer 2D feito em Python, usando o framework Pygame Zero. O jogo tem três fases principais (Escola, Universidade e Centro de Pesquisa) mais uma Vila que funciona como um hub inicial, quatro chefes com padrões de ataque próprios, sete itens diferentes e cinco cientistas reais que aparecem como NPCs dando dicas e fatos históricos.

A jogabilidade combina exploração de plataforma (pular, correr, nadar em trechos submersos) com combate corpo a corpo e à distância contra inimigos comuns e chefes. O jogador controla Lia, uma estudante que sai investigando uma anomalia científica misteriosa depois de descobrir que a mãe está doente.

### Controles

- Setas / A D — mover
- Espaço / seta para cima / W — pular
- Q — investida (dash)
- F ou clique esquerdo — atacar corpo a corpo (combo de até 4 hits)
- R — ataque à distância (desbloqueado após vencer a Fase 1)
- E ou Enter — interagir / falar com NPCs
- 1, 2, 3 — usar item consumível
- R (na tela de fim de jogo) — reiniciar

---

## 2. A história

O jogo começa num quarto de hospital, não numa masmorra. Lia está sentada ao lado da cama quando a mãe pede pra ela se aproximar: os médicos encontraram um câncer, vai ter tratamento, e vai ter dias difíceis. Lia pergunta se existe alguma coisa que ela possa fazer — e a mãe responde com a frase que guia o resto da jornada:

> "Todo experimento pode falhar. Levante-se e tente de novo, minha filha — isso vale pra ciência, e vale pra vida."

É assim que Lia decide ir atrás de cada pista, cada pesquisa, cada resposta que existir por aí. Echoes of Life não é uma história sobre monstros — é sobre uma menina que resolve levar ciência a sério porque precisa dela, de verdade, por alguém que ama.

A primeira pista aparece perto de casa, num laboratório escondido embaixo do pátio da própria escola. Ali, dentro do Rei Slime, pulsa um núcleo de uma cor que não existe em mais nenhum lugar do mundo de Lia — um coral ligado a uma reação biológica rara que cientistas de verdade andam estudando há tempos.

É na Universidade que a pesquisa começa a fazer sentido. No laboratório mais velho do prédio, um tanque de contenção rachado guarda o que sobrou do Espécime 07 — o material que primeiro revelou essa reação. A etiqueta ainda diz "ESPÉCIME 07 — NÃO REMOVER DO TANQUE", mas alguém removeu assim mesmo, e o que escapou se espalhou pelo prédio inteiro: alunos com os olhos acesos naquele mesmo coral, um zelador que continua fazendo a ronda de sempre, um Bibliotecário Silente guardando páginas que ninguém devia ter lido.

No Centro de Pesquisa, numa caverna vulcânica sob o prédio, os estudos estão mais avançados — e mais perigosos. Um dragão feito da própria rocha do lugar guarda o que restou das pesquisas originais. É o fim da linha: se existir uma resposta em algum lugar, é ali.

Em cada fase, Lia encontra cientistas — mulheres reais, de hoje e de um século atrás — dispostas a conversar com ela: Marie Curie, Ada Lovelace, Katherine Johnson, Jaqueline Goes de Jesus e Rosalind Franklin. Nenhuma delas sabe da mãe de Lia, mas cada uma, à sua maneira, mostra o que significa não desistir de uma pergunta difícil.

No fim, o jogo não promete uma cura mágica — nenhuma pesquisa real funciona assim. O que ele promete é o que a mãe de Lia disse no início: que toda tentativa vale a pena, mesmo quando falha, e que ninguém precisa procurar sozinho.

### As três fases (+ a Vila)

**Vila (hub inicial)** — aldeia onde Lia mora, com moradores (Seu Joaquim, Dona Marta, Bento e Sra. Amélia) que dão contexto e conversa antes da aventura começar.

**Fase 1 — Escola** — *"A primeira pergunta pode mudar o mundo."* Lia começa no lugar mais familiar: a própria escola, com um laboratório subterrâneo escondido embaixo do pátio. É lá, contra o Rei Slime, que a anomalia aparece pela primeira vez. NPC: Rosalind Franklin. Item de pesquisa: Essência de Slime.

**Fase 2 — Universidade** — *"Conhecimento se constrói em movimento."* Um corredor universitário tomado por alunos possuídos e vigiado por um zelador guardião leva a duas salas secretas: o laboratório (Espécime 07) e a biblioteca (Bibliotecário Silente). NPCs: Katherine Johnson, Marie Curie, Ada Lovelace. Itens: Livro Mágico e Amostra de Espécime.

**Fase 3 — Centro de Pesquisa** — *"Pesquisa é colaboração, coragem e esperança."* Uma caverna vulcânica com trechos submersos que exigem gerenciar o fôlego de Lia. No fundo, o Dragão guarda o fim da jornada. NPC: Jaqueline Goes de Jesus. Item: Sangue do Dragão.

### Personagens

- **Lia** — protagonista. Estudante curiosa o bastante para reparar no que os outros ignoram. Pula, corre com dash, luta corpo a corpo e nada em trechos submersos.
- **Marie Curie** (Fase 2, laboratório) — Segura um frasco de rádio. Fala real: foi a primeira pessoa a receber dois Prêmios Nobel em áreas diferentes.
- **Ada Lovelace** (Fase 2, biblioteca) — Segura um cartão perfurado. Reconhecida por escrever um dos primeiros algoritmos para uma máquina.
- **Katherine Johnson** (Fase 2, corredor) — Segura um caderno de trajetória. Calculou trajetórias essenciais para missões espaciais da NASA.
- **Jaqueline Goes de Jesus** (Fase 3) — Segura uma micropipeta. Participou do sequenciamento do genoma do coronavírus no Brasil, em 2020 — é uma cientista viva; sua presença é uma homenagem feita com respeito, num projeto escolar não-comercial.
- **Rosalind Franklin** (Fase 1) — Segura a Foto 51. Produziu imagens de raios X fundamentais para compreender a estrutura do DNA.

Além dessas cinco, o jogo cita outras cientistas brasileiras através de fragmentos de pesquisa coletáveis: Bertha Lutz, Enedina Alves Marques, Nise da Silveira, Sônia Guimarães, Mayana Zatz e Johanna Döbereiner.

### Inimigos e chefes

Inimigos comuns: Slime (Fase 1), Cervo de Cristal e Entidade Sombria (Fase 3), Estudante Possuído e Zelador Guardião — este último um mini-chefe (Fase 2).

- **Rei Slime** (chefe da Fase 1) — corpo translúcido com núcleo coral visível. Ataques: Esmagar (onda rasteira nos dois lados — resposta: pular) e Cisão (cospe 4 slimes menores — resposta: andar, não pular no meio deles).
- **Espécime 07** (chefe do Laboratório, Fase 2) — guardião do laboratório velho, a coisa que estava no tanque de contenção. Ataques: Jato (à distância) e Investida (corpo a corpo com antecipação visível).
- **Bibliotecário Silente** (chefe da Biblioteca, Fase 2) — rosto apagado, só resta uma página acesa em coral. Ataques: Silêncio (área, punindo ficar parado perto dele) e Errata (invoca tomos).
- **Dragão** (chefe final, Fase 3) — feito do mesmo material da caverna, dorso de basalto e ventre em brasa. Ataques: Sopro (jato de fogo rasteiro — pular) e Brasas/Terremoto (voa e solta pedras incandescentes — andar para reposicionar, nunca pular).

### Itens

- **Gororoba** (consumível) — recupera 1 coração de vida; cai de slimes comuns na Fase 1.
- **Essência de Slime** (pesquisa) — drop garantido do Rei Slime; conclui a Fase 1.
- **Carcaça de Robô** (consumível) — dá +1 escudo, absorvendo o próximo dano; cai de inimigos da Fase 2.
- **Livro Mágico** (pesquisa) — drop garantido do Bibliotecário Silente; conclui parte da Fase 2.
- **Amostra de Espécime** (pesquisa) — drop garantido do Espécime 07; conclui a outra parte da Fase 2.
- **Dark Crystal** (consumível) — dá +1 coração e +1 escudo; cai de inimigos da Fase 3.
- **Sangue do Dragão** (pesquisa) — drop garantido do Dragão; conclui a Fase 3.

---

## 3. Como o código é organizado por dentro

O jogo é feito com Pygame Zero (pgzero), uma camada simplificada sobre o Pygame que evita ter que escrever manualmente o laço principal do jogo (aquele "enquanto o jogo estiver rodando, atualiza e desenha" que todo jogo precisa) — a função `pgzrun.go()`, no final de `main.py`, cuida disso. Existem dois pontos de entrada: `main.py` (versão desktop, a que você roda no computador) e `main_web.py` (versão para navegador, compilada para WebAssembly com a ferramenta pygbag). Nenhum dos outros módulos do jogo depende de nada exclusivo do Pygame Zero — por isso o mesmo código de lógica funciona tanto no desktop quanto na web.

Os dois pontos de entrada desenham tudo numa superfície fixa de 1920×1080 pixels, que depois é copiada para o tamanho real da janela. Ou seja: toda a lógica do jogo (posições, colisões, câmera) trabalha sempre nesse tamanho de referência, não importa a resolução real da tela do jogador.

### `settings.py` — as constantes globais

Arquivo simples que centraliza números que afetam o jogo inteiro: resolução da tela (1920×1080), física (gravidade, velocidade de queda máxima, velocidade de movimento, força do pulo), tamanho e hitbox da Lia, o zoom de câmera e o caminho das pastas de assets. Qualquer ajuste de "sensação" do jogo passa por esse único lugar.

### `game.py` — o maestro do jogo (o arquivo mais importante, ~2.760 linhas)

A classe `Game` guarda todo o estado de uma partida (vidas, inventário, escudo, câmera, timers de combate) e coordena todos os outros módulos. É o arquivo mais importante para entender e conseguir explicar.

- **Máquina de estados** — `Game.state` alterna entre TITLE (menu), SETTINGS (tela de volume), INTRO (cutscene do hospital), o jogo em si, GAME_OVER e COMPLETE (vitória). A cada quadro, o jogo lê os controles e chama o método de atualização do estado atual. Se um diálogo ou uma dica está ativo, o jogo pausa a simulação normal e só atualiza aquele overlay — é assim que conversar com um NPC "congela" o mundo.
- **Combate** — o ataque corpo a corpo encadeia um combo de até 4 hits: cada aperto dentro de uma janela de tempo avança o combo, e passar do tempo sem atacar volta pro primeiro hit. O 4º hit causa o dobro de dano, assim como atacar durante o dash. O dano é resolvido comparando uma caixa retangular na frente da Lia contra a hitbox de cada inimigo vivo. O ataque à distância (só depois de vencer a Fase 1) dispara um projétil reto.
- **Parry (aparar)** — usando o mesmo botão de ataque, acertar certos golpes de chefe "que voam" (pedras, lâminas, tomos, jato) no timing certo destrói aquele golpe e devolve dano extra no chefe, com tela tremendo e um instante de "congelamento" — inspirado em jogos como Hollow Knight e Cuphead. Nem todo ataque é aparável: ondas no chão e investidas corpo a corpo, não.
- **Vida e dano** — vidas em corações fracionários: inimigo comum tira meio coração, chefe tira um coração inteiro. Tomar dano por contato não teleporta mais a Lia — ela só perde vida e ganha invencibilidade breve, continuando no lugar. Só cair fora do mapa a faz voltar ao checkpoint. O escudo (item) absorve qualquer dano antes das vidas.
- **Colisão e física** — detecção por retângulos (AABB). Para não ficar lento comparando contra todos os blocos do mapa a cada quadro, o chão é indexado em "pedaços" espaciais (chunks) e só os blocos próximos da Lia são testados.
- **Mapas Tiled** — cada fase carrega um arquivo `.tmx` feito no editor Tiled. Camadas marcadas como "Colisão" viram blocos sólidos automaticamente; uma camada "Frente" é desenhada depois da Lia (efeito de primeiro plano). Objetos do Tiled (spawn, checkpoints, inimigos, portas, NPCs, alavancas) são lidos por tipo — ou seja, dá pra reposicionar quase tudo do jogo só editando o mapa, sem tocar em código.
- **Progressão de fase** — a saída só libera quando toda a pesquisa da fase foi coletada e os itens obrigatórios dos chefes estão no inventário (a Fase 2 exige os itens dos dois chefes). Vencer a Fase 1 desbloqueia o ataque à distância para sempre.
- **Câmera** — segue a Lia suavemente, exceto dentro da arena de um chefe vivo, onde trava para enquadrar a arena inteira.
- **Configurações de áudio** — os sliders de volume chamam funções de `audio.py` a cada movimento do mouse, mas só gravam no disco quando o mouse é solto, evitando gravar a cada pixel arrastado.

### `level.py` — definição e montagem de cada fase

Contém os dados descritivos de cada fase (nome, tamanho do mundo, pontos de pesquisa) e a classe `Level`, que monta uma fase concreta a partir desses dados e do arquivo `.tmx` correspondente. É aqui que fica a lógica do quebra-cabeça da Fase 1 (puxar alavanca, apertar botões na ordem certa, montar o microscópio), a leitura de água/lava/espinhos como zonas de perigo, a criação de inimigos a partir de objetos do Tiled e a montagem das arenas de chefe.

### `player.py` — a Lia

Guarda posição, velocidade, direção, timers de dash/pulo e a animação (14 quadros numa spritesheet única: parado, andar, pulo em três fases, combo de ataque, morte). Controla também a física de natação usada na Fase 3: debaixo d'água a gravidade normal vira um afundar suave, e segurar o pulo faz Lia subir continuamente. O fôlego dura 7 segundos antes de começar a afogar.

### `enemy.py` — inimigos e chefes (~2.900 linhas)

Cada inimigo é uma classe própria, mas todos seguem o mesmo padrão de máquina de estados: patrulha, ferido, morrendo/morto (inimigos comuns reaparecem depois de ~20s; chefes derrotados ficam mortos para sempre) e, nos chefes, uma sequência de telégrafo → ataque ativo → recuperação para cada golpe.

Os quatro chefes de verdade nascem adormecidos e só "acordam" quando Lia se aproxima o bastante — estilo Hollow Knight/Silksong. Cada golpe tem uma fase de antecipação visível antes de causar dano de fato, para o jogador aprender a ler o padrão em vez de decorar por tentativa e erro. O Dragão, chefe final, fica parado no lugar e é permanentemente imune a corpo a corpo — só o ataque à distância funciona nele.

### `tiled_map.py` — leitor de mapas do Tiled

Implementa, sem depender de biblioteca externa, a leitura do formato XML/TMX do Tiled: camadas de tile (com decodificação base64+zlib), tilesets externos, tiles animados (como a água) e objetos com propriedades customizadas. Também otimiza o desenho por chunks, mostrando só a área visível pela câmera.

### `dialogue.py`, `cutscene.py`, `hint.py` — textos e pausas

`DialogueBox` é a caixa de diálogo usada por NPCs, achados de lore e a cutscene inicial: o texto aparece gradualmente, caractere por caractere (efeito estilo Undertale), acelerável apertando a tecla de interação. `IntroCutscene` é a cena do hospital entre o título e a Vila, com uma sequência fixa de falas. `Hint` é um sistema separado (vinheta escura + texto) para avisos pontuais de mecânica, como o painel do elevador da Fase 1.

### `projectile.py`, `vfx.py`, `plataform.py`, `hud.py`, `audio.py`

- **projectile.py** — o disparo do ataque à distância: trajetória reta, sem gravidade.
- **vfx.py** — efeitos visuais efêmeros (poeira, respingo, impacto, flash de parry), com folhas de efeito próprias por fase/sala.
- **plataform.py** — plataformas fixas ou que oscilam, configuráveis pelo Tiled.
- **hud.py** — desenha toda a interface: corações de vida (incluindo meio coração), inventário, barra de habilidades com cooldowns, barra de vida do chefe, mensagens temporárias.
- **audio.py** — camada protetora sobre o som do Pygame Zero: tocar uma música/efeito que ainda não tem arquivo no disco simplesmente não faz nada, em vez de travar o jogo — é isso que permite ir soltando os arquivos de áudio aos poucos sem quebrar nada. Também guarda e recarrega o volume de música/efeitos escolhido no menu de Configurações.

---

## 4. Mecânicas de jogo explicadas (para a apresentação)

- **Movimento** — Lia anda com as setas/WASD e pula com espaço/seta cima/W, com um pequeno perdão de tempo pra pular logo depois de sair de uma borda. O dash é um deslocamento rápido na direção que ela olha, com um cooldown visível no HUD.
- **Combate corpo a corpo** — combo de até 4 golpes; acertos seguidos no ritmo certo avançam o combo, o 4º é um finalizador mais forte. Atacar durante o dash também causa dano extra.
- **Parry** — apertar o ataque no timing certo contra certos golpes de chefe destrói o golpe e devolve dano alto, com tela tremendo — recompensa quem reage no timing certo em vez de só bater.
- **Ataque à distância** — desbloqueado ao vencer a Fase 1; essencial contra chefes que ficam temporariamente (ou, no caso do Dragão, permanentemente) imunes a espada.
- **Vida, dano e escudo** — corações de vida (com meio coração possível); levar dano não empurra nem teleporta a Lia, só dá invencibilidade breve. Só cair num buraco sem fundo a faz voltar ao checkpoint. O escudo absorve o próximo golpe, seja qual for.
- **Itens** — consumíveis (cura vida, dá escudo, ou os dois) usáveis com 1/2/3, e itens de pesquisa/quest que nunca são "usados" — só liberam a saída da fase.
- **Diálogos e exploração** — apertar E perto de um NPC inicia uma fala motivacional ou um fato histórico real. Existem também achados opcionais de lore que nunca bloqueiam o avanço, só recompensam quem explora.
- **Fôlego/natação** — em trechos submersos da Fase 3, Lia nada livremente em vez de cair; tem cerca de 7 segundos de fôlego antes de começar a se afogar.
- **Chefes** — cada um dos quatro fica adormecido até Lia se aproximar, e alterna entre 2-3 padrões de ataque claramente sinalizados antes de acontecerem, para o jogador aprender a reagir em vez de decorar cegamente.

---

## 5. O site do jogo

O site (arquivo `site/index.html`, dentro da pasta do projeto) é uma página única, sem depender de nenhum framework — só HTML, CSS e um pouquinho de JavaScript. Ele já está com todo o conteúdo escrito: seções de Sobre, História, Mundo/Fases, Personagens, Inimigos/Chefes, Itens, Ciência (os fatos reais das cientistas) e Jogar.

A seção "Jogar" tem duas abas: uma pra jogar direto no navegador (que exige compilar o jogo para WebAssembly com a ferramenta pygbag e colocar o resultado em `site/jogo_web/`) e outra com o passo a passo para baixar e rodar localmente com Python (`pip install pgzero`, depois `pgzrun main.py`). O site detecta sozinho, com um pequeno script, se o build web já existe — se não existir, mostra as instruções em vez de um iframe quebrado.

Ou seja: o site já está pronto para apresentar como está, mostrando toda a lore, o elenco de personagens e o funcionamento do jogo, mesmo que a versão jogável embutida no navegador ainda não tenha sido gerada.

---

## 6. O que já está pronto

O ciclo completo do jogo funciona de ponta a ponta: Título → Configurações (com volume de música/efeitos persistido em disco) → Cutscene do hospital → Vila (com diálogo dos 4 moradores) → Fase 1 → Fase 2 (com as duas salas secretas e seus dois chefes) → Fase 3 (com natação e o Dragão) → tela de vitória ou derrota.

Também estão prontos e testados: o sistema de combate completo (combo, dash, parry, ataque à distância), a vida fracionária em corações, a progressão por itens de pesquisa, a persistência do volume, e correções recentes importantes — um bug que afundava as casas da Vila no chão (a forma como os tiles maiores eram ancorados), um bug que deixava o jogo completamente mudo (erro de escopo do Pygame Zero) e uma otimização de performance que eliminava um redimensionamento de tela desnecessário rodando a cada quadro.

Sobre o áudio: já estão no jogo três músicas (da Fase 1, do Rei Slime e da Vila) e alguns efeitos (pulo, projétil, quatro variações de soco, o terremoto do Dragão). O sistema já está 100% preparado para receber o resto — falta só depositar os arquivos com o nome certo nas pastas de música e efeitos.

**Um ponto que vale confirmar visualmente antes da apresentação:** os documentos de planejamento (`PLANO_FASE1.md`) descrevem a repintura do mapa da Fase 1 no Tiled como pendente, mas ao conferir o arquivo de mapa agora, as camadas de terreno já têm dados pintados — parece que esse trabalho avançou depois que a documentação foi escrita. Vale abrir o Tiled ou rodar o jogo rapidamente pra confirmar se a Fase 1 já está com o cenário completo antes de falar sobre isso na apresentação.

---

## 7. O que ainda falta / próximos passos

### Arte pendente

- Sprite própria para os 4 NPCs da Vila (hoje interagíveis, mas invisíveis em tela).
- Fundo de céu dedicado (`ceu.png`) para a Vila e a Fase 1 — ainda não existe no disco.
- Arte da bancada do microscópio na Fase 1.
- Frames de animação dedicados ao ataque à distância da Lia (hoje reaproveita o sprite parado/andando).

### Áudio

A maior pendência em volume de trabalho: falta praticamente toda a trilha sonora (menu, cutscene, Fases 2 e 3, as duas salas secundárias, os três chefes restantes, telas de vitória/derrota) e a maioria dos efeitos sonoros (dano, morte, escudo, itens, portas, alavancas, botões, diálogo, seleção de menu). O encanamento de código já está pronto — é só ir soltando os arquivos aos poucos.

### Mapas / mundo

- Confirmar visualmente se a Fase 1 já está com o cenário completo (ver observação na seção anterior).
- Resolver a falta de um caminho de volta na Fase 3 (hoje é praticamente só de ida).

### Mecânicas novas / ideias em aberto (sem compromisso de prazo)

- Tremor de tela e poeira caindo do teto no momento em que um chefe acorda.
- Uma fase de "fúria" para chefes abaixo de 50% de vida (ataques mais rápidos).
- Uma segunda habilidade depois da Fase 2 (ainda só uma ideia, não confirmada).
- Ajuste geral de dificuldade dos chefes, a discutir.

Esses últimos itens vêm de um documento de ideias (`IDEIAS_FUTURAS.md`) que funciona como uma lista viva — nada ali tem prazo comprometido, é um banco de ideias que só vira tarefa quando decidido fazer.

---

## 8. Folha-cola para a apresentação

Se precisar resumir o jogo em poucas frases: Echoes of Life é um platformer 2D em Python/Pygame Zero, com 3 fases + uma vila-hub, sobre uma estudante (Lia) que investiga uma anomalia científica depois de descobrir que a mãe está com câncer — coletando ao longo do caminho fatos reais sobre cientistas mulheres, algumas aparecendo como NPCs.

Pontos técnicos fortes para citar: mapas construídos visualmente no editor Tiled e lidos por um parser próprio (sem depender de biblioteca externa); o mesmo código de lógica roda tanto no desktop quanto compilado para navegador (WebAssembly, via pygbag); sistema de combate com combo, dash e parry inspirado em jogos como Hollow Knight e Cuphead; otimização de colisão por chunks espaciais para não pesar o jogo; sistema de áudio à prova de arquivo faltando, que permite ir completando a trilha sonora aos poucos sem travar nada.

Se perguntarem o que falta: principalmente trilha sonora e efeitos sonoros (o código já está pronto pra recebê-los), sprites dos moradores da Vila, e alguns ajustes de mundo (caminho de volta na Fase 3, confirmação do cenário final da Fase 1).
