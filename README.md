# Echoes of Life

Jogo em Python/Pygame, com entrada desktop em `jogo/main.py` e entrada assíncrona para pygbag em `jogo/main_web.py`.

## Executar no Windows

Validado com Python 3.12. Em PowerShell, na pasta do projeto:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r jogo/requirements.txt
.venv/Scripts/python.exe -X utf8 jogo/main.py
```

O jogo abre em tela cheia; F11 alterna para janela. Recursos, mapas e fontes são encontrados a partir da pasta `jogo/`, independentemente da pasta usada para executar o comando. O progresso fica em `jogo/save.json` e as preferências em `jogo/audio_settings.json`. Esses arquivos são locais e ignorados pelo Git.

## Estrutura

```text
SNCTJOGO/
├── jogo/             # código, dependências, recursos e dados locais do jogo
├── site/             # site de apresentação
├── tests/            # testes e referências de regressão
├── bench.py          # simulação e comparação dos cenários
├── build_web.py      # empacotamento WASM sem renomear as entradas
├── smoke_main.py     # verificação da entrada desktop
├── test_support.py   # suporte às verificações
└── *.md              # documentação
```

Os módulos e recursos da tabela abaixo ficam dentro de `jogo/`. Os testes e as ferramentas de verificação ficam na raiz.

| Arquivo/pasta | Responsabilidade |
| --- | --- |
| `main.py`, `main_web.py` | Janela, laço da plataforma e eventos |
| `input_adapter.py` | Tela lógica, teclado web e roteamento compartilhado do mouse |
| `game.py` | Sessão, transições e coordenação da atualização e do desenho |
| `combat.py` | Ataques, combos, projéteis, parry e colisões de combate |
| `inventory.py` | Contagens de itens, consumo pelas teclas 1/2/3, drops e coleta de ferramentas |
| `puzzles.py` | Estado dos puzzles, bancadas, painel, caixa de energia e integração dos minigames |
| `interactions.py` | Prioridade das interações e sequência compartilhada de diálogos, portas e elevador |
| `game_data.py` | Estados, regras, itens, textos, diálogos e tabelas estáticas |
| `assets.py` | Carregamento, recortes, escalas, fundos e névoa sob demanda |
| `render_state.py` | Dados da sessão necessários ao desenho do cenário |
| `level.py`, `tiled_map.py` | Cenários, entidades, leitura TMX/TSX e desenho por chunks |
| `player.py`, `projectile.py` | Movimento do personagem e dos projéteis |
| `enemy.py` | Inimigos de chão e ponto público de importação das classes específicas |
| `enemy_common.py` | Ciclo de dano/morte/respawn e patrulha compartilhados pelos inimigos de chão |
| `enemy_wraith.py`, `enemy_summons.py` | Entidade sombria flutuante e invocações transitórias |
| `enemy_librarian.py`, `enemy_specimen.py`, `enemy_slime_king.py` | Estados, ataques e desenho próprios de cada chefe |
| `minigame.py` | Microscópio e caixa de energia |
| `progress.py` | Validação e gravação atômica do save v1 |
| `audio.py`, `audio_backend.py` | Preferências e backend de áudio desktop/web |
| `hud.py`, `dialogue.py`, `vfx.py` | Interface, diálogo e efeitos visuais |
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

O caminho normal (`CAMERA_ZOOM = 1`) desenha diretamente na superfície lógica;
o buffer intermediário só existe quando há zoom real. As camadas transparentes
do parallax da vila são recortadas automaticamente na memória, preservando o
período e o deslocamento originais, e o rastro do dash reutiliza superfícies em
cache. Há testes de equivalência pixel a pixel para esses três comportamentos.

As verificações usam vídeo/áudio dummy e arquivos temporários, sem modificar o save do jogador. `ECHOES_DATA_DIR` permite escolher outro diretório de dados existente antes de iniciar o jogo.

A versão web usa pygbag, instalado separadamente:

```powershell
.venv/Scripts/python.exe -m pip install pygbag==0.9.3
.venv/Scripts/python.exe build_web.py
```

O resultado fica em `jogo/build/web/` e pode ser copiado para `site/jogo_web/`. O script usa `main_web.py` como entrada sem renomear o `main.py` do desktop e exclui do pacote os dados locais e as versões MP3/WAV que têm cópias OGG compatíveis com o navegador.

O andamento e as etapas restantes estão em [REFATORACAO.md](REFATORACAO.md). Os outros documentos de revisão e propostas são registros históricos e podem descrever código anterior.

`remover_orfaos.sh` também é histórico: por segurança, ele agora apenas lista
os candidatos que ainda existem. Nenhum recurso é apagado automaticamente.
