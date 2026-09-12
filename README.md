# Echoes of Life

Jogo em Python/Pygame, com entrada desktop em `main.py` e entrada assíncrona para pygbag em `main_web.py`.

## Executar no Windows

Validado com Python 3.12. Em PowerShell, na pasta do projeto:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/pgzrun.exe main.py
```

O jogo abre em tela cheia; F11 alterna para janela. Recursos, mapas e fontes são encontrados a partir da pasta do projeto. O progresso fica em `save.json` e as preferências em `audio_settings.json`. Esses arquivos são locais e ignorados pelo Git.

## Estrutura

| Arquivo/pasta | Responsabilidade |
| --- | --- |
| `main.py`, `main_web.py` | Janela, laço da plataforma e eventos |
| `input_adapter.py` | Tela lógica, teclado web e roteamento compartilhado do mouse |
| `game.py` | Sessão, transições, combate, interações e coordenação do desenho |
| `game_data.py` | Estados, regras, itens, textos, diálogos e tabelas estáticas |
| `assets.py` | Carregamento, recortes, escalas, fundos e névoa sob demanda |
| `render_state.py` | Dados da sessão necessários ao desenho do cenário |
| `level.py`, `tiled_map.py` | Construção dos cenários, entidades e leitura TMX/TSX |
| `player.py`, `enemy.py`, `projectile.py` | Movimento e comportamento de personagens, inimigos e projéteis |
| `minigame.py` | Microscópio e caixa de energia |
| `progress.py` | Validação e gravação atômica do save v1 |
| `audio.py`, `hud.py`, `dialogue.py`, `vfx.py` | Áudio e apresentação |
| `maps/`, `images/`, `fonts/`, `music/`, `sounds/` | Conteúdo e recursos |
| `tests/`, `bench.py`, `smoke_main.py` | Regressões, simulação e verificação desktop |

## Verificações

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe smoke_main.py
.venv/Scripts/python.exe bench.py --report .test-output/referencia.json --capture-dir .test-output/referencia
```

O benchmark percorre a vila, três fases e três salas durante 600 quadros cada. Inclui movimento, salto, ataque, dash, interação, item e disparo. Não equivale a terminar o jogo.

Para comparar uma alteração futura com a referência:

```powershell
.venv/Scripts/python.exe bench.py --report .test-output/novo.json --compare .test-output/referencia.json
```

A comparação verifica pixels iniciais, posição final, vidas e estados, usando a mesma semente e duração. Diferenças de tempo não fazem o teste falhar. `--profile 1` mostra os custos da Fase 1; `--quick` omite as salas.

As verificações usam vídeo/áudio dummy e arquivos temporários, sem modificar o save do jogador. `ECHOES_DATA_DIR` permite escolher outro diretório de dados existente antes de iniciar o jogo.

A versão web continua usando pygbag, instalado separadamente. As verificações locais exercitam sua função de entrada com Pygame nativo; a execução WASM deve ser validada no navegador ao preparar um build.

O andamento e as etapas restantes estão em [REFATORACAO.md](REFATORACAO.md). Os outros documentos de revisão e propostas são registros históricos e podem descrever código anterior.
