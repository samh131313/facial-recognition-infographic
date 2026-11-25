"""Builds 'Liquidity X-Ray' for EaglercraftX / Minecraft 1.8 (pack_format 1).
Hides common filler blocks (empty models) and redraws ores/valuables without cullface so they stay
visible through the hidden blocks. Contains no Mojang textures: only JSON models pointing at the
game's own textures, plus a generated icon.  Usage: python3 build_xray_pack.py [out.zip]"""
import io, json, sys, zipfile
from PIL import Image, ImageDraw

OUT = sys.argv[1] if len(sys.argv) > 1 else 'Liquidity-XRay.zip'

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
    'netherrack': 'netherrack', 'end_stone': 'end_stone', 'soul_sand': 'soul_sand',
    'clay': 'clay', 'hardened_clay': 'hardened_clay',
}
SHOW = {  # model name -> texture
    'coal_ore': 'coal_ore', 'iron_ore': 'iron_ore', 'gold_ore': 'gold_ore',
    'diamond_ore': 'diamond_ore', 'emerald_ore': 'emerald_ore', 'lapis_ore': 'lapis_ore',
    'redstone_ore': 'redstone_ore', 'lit_redstone_ore': 'redstone_ore', 'quartz_ore': 'quartz_ore',
    'mob_spawner_cage': 'mob_spawner',
}

def hidden(tex):
    # A single zero-size element: valid for the model loader, but nothing to draw.
    # Eaglercraft's loader needs EITHER "parent" OR non-empty "elements" (never both, never []).
    return {"textures": {"particle": "blocks/" + tex, "x": "blocks/" + tex},
            "elements": [{"from": [8, 8, 8], "to": [8, 8, 8],
                          "faces": {"up": {"uv": [0, 0, 0, 0], "texture": "#x"}}}]}

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
    im = Image.new('RGBA', (64, 64), (20, 20, 26, 255)); d = ImageDraw.Draw(im)
    for (x, y, c) in [(10, 12, (90, 220, 255)), (36, 30, (60, 200, 90)), (16, 40, (230, 190, 60)), (40, 8, (220, 60, 60))]:
        d.rectangle([x, y, x + 13, y + 13], fill=c + (255,), outline=(255, 255, 255, 255))
    d.text((4, 52), "X-RAY", fill=(255, 255, 255, 255))
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('pack.mcmeta', json.dumps({"pack": {"pack_format": 1,
        "description": "Liquidity X-Ray: ores visible, filler hidden"}}, indent=1))
    z.writestr('pack.png', icon())
    for name, tex in HIDE.items():
        z.writestr('assets/minecraft/models/block/%s.json' % name, json.dumps(hidden(tex)))
    for name, tex in SHOW.items():
        z.writestr('assets/minecraft/models/block/%s.json' % name, json.dumps(visible(tex)))
print('built', OUT, len(HIDE), 'hidden,', len(SHOW), 'highlighted')
