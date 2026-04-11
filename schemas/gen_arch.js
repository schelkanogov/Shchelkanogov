const fs = require('fs');
const zlib = require('zlib');
const https = require('https');
const path = require('path');

function encode64(data) {
  let r = "";
  for (let i = 0; i < data.length; i += 3) {
    if (i + 2 == data.length) {
      r += append3bytes(data.charCodeAt(i), data.charCodeAt(i + 1), 0);
    } else if (i + 1 == data.length) {
      r += append3bytes(data.charCodeAt(i), 0, 0);
    } else {
      r += append3bytes(
        data.charCodeAt(i),
        data.charCodeAt(i + 1),
        data.charCodeAt(i + 2)
      );
    }
  }
  return r;
}

function append3bytes(b1, b2, b3) {
  let c1 = b1 >> 2;
  let c2 = ((b1 & 0x3) << 4) | (b2 >> 4);
  let c3 = ((b2 & 0xf) << 2) | (b3 >> 6);
  let c4 = b3 & 0x3f;
  let r = "";
  r += encode6bit(c1 & 0x3f);
  r += encode6bit(c2 & 0x3f);
  r += encode6bit(c3 & 0x3f);
  r += encode6bit(c4 & 0x3f);
  return r;
}

function encode6bit(b) {
  if (b < 10) return String.fromCharCode(48 + b);
  b -= 10;
  if (b < 26) return String.fromCharCode(65 + b);
  b -= 26;
  if (b < 26) return String.fromCharCode(97 + b);
  b -= 26;
  if (b == 0) return "-";
  if (b == 1) return "_";
  return "?";
}

function generate(name) {
    const text = fs.readFileSync(`D:\\Pavel\\Рабочий стол\\!!! АВТОМАТИЗАЦИЯ !!!\\!!! Щелканогов Павел !!!\\Shchelkanogov\\schemas\\${name}.puml`, 'utf8');
    const deflated = zlib.deflateSync(text, { level: 9 });
    const encoded = encode64(deflated.toString('binary'));
    
    const url = `https://www.plantuml.com/plantuml/png/${encoded}`;
    
    https.get(url, (res) => {
        if (res.statusCode === 200) {
            const file = fs.createWriteStream(`D:\\Pavel\\Рабочий стол\\!!! АВТОМАТИЗАЦИЯ !!!\\!!! Щелканогов Павел !!!\\Shchelkanogov\\schemas\\puml_${name}.png`);
            res.pipe(file);
            file.on('finish', () => console.log(`Generated ${name}`));
        } else {
            console.log(`Failed ${name} - Status: ${res.statusCode}`);
        }
    }).on('error', (e) => console.error(e));
}

generate('architecture');
generate('resolution_flow');
generate('ai_orchestration');
