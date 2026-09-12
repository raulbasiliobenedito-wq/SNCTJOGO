"""Ponto de entrada para a versão web (WASM) do jogo, via pygbag.

O `main.py` original usa `pgzrun.go()`, que não roda em WASM. Este arquivo
faz a mesma coisa manualmente: cria a janela com pygame puro e chama
`game.update(keyboard, dt)` / `game.draw(screen)` dentro de um laço
assíncrono, cedendo o controle ao navegador a cada quadro com
`await asyncio.sleep(0)` (exigência do pygbag/Pyodide).

Isso só é possível porque game.py, level.py, player.py, enemy.py etc. já
não dependem de nada específico do pgzero (nenhum Actor, sound, music ou
Clock) — só de um objeto "keyboard" com um atributo booleano por tecla e de
um "screen" com `.surface`, que esta camada fornece.

COMO GERAR O BUILD WEB
-----------------------
1. pip install pygbag
2. Nesta pasta (a mesma do main.py), rode:
       python -m pygbag main_web.py
   Isso abre um servidor local (geralmente em http://localhost:8000) já
   servindo o jogo rodando no navegador, e cria uma pasta build/web com os
   arquivos prontos pra hospedar (ex.: GitHub Pages, itch.io).

   Se o pygbag reclamar que o arquivo de entrada precisa se chamar
   main.py, renomeie temporariamente:
       main.py      -> main_desktop.py
       main_web.py  -> main.py
   rode o comando acima, depois desfaça a renomeação (o main.py original
   continua sendo o ponto de entrada pra jogar localmente com pgzrun).

3. Copie o conteúdo gerado em build/web/ para a pasta site/jogo_web/ (ver
   site/index.html, seção "Jogar") — a página já está preparada pra
   carregar build/web/index.html num iframe automaticamente, se ele
   existir.
"""

import asyncio

import pygame

from game import Game
from input_adapter import LogicalScreen, mouse_down, mouse_move, mouse_up, KeyboardState
from settings import HEIGHT as GAME_HEIGHT, TITLE, WIDTH as GAME_WIDTH


WIDTH = GAME_WIDTH
HEIGHT = GAME_HEIGHT


async def main():
    pygame.init()
    display = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)

    game = Game()
    logical_screen = LogicalScreen()
    keyboard = KeyboardState()
    clock = pygame.time.Clock()
    same_size = (WIDTH, HEIGHT) == (GAME_WIDTH, GAME_HEIGHT)

    running = True
    while running:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_down(game, event.pos)
            elif event.type == pygame.MOUSEMOTION:
                mouse_move(game, event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_up(game, event.pos)

        keyboard.refresh(pygame.key.get_pressed())
        game.update(keyboard, dt)
        game.draw(logical_screen)

        if same_size:
            display.blit(logical_screen.surface, (0, 0))
        else:
            enlarged = pygame.transform.smoothscale(logical_screen.surface, (WIDTH, HEIGHT))
            display.blit(enlarged, (0, 0))
        pygame.display.flip()

        # Cede o controle ao laço de eventos do navegador a cada quadro —
        # sem isso, o pygbag trava a aba (é a exigência central do modelo
        # assíncrono do Pyodide/emscripten).
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
