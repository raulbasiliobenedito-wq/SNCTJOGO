from pathlib import Path

import pygame


class VFXManager:
    """Gerencia instâncias efêmeras de efeitos visuais (poeira ao andar,
    respingo ao entrar na água, impacto ao sofrer dano) a partir de uma única
    spritesheet (vfx.png, quadro 32x32, grade 8 col x 5 lin). Cada instância
    ativa só guarda tipo/posição/tempo decorrido; o quadro é calculado sob
    demanda a partir do fps de cada efeito, então não há estado por-quadro
    pra manter sincronizado."""

    FRAME_SIZE = 32

    # linha na spritesheet, número de quadros usados e fps de reprodução —
    # direto do LEIA-ME_integracao.md (seção "vfx.png"). Efeitos com
    # "sheet": "fase2" vêm de vfx_university.png (LEIA-ME_fase2.md) em vez
    # da folha genérica.
    DEFS = {
        "impact": {"row": 0, "frames": 6, "fps": 18, "loop": False},
        "dust": {"row": 1, "frames": 5, "fps": 16, "loop": False},
        "splash": {"row": 2, "frames": 5, "fps": 16, "loop": False},
        "ember": {"row": 3, "frames": 8, "fps": 6, "loop": True},
        "slash": {"row": 4, "frames": 4, "fps": 20, "loop": False},
        "chalk": {"row": 0, "frames": 6, "fps": 18, "loop": False, "sheet": "fase2"},
        "glass": {"row": 1, "frames": 5, "fps": 16, "loop": False, "sheet": "fase2"},
        "chem_splash": {"row": 2, "frames": 5, "fps": 16, "loop": False, "sheet": "fase2"},
        "spark": {"row": 3, "frames": 5, "fps": 20, "loop": False, "sheet": "fase2"},
        "paper": {"row": 4, "frames": 6, "fps": 12, "loop": True, "sheet": "fase2"},
        # vfx_lab.png (LEIA-ME_laboratorio.md) — sala do laboratório velho.
        "acid_burn": {"row": 0, "frames": 6, "fps": 17, "loop": False, "sheet": "lab"},
        "steam": {"row": 1, "frames": 6, "fps": 14, "loop": True, "sheet": "lab"},
        "toxic_cloud": {"row": 2, "frames": 8, "fps": 11, "loop": True, "sheet": "lab"},
        "containment_break": {"row": 3, "frames": 6, "fps": 16, "loop": False, "sheet": "lab"},
        "lab_spark": {"row": 4, "frames": 5, "fps": 20, "loop": False, "sheet": "lab"},
        # vfx_library.png (LEIA-ME_biblioteca.md) — sala da biblioteca.
        "page_burst": {"row": 0, "frames": 6, "fps": 17, "loop": False, "sheet": "library"},
        "book_dust": {"row": 1, "frames": 5, "fps": 14, "loop": False, "sheet": "library"},
        "candle_flare": {"row": 2, "frames": 4, "fps": 12, "loop": False, "sheet": "library"},
        "ink_splash": {"row": 3, "frames": 5, "fps": 15, "loop": False, "sheet": "library"},
        "silence_wave": {"row": 4, "frames": 6, "fps": 15, "loop": False, "sheet": "library"},
        # vfx/parry_flash.png (folha dedicada, 1 linha, 6 quadros) — flash do
        # parry bem-sucedido (ver Game._check_parries). Só existe depois que
        # o Raul salvar o arquivo; até lá __init__ pula essa entrada de
        # propósito (ver comentário logo abaixo) e spawn("parry_flash", ...)
        # vira um no-op silencioso, sem derrubar o jogo.
        "parry_flash": {"row": 0, "frames": 6, "fps": 20, "loop": False, "sheet": "parry"},
    }

    def __init__(self, sheet_path, extra_sheets=None):
        """`extra_sheets` é um dict {nome: caminho} — cada DEF pode apontar
        pra um desses via a chave "sheet" (ver DEFS acima). `nome` "primary"
        é reservado pra `sheet_path`. Uma folha extra que ainda não existe no
        disco (ex.: parry_flash.png antes do Raul salvá-la) é simplesmente
        ignorada em vez de derrubar o jogo — os DEFs que apontam pra ela só
        ficam de fora de self.frames, e spawn() já sabe pular esses casos."""
        sheets = {"primary": pygame.image.load(sheet_path).convert_alpha()}
        for name, path in (extra_sheets or {}).items():
            if not Path(path).exists():
                continue
            sheets[name] = pygame.image.load(path).convert_alpha()
        self.frames = {}
        for name, info in self.DEFS.items():
            sheet = sheets.get(info.get("sheet", "primary"))
            if sheet is None:
                continue
            row = info["row"]
            self.frames[name] = [
                sheet.subsurface(
                    pygame.Rect(col * self.FRAME_SIZE, row * self.FRAME_SIZE, self.FRAME_SIZE, self.FRAME_SIZE)
                ).copy()
                for col in range(info["frames"])
            ]
        self.active = []

    def spawn(self, kind, center_x, center_y):
        """Centraliza o efeito no ponto dado (ex.: pés do jogador, centro do
        inimigo atingido). Se a folha daquele efeito ainda não foi carregada
        (ex.: parry_flash.png antes de existir no disco, ver __init__), não
        faz nada — silencioso de propósito, pra um asset pendente nunca
        travar a jogabilidade."""
        if kind not in self.frames:
            return
        self.active.append({"kind": kind, "x": center_x, "y": center_y, "elapsed": 0})

    def update(self):
        still_active = []
        for particle in self.active:
            particle["elapsed"] += 1
            info = self.DEFS[particle["kind"]]
            frame_index = particle["elapsed"] * info["fps"] // 60
            if frame_index < info["frames"]:
                still_active.append(particle)
            elif info["loop"]:
                particle["elapsed"] = 0
                still_active.append(particle)
        self.active = still_active

    def draw(self, surface, camera_x, camera_y):
        for particle in self.active:
            info = self.DEFS[particle["kind"]]
            frame_index = min(info["frames"] - 1, particle["elapsed"] * info["fps"] // 60)
            frame = self.frames[particle["kind"]][frame_index]
            surface.blit(
                frame,
                (
                    particle["x"] - camera_x - self.FRAME_SIZE // 2,
                    particle["y"] - camera_y - self.FRAME_SIZE // 2,
                ),
            )
