"""Writes the two pack icons used on the /minecraft page: xray.png and fullbright.png (64x64)."""
import sys
from PIL import Image, ImageDraw
out = sys.argv[1] if len(sys.argv) > 1 else '.'

im = Image.new('RGBA', (64, 64), (20, 20, 26, 255)); d = ImageDraw.Draw(im)
for (x, y, c) in [(10, 12, (90, 220, 255)), (36, 30, (60, 200, 90)), (16, 40, (230, 190, 60)), (40, 8, (220, 60, 60))]:
    d.rectangle([x, y, x + 13, y + 13], fill=c + (255,), outline=(255, 255, 255, 255))
d.text((4, 52), "X-RAY", fill=(255, 255, 255, 255)); im.save(out + '/xray.png')

im = Image.new('RGBA', (64, 64), (24, 30, 52, 255)); d = ImageDraw.Draw(im)
for i in range(8):  # pixel sun rays
    import math
    a = i * math.pi / 4; x, y = 32 + 24 * math.cos(a), 30 + 24 * math.sin(a)
    d.rectangle([x - 3, y - 3, x + 3, y + 3], fill=(255, 214, 80, 255))
d.ellipse([18, 16, 46, 44], fill=(255, 236, 120, 255), outline=(255, 190, 40, 255), width=3)
d.text((2, 52), "BRIGHT", fill=(255, 255, 255, 255)); im.save(out + '/fullbright.png')
print('icons written to', out)
