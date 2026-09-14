#!/usr/bin/env bash
# Inventário histórico de possíveis órfãos.
#
# Este arquivo se chamava "remover_orfaos.sh" e apagava recursos diretamente.
# A lista foi criada antes de código, mapas e assets migrarem para jogo/ e não é
# uma autorização para excluir arte. O script agora é deliberadamente somente
# leitura: mostra quais candidatos ainda existem para uma revisão manual.
set -euo pipefail

script_path="${BASH_SOURCE[0]}"
script_dir="${script_path%/*}"
[[ "$script_dir" == "$script_path" ]] && script_dir="."
script_dir="$(cd -- "$script_dir" && pwd)"
project_root="${1:-$script_dir}"
game_root="$project_root/jogo"

if [[ ! -d "$game_root/images" || ! -d "$game_root/maps" ]]; then
    printf 'Projeto inválido: não encontrei jogo/images e jogo/maps em %s\n' "$project_root" >&2
    exit 2
fi

candidates=(
    "images/backgrounds/ifsp_background.png"
    "images/backgrounds/cave_background.png"
    "images/backgrounds/cave_background_underwater.png"
    "images/player/background.png"
    "images/lava_lake.png"
    "images/enemies/crystal_crab.png"
    "images/enemies/dark_hand.png"
    "images/enemies/slime_king_attack.png"
    "images/objects/activated_lever.png"
    "images/objects/lever.png"
    "images/vfx/boss_attacks/indicador_perigo.png"
    "images/vfx/boss_attacks/meteoro.png"
    "images/tiles/university_sheet.png"
    "images/props/banner.png"
    "images/props/bench.png"
    "images/props/book_stack.png"
    "images/props/bush.png"
    "images/props/grad_cap.png"
    "images/props/plant_pot.png"
    "maps/fase3_cave_tileset_32x32.png"
    "fonts/ThaleahFat.ttf"
    "images/fase3_tileset"
)

printf 'Candidatos históricos ainda presentes:\n'
found=0
for relative_path in "${candidates[@]}"; do
    if [[ -e "$game_root/$relative_path" ]]; then
        printf '  jogo/%s\n' "$relative_path"
        found=$((found + 1))
    fi
done

printf '\n%d candidato(s) encontrado(s). Nenhum arquivo foi removido.\n' "$found"
printf 'Confirme usos em Python, TMX/TSX, site e documentação antes de excluir manualmente.\n'
