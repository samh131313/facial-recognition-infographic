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

def hidden(tex):
    # Full cube drawn with a see-through texture that only has a thin border.
    # cube_all keeps "cullface", so faces touching other solid blocks are skipped and
    # only faces exposed to air (cave walls, floors, ceilings) show their outline.
    # Parent-only model: Eaglercraft rejects models with both "parent" and "elements".
    return {"parent": "block/cube_all",
            "textures": {"all": "blocks/liquidity_xray_outline", "particle": "blocks/" + tex}}


def outline_png():
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 15, 15], outline=(205, 205, 205, 255))
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
    im = Image.new('RGBA', (64, 64), (20, 20, 26, 255)); d = ImageDraw.Draw(im)
    for (x, y, c) in [(10, 12, (90, 220, 255)), (36, 30, (60, 200, 90)), (16, 40, (230, 190, 60)), (40, 8, (220, 60, 60))]:
        d.rectangle([x, y, x + 13, y + 13], fill=c + (255,), outline=(255, 255, 255, 255))
    d.text((4, 52), "X-RAY", fill=(255, 255, 255, 255))
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('pack.mcmeta', json.dumps({"pack": {"pack_format": 1,
        "description": "Liquidity X-Ray: ores visible, cave outlines"}}, indent=1))
    z.writestr('pack.png', icon())
    z.writestr('assets/minecraft/textures/blocks/liquidity_xray_outline.png', outline_png())
    for name, tex in HIDE.items():
        z.writestr('assets/minecraft/models/block/%s.json' % name, json.dumps(hidden(tex)))
    for item, blk in ITEMS.items():
        tex = ITEM_TEX_OVERRIDE.get(blk, HIDE[blk])
        z.writestr('assets/minecraft/models/item/%s.json' % item,
                   json.dumps({"parent": "block/cube_all", "textures": {"all": "blocks/" + tex}}))
    for name, tex in SHOW.items():
        z.writestr('assets/minecraft/models/block/%s.json' % name, json.dumps(visible(tex)))
print('built', OUT, len(HIDE), 'hidden,', len(SHOW), 'highlighted,', len(ITEMS), 'item icons kept')
