from PIL import Image
import os

png_path = r"c:\Users\vrusu\Translate\lingua_beta\lingua\resources\icon_new.png"
ico_path = r"c:\Users\vrusu\Translate\lingua_beta\lingua\resources\icon.ico"
icns_path = r"c:\Users\vrusu\Translate\lingua_beta\lingua\resources\icon.icns"
old_ico_path = r"c:\Users\vrusu\Translate\lingua_beta\lingua\resources\icon_old.ico"

# Backup old icon
if os.path.exists(ico_path) and not os.path.exists(old_ico_path):
    os.rename(ico_path, old_ico_path)

# Convert PNG to ICO while preserving transparency
img = Image.open(png_path)
# Ensure it's RGBA
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Define standard icon sizes
icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(ico_path, format='ICO', sizes=icon_sizes)
print(f"Successfully converted {png_path} to {ico_path} with transparency.")

# Convert to ICNS for macOS
img.save(icns_path, format='ICNS')
print(f"Successfully converted {png_path} to {icns_path} for macOS.")
