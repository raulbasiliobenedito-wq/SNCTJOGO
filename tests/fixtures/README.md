# Referências dos inimigos de chão

`ground_enemies.json` foi capturado antes da extração das classes-base, a partir do código do commit `4553e8e`, com Pygame 2.6.1. Guarda a origem e o hash do arquivo original.

Os roteiros estão em `tests/enemy_scenarios.py`. São quatro cenários para cada um dos quatro inimigos: patrulha com plataforma deslocada, plataforma estreita, dano seguido de morte/respawn e pisão durante a reação ao dano.

Para cada cenário, a referência contém:

- hash de posição, hitbox, direção, velocidade, vida, estado e temporizadores em todos os quadros;
- transições e resultados dos golpes, para ajudar a investigar uma diferença;
- hash de imagens nos quadros amostrados e em todas as mudanças de estado, direção ou quadro de morte.

O teste visual usa sprites sintéticos assimétricos, permitindo conferir espelhamento, seleção dos quadros e alinhamento sem depender de uma versão da arte. O benchmark do jogo complementa a verificação com as imagens reais dos sete cenários.

Execute `python -m unittest discover -s tests -p test_enemies.py -v`. As referências são dados fixos: os testes não as atualizam. Uma mudança futura de balanceamento ou comportamento deve revisar os resultados esperados antes de substituir a referência; não regenere o arquivo apenas para fazer um teste passar.

## Referência de combate

`combat_sequence.json` foi capturado no commit `aacce7c`, antes da extração para `CombatSystem`. O roteiro de 240 quadros está em `tests/test_combat.py`: combina golpes, tentativas durante cooldown, finalizador, dash, desbloqueio do disparo, troca de direção e expiração dos projéteis. O hash cobre cada quadro; os sons e o estado final ficam explícitos para investigação.

`python -m unittest discover -s tests -p test_combat.py -v` executa a referência e os demais contratos de combate. Os adaptadores do teste permitem também executar o roteiro contra a organização anterior de Game; a referência não é regenerada automaticamente.

## Inimigos com estados específicos

`special_enemies.json` foi capturado antes de qualquer extração de `DarkWraith`, `SmallSlime`, `Librarian`, `Specimen` ou `SlimeKing`. Os roteiros determinísticos ficam em `tests/special_enemy_scenarios.py` e registram cada quadro dos ataques, temporizadores, posições, vida, hazards, objetos lançados e invocações.

A referência cobre o ataque e o respawn do DarkWraith, os três ataques do Bibliotecário, os três ataques do Espécime e os dois ataques do Rei Slime com a criação de `SmallSlime`. Dois contratos explícitos documentam comportamentos que não devem ser corrigidos por acidente durante a refatoração: a órbita do Errata atualmente transita para o mergulho após um único update em `ERRATA_ORBIT`, apesar de o timer receber 15, e invocações mortas continuam em `Level.enemies`. Alterar qualquer um deles exige uma decisão de jogabilidade ou de ciclo de vida separada da extração estrutural.

## Referência de desenho dos mapas

`map_rendering.json` foi capturado antes de deduplicar tiles grandes que
atravessam limites de chunks. Os 13 pontos de câmera de
`tests/map_render_scenarios.py` cobrem todos os mapas TMX, coordenadas
fracionárias, animações, casas e props maiores que o grid e a camada
`Frente` desenhada depois da personagem.

Cada caso guarda a hash RGBA do mapa normal e uma segunda hash após inserir
uma faixa opaca entre `draw()` e `draw_foreground()`. Assim, o contrato
protege tanto os pixels quanto a ordem de sobreposição. A referência é fixa:
uma mudança intencional de arte ou renderização deve ser analisada antes de
substituí-la.

Em 13/09/2026, somente o caso `vila/right_house_boundary` foi atualizado após
uma edição intencional de `vila.tmx`, posterior à captura original. As imagens
base e de primeiro plano desse ponto foram inspecionadas antes da troca das
hashes; os outros 12 casos permaneceram inalterados.

## Contratos de inventário

`tests/test_inventory.py` usa resultados esperados explícitos, sem um novo arquivo de referência. Seus 12 testes passaram na versão local anterior à extração de `InventorySystem` (após a mudança para `jogo/`) e na versão extraída. A cópia local do módulo anterior está em `.test-output/inventory-before-game.py`; os testes não dependem dela.

Execute `python -m unittest discover -s tests -p test_inventory.py -v` a partir da raiz. Os casos cobrem consumo, drops, ferramentas, transições e persistência. Não altere suas expectativas apenas para acomodar uma refatoração; uma mudança nas regras exige revisão deliberada.
