"""Build SoundUp PNG/ICO assets from the supplied neon artwork."""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / ".build" / "new_logo_source.png"
PNG_OUT = ROOT / "soundup.png"
ICO_OUT = ROOT / "soundup.ico"
ICO_INSTALLER = ROOT / "installer" / "wix" / "soundup.ico"

with Image.open(SOURCE) as source:
    image = source.convert("RGBA")

print("origem:", image.size, image.mode)
for point in ((0, 0), (image.width - 1, 0), (0, image.height - 1),
              (image.width - 1, image.height - 1)):
    print("canto", point, image.getpixel(point))

# Remove the white studio background by flooding from every corner. The dark
# outline around the badge and the lettering stops the fill, so white details
# inside the artwork are preserved.
for corner in ((0, 0), (image.width - 1, 0),
               (0, image.height - 1), (image.width - 1, image.height - 1)):
    ImageDraw.floodfill(image, corner, (0, 0, 0, 0), thresh=48)

alpha = image.getchannel("A")
bbox = alpha.getbbox()
print("bbox:", bbox)
image = image.crop(bbox)
print("recortado:", image.size)

# Square canvas with a small transparent margin so taskbar icons breathe.
side = max(image.size)
margin = int(side * 0.04)
canvas = Image.new("RGBA", (side + margin * 2, side + margin * 2), (0, 0, 0, 0))
canvas.paste(image, ((canvas.width - image.width) // 2,
                     (canvas.height - image.height) // 2), image)
canvas = canvas.resize((1024, 1024), Image.LANCZOS)

PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.resize((512, 512), Image.LANCZOS).save(PNG_OUT, "PNG", optimize=True)

sizes = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40),
         (48, 48), (64, 64), (128, 128), (256, 256)]
for target in (ICO_OUT, ICO_INSTALLER):
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, format="ICO", sizes=sizes)

print("png:", PNG_OUT, PNG_OUT.stat().st_size)
print("ico:", ICO_OUT, ICO_OUT.stat().st_size)
print("ico instalador:", ICO_INSTALLER, ICO_INSTALLER.stat().st_size)
print("cores por canto do png:", [canvas.getpixel(p) for p in
      ((0, 0), (canvas.width - 1, 0), (0, canvas.height - 1),
       (canvas.width - 1, canvas.height - 1))])
