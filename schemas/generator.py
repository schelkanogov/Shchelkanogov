import os
import urllib.request
import zlib
import base64

def encode_plantuml(puml_text):
    zlibbed = zlib.compress(puml_text.encode('utf-8'))
    compact_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    b64 = base64.b64encode(zlibbed[2:-4])
    def encode6bit(b):
        if b < 10: return chr(48 + b)
        b -= 10
        if b < 26: return chr(65 + b)
        b -= 26
        if b < 26: return chr(97 + b)
        b -= 26
        if b == 0: return '-'
        if b == 1: return '_'
        return '?'
    
    res = ""
    i = 0
    while i < len(zlibbed[2:-4]):
        b1 = zlibbed[2:-4][i]
        b2 = zlibbed[2:-4][i+1] if i+1 < len(zlibbed[2:-4]) else 0
        b3 = zlibbed[2:-4][i+2] if i+2 < len(zlibbed[2:-4]) else 0
        res += encode6bit(b1 >> 2)
        res += encode6bit(((b1 & 0x3) << 4) | (b2 >> 4))
        res += encode6bit(((b2 & 0xF) << 2) | (b3 >> 6)) if i+1 < len(zlibbed[2:-4]) else ""
        res += encode6bit(b3 & 0x3F) if i+2 < len(zlibbed[2:-4]) else ""
        i += 3
    return res

schemas = ["architecture", "resolution_flow", "ai_orchestration"]
out_dir = r"D:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\!!! Щелканогов Павел !!!\Shchelkanogov\schemas"

for name in schemas:
    with open(os.path.join(out_dir, f"{name}.puml"), "r", encoding="utf-8") as f:
        text = f.read()
    
    url = f"http://www.plantuml.com/plantuml/png/{encode_plantuml(text)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                with open(os.path.join(out_dir, f"puml_{name}.png"), "wb") as f:
                    f.write(response.read())
                print(f"Generated puml_{name}.png")
            else:
                print(f"Failed to generate {name}. Status: {response.status}")
    except Exception as e:
        print(f"Failed {name}: {e}")

