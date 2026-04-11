const fs = require('fs');
const http = require('https');
const path = require('path');

const schemas = ["architecture", "resolution_flow", "ai_orchestration"];
const dir = __dirname;

schemas.forEach(name => {
    const pumlPath = path.join(dir, `${name}.puml`);
    let content = fs.readFileSync(pumlPath, 'utf8');
    
    // Remove BOM if exists
    if (content.charCodeAt(0) === 0xFEFF) {
        content = content.slice(1);
    }
    
    const postData = JSON.stringify({
        diagram_source: content,
        diagram_type: "plantuml",
        output_format: "png"
    });

    const req = http.request('https://kroki.io', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        }
    }, (res) => {
        if (res.statusCode === 200) {
            const outPath = path.join(dir, `gen_${name}.png`);
            const file = fs.createWriteStream(outPath);
            res.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log(`Successfully generated gen_${name}.png`);
            });
        } else {
            console.error(`Failed to generate ${name}, Status: ${res.statusCode}`);
            res.on('data', d => process.stdout.write(d));
        }
    });

    req.on('error', (e) => {
        console.error(`Problem with request for ${name}: ${e.message}`);
    });

    req.write(postData);
    req.end();
});
