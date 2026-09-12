# Referências dos inimigos de chão

`ground_enemies.json` foi capturado antes da extração das classes-base, a partir do código do commit `4553e8e`, com Pygame 2.6.1. Guarda a origem e o hash do arquivo original.

Os roteiros estão em `tests/enemy_scenarios.py`. São quatro cenários para cada um dos quatro inimigos: patrulha com plataforma deslocada, plataforma estreita, dano seguido de morte/respawn e pisão durante a reação ao dano.

Para cada cenário, a referência contém:

- hash de posição, hitbox, direção, velocidade, vida, estado e temporizadores em todos os quadros;
- transições e resultados dos golpes, para ajudar a investigar uma diferença;
- hash de imagens nos quadros amostrados e em todas as mudanças de estado, direção ou quadro de morte.

O teste visual usa sprites sintéticos assimétricos, permitindo conferir espelhamento, seleção dos quadros e alinhamento sem depender de uma versão da arte. O benchmark do jogo complementa a verificação com as imagens reais dos sete cenários.

Execute `python -m unittest discover -s tests -p test_enemies.py -v`. As referências são dados fixos: os testes não as atualizam. Uma mudança futura de balanceamento ou comportamento deve revisar os resultados esperados antes de substituir a referência; não regenere o arquivo apenas para fazer um teste passar.
