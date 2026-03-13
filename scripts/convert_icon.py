from PIL import Image
import os

source_png = r"C:\Users\vrusu\.gemini\antigravity\brain\27693f04-6129-49eb-a34e-811668e45e63\lingua_icon_concept_1_1773349704893.png"
res_dir = r"c:\Users\vrusu\Translate\lingua_beta\lingua\resources"

if not os.path.exists(res_dir):
    os.makedirs(res_dir)

# 1. Save as icon.png (256x256 is usually enough for app icons)
img = Image.open(source_png)
img_png = img.resize((256, 256), Image.Resampling.LANCZOS)
img_png.save(os.path.join(res_dir, "icon.png"))
print(f"Saved {os.path.join(res_dir, 'icon.png')}")

# 2. Save as icon.ico (multisize)
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(os.path.join(res_dir, "icon.ico"), sizes=icon_sizes)
print(f"Saved {os.path.join(res_dir, 'icon.ico')}")
