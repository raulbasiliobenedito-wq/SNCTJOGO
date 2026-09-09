#!/usr/bin/env bash
# Assets confirmadamente órfãos: nenhum .py, .tmx, .tsx, .md, .html ou .json
# do projeto os referencia (conferido duas vezes, inclusive nomes montados
# por f-string e no site/index.html).
# NÃO inclui: images/npcs/cientistas.png (usado por site/index.html),
# images/tiles/platform1-4.png (f-string em _load_platform_tiles, pele
# genérica de qualquer plataforma-objeto futura do Tiled).
set -e
# rode este script DE DENTRO da pasta SNCTJOGO
cd "${1:-.}"
rm -fv images/backgrounds/ifsp_background.png \
       images/backgrounds/cave_background.png \
       images/backgrounds/cave_background_underwater.png \
       images/player/background.png \
       images/lava_lake.png \
       images/enemies/crystal_crab.png \
       images/enemies/dark_hand.png \
       images/enemies/slime_king_attack.png \
       images/objects/activated_lever.png \
       images/objects/lever.png \
       images/vfx/boss_attacks/indicador_perigo.png \
       images/vfx/boss_attacks/meteoro.png \
       images/tiles/university_sheet.png \
       images/props/banner.png images/props/bench.png images/props/book_stack.png \
       images/props/bush.png images/props/grad_cap.png images/props/plant_pot.png \
       maps/fase3_cave_tileset_32x32.png \
       fonts/ThaleahFat.ttf
rm -rfv "images/fase3_tileset"
# Backups e artefatos de build (20 MB) — regeneráveis, já no .gitignore.
rm -fv maps/*.bak_v* images/backgrounds/*.bak_v* build/web/snctjogo.apk build/web/snctjogo.tar.gz
echo "Pronto."
