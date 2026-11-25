"""Builds 'Liquidity X-Ray' for EaglercraftX / Minecraft 1.8 (pack_format 1).
Hides common filler blocks (empty models) and redraws ores/valuables without cullface so they stay
visible through the hidden blocks. Contains no Mojang textures: only JSON models pointing at the
game's own textures, plus a generated icon.  Usage: python3 build_xray_pack.py [out.zip]"""
import io, json, sys, zipfile
from PIL import Image, ImageDraw

OUT = sys.argv[1] if len(sys.argv) > 1 else 'Liquidity-XRay-Outlines.zip'
MODE = sys.argv[2] if len(sys.argv) > 2 else 'outlines'   # 'outlines' or 'classic'
assert MODE in ('outlines', 'classic')

# Model names checked against this game build's own blockstates (EaglercraftX 1.9.4-u35):
# e.g. stone randomly uses 'stone' OR 'stone_mirrored', so both must be hidden.
HIDE = {  # model name -> particle texture (keeps break particles sensible)
    'stone': 'stone', 'stone_mirrored': 'stone', 'granite': 'stone_granite', 'granite_smooth': 'stone_granite_smooth',
    'diorite': 'stone_diorite', 'diorite_smooth': 'stone_diorite_smooth',
    'andesite': 'stone_andesite', 'andesite_smooth': 'stone_andesite_smooth',
    'dirt': 'dirt', 'coarse_dirt': 'coarse_dirt', 'podzol': 'dirt_podzol_side',
    'grass_normal': 'dirt', 'grass_snowed': 'dirt', 'mycelium': 'dirt',
    'gravel': 'gravel', 'sand': 'sand', 'red_sand': 'red_sand',
    'sandstone_normal': 'sandstone_normal', 'sandstone_smooth': 'sandstone_smooth',
    'sandstone_chiseled': 'sandstone_carved',
    'red_sandstone_normal': 'red_sandstone_normal', 'red_sandstone_smooth': 'red_sandstone_smooth',
    'red_sandstone_chiseled': 'red_sandstone_carved',
    'cobblestone': 'cobblestone',  # mossy_cobblestone stays visible (dungeons)
    'netherrack': 'netherrack', 'end_stone': 'end_stone', 'soul_sand': 'soul_sand',
    'clay': 'clay', 'hardened_clay': 'hardened_clay',
}
SHOW = {  # model name -> texture
    'coal_ore': 'coal_ore', 'iron_ore': 'iron_ore', 'gold_ore': 'gold_ore',
    'diamond_ore': 'diamond_ore', 'emerald_ore': 'emerald_ore', 'lapis_ore': 'lapis_ore',
    'redstone_ore': 'redstone_ore', 'lit_redstone_ore': 'redstone_ore', 'quartz_ore': 'quartz_ore',
    'mob_spawner_cage': 'mob_spawner',
}

# Item icons: hidden blocks would otherwise also vanish from the inventory/hotbar, because
# item models inherit the block model. Item names taken from this game build.
ITEMS = {  # item model -> block model it normally uses
    'andesite': 'andesite',
    'andesite_smooth': 'andesite_smooth',
    'chiseled_red_sandstone': 'red_sandstone_chiseled',
    'chiseled_sandstone': 'sandstone_chiseled',
    'clay': 'clay',
    'coarse_dirt': 'coarse_dirt',
    'cobblestone': 'cobblestone',
    'cobblestone_monster_egg': 'cobblestone',
    'diorite': 'diorite',
    'diorite_smooth': 'diorite_smooth',
    'dirt': 'dirt',
    'end_stone': 'end_stone',
    'granite': 'granite',
    'granite_smooth': 'granite_smooth',
    'grass': 'grass_normal',
    'gravel': 'gravel',
    'hardened_clay': 'hardened_clay',
    'mycelium': 'mycelium',
    'netherrack': 'netherrack',
    'podzol': 'podzol',
    'red_sand': 'red_sand',
    'red_sandstone': 'red_sandstone_normal',
    'sand': 'sand',
    'sandstone': 'sandstone_normal',
    'smooth_red_sandstone': 'red_sandstone_smooth',
    'smooth_sandstone': 'sandstone_smooth',
    'soul_sand': 'soul_sand',
    'stone': 'stone',
    'stone_monster_egg': 'stone',
}
ITEM_TEX_OVERRIDE = {'grass_normal': 'grass_side', 'mycelium': 'mycelium_side'}  # nicer icon than the particle texture

FRAME = 'liquidity_xray_frame'
W = 0.25  # line width in model pixels (16 = one block) -> 1/64 of a block


