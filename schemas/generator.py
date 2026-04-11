import os
import urllib.request
import zlib
import base64

def encode_kroki(puml_text):
    return base64.urlsafe_b64encode(zlib.compress(puml_text.encode('utf-8'), 9)).decode('ascii')

schemas = ["architecture", "resolution_flow", "ai_orchestration"]
out_dir = r"D:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\!!! Щелканогов Павел !!!\Shchelkanogov\schemas"

for name in schemas:
    with open(os.path.join(out_dir, f"{name}.puml"), "r", encoding="utf-8") as f:
        text = f.read()
    
    # Use standard C4 PlantUML macro support via Kroki
    url = f"https://kroki.io/plantuml/png/{encode_kroki(text)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                with open(os.path.join(out_dir, f"puml_{name}.png"), "wb") as f:
                    f.write(response.read())
                print(f"Generated puml_{name}.png via Kroki")
            else:
                print(f"Failed to generate {name}. Status: {response.status}")
    except Exception as e:
        print(f"Failed {name}: {e}")
