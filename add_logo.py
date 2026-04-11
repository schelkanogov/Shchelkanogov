import os
from PIL import Image

def add_watermark(bg_path, logo_path, out_path):
    print(f"Processing {bg_path}...")
    try:
        # Load background (PlantUML schema)
        bg = Image.open(bg_path).convert("RGBA")
        
        # Load logo
        logo = Image.open(logo_path).convert("RGBA")
        
        # Scale logo down so it fits nicely in the corner
        # The schema is roughly 1500-2000px wide. Logo is probably a few hundred.
        target_logo_width = 300
        aspect_ratio = logo.height / logo.width
        new_height = int(target_logo_width * aspect_ratio)
        logo = logo.resize((target_logo_width, new_height), Image.LANCZOS)
        
        # Paste logo at top-right corner with 40px padding
        padding = 40
        x = bg.width - logo.width - padding
        y = padding
        if x < 0: x = 0
        
        bg.paste(logo, (x, y), logo)
        
        # Save output
        bg.save(out_path, "PNG")
        print(f"Saved {out_path}")
    except Exception as e:
        print(f"Error processing {bg_path}: {e}")

base_dir = r"D:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\!!! Щелканогов Павел !!!\Shchelkanogov"
bg_arch = os.path.join(base_dir, "images", "architecture.png")
bg_life = os.path.join(base_dir, "images", "lifecycle.png")
logo = r"D:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\!!! Детектор Уязвимостей !!!\Разное\Лого\VulnDetector\logo (1).png"

out_arch = os.path.join(base_dir, "images", "architecture_v21.png")
out_life = os.path.join(base_dir, "images", "lifecycle_v21.png")

add_watermark(bg_arch, logo, out_arch)
add_watermark(bg_life, logo, out_life)