def frame_model():
    """Thin opaque strips around the edge of each of the 6 faces, nothing inside.
    No transparency needed (some GPUs/Eaglercraft setups draw transparent pixels black).
    Every strip has cullface = its face's direction, so a face's outline is skipped when
    that side touches another solid block: only faces exposed to air get outlined."""
    els = []
    def strip(face, frm, to):
        els.append({"from": frm, "to": to, "faces": {face: {"uv": [0, 0, 16, 16], "texture": "#line", "cullface": face}}})
    # rectangles on each face plane: 4 strips each
    for face, axis, val in (("north", 2, 0), ("south", 2, 16), ("west", 0, 0), ("east", 0, 16), ("down", 1, 0), ("up", 1, 16)):
        other = [a for a in (0, 1, 2) if a != axis]
        a, b = other
        def box(a0, a1, b0, b1):
            frm = [0, 0, 0]; to = [0, 0, 0]
            frm[axis] = to[axis] = val
            frm[a], to[a] = a0, a1; frm[b], to[b] = b0, b1
            return frm, to
        for (a0, a1, b0, b1) in ((0, 16, 0, W), (0, 16, 16 - W, 16), (0, W, W, 16 - W), (16 - W, 16, W, 16 - W)):
            strip(face, *box(a0, a1, b0, b1))
    return {"textures": {"line": "blocks/liquidity_xray_line", "particle": "blocks/liquidity_xray_line"},
            "elements": els}


def hidden(tex):
    # Parent-only model pointing at the shared frame (Eaglercraft: parent OR elements, not both).
    return {"parent": "block/" + FRAME, "textures": {"particle": "blocks/" + tex}}


def line_png():
    im = Image.new('RGBA', (16, 16), (150, 150, 150, 255))  # fully opaque
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()


def hidden_classic(tex):
    # Classic look: fully invisible. A single zero-size element (valid for Eaglercraft's loader,
    # which needs EITHER "parent" OR non-empty "elements"), so nothing is drawn.
    return {"textures": {"particle": "blocks/" + tex, "x": "blocks/" + tex},
            "elements": [{"from": [8, 8, 8], "to": [8, 8, 8],
                          "faces": {"up": {"uv": [0, 0, 0, 0], "texture": "#x"}}}]}


def outline_png():
    # 64x64 with a 1-pixel border -> lines are 1/64 of a block wide (a 16x16 texture made them
    # 4x thicker, which filled the screen in narrow tunnels). Dim grey so it stays subtle.
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 63, 63], outline=(150, 150, 150, 255))
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()


# Same hand-held/third-person placement as vanilla 1.8 block/block (no parent allowed with elements)
DISPLAY = {"thirdperson": {"rotation": [10, -45, 170], "translation": [0, 1.5, -2.75],
                           "scale": [0.375, 0.375, 0.375]}}

def visible(tex):
    face = {"uv": [0, 0, 16, 16], "texture": "#all"}  # no "cullface": always drawn
    return {"display": DISPLAY,
            "textures": {"all": "blocks/" + tex, "particle": "blocks/" + tex},
            "elements": [{"from": [0, 0, 0], "to": [16, 16, 16],
                          "faces": {f: dict(face) for f in ("down", "up", "north", "south", "west", "east")}}]}

def icon():
    im = Image.new('RGBA', (64, 64), (20, 20, 26, 255) if MODE == 'outlines' else (52, 22, 70, 255))
    d = ImageDraw.Draw(im)
    if MODE == 'outlines':  # wireframe grid + ores
        for k in range(0, 64, 16):
            d.line([(k, 0), (k, 63)], fill=(150, 150, 150, 255)); d.line([(0, k), (63, k)], fill=(150, 150, 150, 255))
    for (x, y, c) in [(10, 12, (90, 220, 255)), (36, 30, (60, 200, 90)), (16, 40, (230, 190, 60)), (40, 8, (220, 60, 60))]:
        d.rectangle([x, y, x + 13, y + 13], fill=c + (255,), outline=(255, 255, 255, 255))
    d.rectangle([0, 50, 63, 63], fill=(0, 0, 0, 200))
    d.text((3, 51), "OUTLINE" if MODE == 'outlines' else "CLASSIC", fill=(255, 255, 255, 255))
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()


with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('pack.mcmeta', json.dumps({"pack": {"pack_format": 1,
        "description": ("X-Ray Outlines: cave walls outlined, ores visible" if MODE == "outlines" else "X-Ray Classic: filler invisible, no outlines")}}, indent=1))
    z.writestr('pack.png', icon())
    if MODE == 'outlines':
        z.writestr('assets/minecraft/textures/blocks/liquidity_xray_line.png', line_png())
        z.writestr('assets/minecraft/models/block/%s.json' % FRAME, json.dumps(frame_model()))
    for name, tex in HIDE.items():
        z.writestr('assets/minecraft/models/block/%s.json' % name, json.dumps(hidden(tex) if MODE == 'outlines' else hidden_classic(tex)))
    for item, blk in ITEMS.items():
        tex = ITEM_TEX_OVERRIDE.get(blk, HIDE[blk])
        z.writestr('assets/minecraft/models/item/%s.json' % item,
                   json.dumps({"parent": "block/cube_all", "textures": {"all": "blocks/" + tex}}))
    for name, tex in SHOW.items():
        z.writestr('assets/minecraft/models/block/%s.json' % name, json.dumps(visible(tex)))
print('built', OUT, MODE, len(HIDE), 'hidden,', len(SHOW), 'highlighted,', len(ITEMS), 'item icons kept')
