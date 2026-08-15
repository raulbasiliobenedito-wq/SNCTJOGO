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
    # direto do LEIA-ME_integracao.md (seção "vfx.png").
    DEFS = {
        "impact": {"row": 0, "frames": 6, "fps": 18, "loop": False},
        "dust": {"row": 1, "frames": 5, "fps": 16, "loop": False},
        "splash": {"row": 2, "frames": 5, "fps": 16, "loop": False},
        "ember": {"row": 3, "frames": 8, "fps": 6, "loop": True},
        "slash": {"row": 4, "frames": 4, "fps": 20, "loop": False},
    }

    def __init__(self, sheet_path):
        sheet = pygame.image.load(sheet_path).convert_alpha()
        self.frames = {}
        for name, info in self.DEFS.items():
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
        inimigo atingido)."""
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
