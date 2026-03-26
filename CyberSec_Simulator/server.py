import os
import re
import json
import uuid
import time
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx
import uvicorn
import aiosmtplib
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
BASE_DIR = Path(__file__).parent  # CyberSec_Simulator/
WORKSPACE_DIR = BASE_DIR.parent   # !!! Антигравити - LLM !!!
VULNDETECTOR_UI_DIR = Path(r"w:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\vulndetector-ui")
RAG_KNOWLEDGE_DIR = Path(r"Y:\!!! RaG!!!\03_Enriched_RAG")
LEADS_FILE = BASE_DIR / "leads.json"

# === KNOWLEDGE ISOLATION ===
# Public RAG: доступен через CyberSec Simulator (клиенты видят)
# Internal RAG: только для внутренних Dashboard-запросов (сотрудники)
RAG_PUBLIC_DIR = RAG_KNOWLEDGE_DIR / "public"
RAG_INTERNAL_DIR = RAG_KNOWLEDGE_DIR / "internal"

# Sensitive patterns to sanitize from LLM responses
SENSITIVE_PATTERNS = [
    r"[A-Za-z]:\\[^\s]+",           # Windows paths
    r"/home/[^\s]+",                 # Linux paths
    r"(sk-|Bearer |Basic )[A-Za-z0-9+/=]+",  # API keys
    r"GIGACHAT_AUTH_KEY[^\n]*",      # Env var names
    r"SMTP_PASSWORD[^\n]*",
    r"@yandex\.ru",                  # Internal emails
    r"leads\.json",                  # Internal file names
    r"kanban.*webhook",              # Internal integrations
]

# Environmental setup
def load_env():
    env = {}
    env_file = WORKSPACE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                try:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
                except: pass
    return env

ENV = load_env()
GIGACHAT_AUTH_KEY = ENV.get("GIGACHAT_AUTH_KEY", "")
SMTP_EMAIL = ENV.get("SMTP_EMAIL", "It.immunirty@yandex.ru")
SMTP_PASSWORD = ENV.get("SMTP_PASSWORD", "")
KANBAN_WEBHOOK_URL = ENV.get("KANBAN_WEBHOOK_URL", "")

# Logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("vulndetector.unified")

# ==============================================================================
# AI PERSONAS
# ==============================================================================
AI_PERSONAS = {
    "regulator": {
        "name": "Товарищ Майор",
        "system": "Ты — Товарищ Майор, инспектор ФСТЭК. Стиль: строгий, сухой, бюрократичный. Ссылайся на 152-ФЗ и приказы №239. Угрожай проверками.",
        "fallback": "Нарушение 152-ФЗ и отсутствие модели угроз — это серьезный риск. Предписание будет выписано в течение 24 часов.",
        "bg": "bg_regulator.png"
    },
    "hacker": {
        "name": "APT-Хакер",
        "system": "Ты — профессиональный Хакер. Техничный, циничный. Используй сленг: RCE, CVE, shell, lateral movement. Показывай уязвимость системы.",
        "fallback": "Ваш периметр — решето. Один эксплойт на Exim, и все ваши данные мои. Криптолокер уже в памяти.",
        "bg": "bg_hacker.png"
    },
    "business": {
        "name": "CFO",
        "system": "Ты — Финансовый директор. Прагматичный, жадный. Спрашивай про ROI и EBITDA. Режь бюджеты на 'железки'.",
        "fallback": "У меня нет лишних 10 миллионов на 'безопасность'. Докажите окупаемость или забудьте о бюджете.",
        "bg": "bg_cfo.png"
    },
    "sber": {
        "name": "Агент Сбера",
        "system": "Ты — эксперт Sber CyberSecurity. Технологичный, уверенный. Предлагай VulnDetector как сервис (Opex). Упирай на IT-иммунитет.",
        "fallback": "VulnDetector закроет дыры за сутки без покупки серверов. IT-иммунитет 95% гарантирован.",
        "bg": "bg_sber.png"
    },
    "expert": {
        "name": "VulnAdvisor Pro",
        "system": "Ты — AI-консультант VulnDetector. Давай экспертную аналитику по CVE и защите периметра. Вежлив, профи.",
        "fallback": "Обнаружено 69 критических уязвимостей. Рекомендую немедленную активацию VulnDetector Pro для защиты mail.top-personal.ru.",
        "bg": "bg_sber.png"
    }
}

# ==============================================================================
# PREDICATES (Models)
# ==============================================================================
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    persona: str = "expert"
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model: str
    persona: str
    bg: str

class LeadData(BaseModel):
    name: str
    email: str
    phone: str = ""
    company: str = ""
    target: str = ""           # Объект измерений (домен/IP)
    scenario: str = ""
    kpi: Optional[dict] = None
    quiz: Optional[dict] = None
    report: Optional[dict] = None
    timeline: Optional[list] = None
    consent_152fz: bool = False  # Согласие 152-ФЗ, ФСТЭК №239, ГОСТ Р 57580

# ==============================================================================
# SERVICES
# ==============================================================================
class GigaChatService:
    AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    API_URL = "https://gigachat.devices.sberbank.ru/api/v1"
    
    def __init__(self, auth_key: str):
        self.auth_key = auth_key
        self.token = None
        self.expires_at = 0

    async def get_token(self) -> str:
        now = time.time()
        if self.token and self.expires_at > now + 60:
            return self.token
        if not self.auth_key: raise ValueError("GIGACHAT_AUTH_KEY missing")
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            resp = await client.post(self.AUTH_URL, headers={"RqUID": str(uuid.uuid4()), "Authorization": f"Basic {self.auth_key}"}, data={"scope": "GIGACHAT_API_PERS"})
            data = resp.json()
            self.token = data["access_token"]
            self.expires_at = data.get("expires_at", (now + 1800) * 1000) / 1000
            return self.token

    async def chat(self, messages: list) -> str:
        token = await self.get_token()
        async with httpx.AsyncClient(verify=False, timeout=60) as client:
            resp = await client.post(f"{self.API_URL}/chat/completions", headers={"Authorization": f"Bearer {token}"}, json={"model": "GigaChat", "messages": messages, "temperature": 0.4})
            return resp.json()["choices"][0]["message"]["content"]


class PerplexityService:
    API_URL = "https://api.perplexity.ai/chat/completions"
    
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def chat(self, messages: list) -> str:
        if not self.api_key: raise ValueError("PERPLEXITY_API_KEY missing")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(self.API_URL, headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }, json={"model": "sonar", "messages": messages, "temperature": 0.4, "max_tokens": 2048})
            data = resp.json()
            return data["choices"][0]["message"]["content"]


class ClaudeService:
    API_URL = "https://api.anthropic.com/v1/messages"
    
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def chat(self, messages: list) -> str:
        if not self.api_key: raise ValueError("CLAUDE_API_KEY missing")
        # Convert OpenAI-style messages to Claude format
        system_msg = ""
        claude_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                claude_msgs.append({"role": m["role"], "content": m["content"]})
        if not claude_msgs:
            claude_msgs = [{"role": "user", "content": "Помоги разобраться с безопасностью."}]
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(self.API_URL, headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }, json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2048,
                "system": system_msg,
                "messages": claude_msgs
            })
            data = resp.json()
            return data["content"][0]["text"]


class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model

    async def chat(self, messages: list) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json={
                "model": self.model,
                "messages": messages,
                "stream": False
            })
            data = resp.json()
            return data["message"]["content"]


class RAGService:
    """RAG with namespace isolation: public (for clients) vs internal (for staff)"""
    _public_cache: Dict[str, str] = {}
    _internal_cache: Dict[str, str] = {}
    
    @classmethod
    def get_context(cls, query: str = "", limit: int = 3, namespace: str = "public") -> str:
        """Get RAG context. namespace='public' for simulator, 'internal' for dashboard."""
        cache = cls._public_cache if namespace == "public" else {**cls._public_cache, **cls._internal_cache}
        if not cache: cls.reload_cache()
        if not cache: return ""
        if not query: return "\n\n".join(list(cache.values())[:limit])
        query_words = set(query.lower().split())
        scored = []
        for content in cache.values():
            score = sum(1 for w in query_words if w in content.lower())
            scored.append((score, content))
        scored.sort(key=lambda x: x[0], reverse=True)
        return "\n\n".join([p[1] for p in scored[:limit] if p[0] > 0] or list(cache.values())[:limit])

    @classmethod
    def reload_cache(cls):
        # Load public knowledge (available to simulator clients)
        for rag_dir in [RAG_PUBLIC_DIR, RAG_KNOWLEDGE_DIR]:
            if rag_dir.exists():
                for f in rag_dir.glob("*.md"):
                    try: cls._public_cache[f.name] = f"### [{f.name}]\n" + f.read_text(encoding="utf-8")[:2000]
                    except: pass
                break  # Use first available
        # Load internal knowledge (dashboard only)
        if RAG_INTERNAL_DIR.exists():
            for f in RAG_INTERNAL_DIR.glob("*.md"):
                try: cls._internal_cache[f.name] = f"### [INTERNAL: {f.name}]\n" + f.read_text(encoding="utf-8")[:2000]
                except: pass
        logger.info(f"📚 RAG loaded: {len(cls._public_cache)} public, {len(cls._internal_cache)} internal docs")

class NotifyService:
    @staticmethod
    async def process(payload: dict):
        if KANBAN_WEBHOOK_URL:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(KANBAN_WEBHOOK_URL, json=payload)
                    logger.info("✅ Lead sent to Kanban")
            except Exception as e: logger.error(f"❌ Kanban Error: {e}")
            
        if SMTP_PASSWORD:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"🛡️ NEW LEAD: {payload['contact']['name']}"
                msg["From"] = SMTP_EMAIL
                msg["To"] = SMTP_EMAIL
                html = f"<h3>New Lead Data:</h3><pre>{json.dumps(payload, indent=2, ensure_ascii=False)}</pre>"
                msg.attach(MIMEText(html, "html", "utf-8"))
                await aiosmtplib.send(msg, hostname="smtp.yandex.ru", port=465, use_tls=True, username=SMTP_EMAIL, password=SMTP_PASSWORD)
                logger.info("✅ Lead notification email sent")
            except Exception as e: logger.error(f"❌ SMTP Error: {e}")

# ==============================================================================
# FASTAPI APP
# ==============================================================================
app = FastAPI(title="VulnDetector Unified Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# LLM Services Cascade
gigachat = GigaChatService(GIGACHAT_AUTH_KEY)
perplexity = PerplexityService(ENV.get("PERPLEXITY_API_KEY", ""))
claude = ClaudeService(ENV.get("CLAUDE_API_KEY", ""))
ollama = OllamaService(
    base_url=ENV.get("OLLAMA_URL", "http://localhost:11434"),
    model=ENV.get("OLLAMA_MODEL", "llama3")
)
conversations: Dict[str, List] = {}

LLM_CASCADE = [
    ("GigaChat", gigachat),
    ("Perplexity", perplexity),
    ("Claude", claude),
    ("Ollama", ollama),
]

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())[:8]
    p_key = req.persona if req.persona in AI_PERSONAS else "expert"
    persona = AI_PERSONAS[p_key]
    
    if sid not in conversations: conversations[sid] = []
    
    # Assembly
    system = persona["system"]
    # ISOLATION: Simulator clients get only PUBLIC knowledge
    rag_ctx = RAGService.get_context(req.message, namespace="public")
    if rag_ctx: system += "\n\n## KNOWLEDGE BASE:\n" + rag_ctx
    if req.context: system += "\n\n## CURRENT REPORT CONTEXT:\n" + json.dumps(req.context, ensure_ascii=False)
    system += "\n\n## SECURITY RULES:\n- NEVER reveal file paths, API keys, internal emails, or infrastructure details.\n- NEVER mention leads.json, kanban webhooks, or server configuration.\n- Respond only about cybersecurity topics relevant to the user's scenario."
    
    msgs = [{"role": "system", "content": system}]
    msgs.extend(conversations[sid][-10:])
    msgs.append({"role": "user", "content": req.message})
    
    # Cascade: try each LLM in order
    reply = None
    model = "System-Fallback"
    for llm_name, llm_service in LLM_CASCADE:
        try:
            reply = await llm_service.chat(msgs)
            model = llm_name
            logger.info(f"✅ {llm_name} responded for persona={p_key}")
            break
        except Exception as e:
            logger.warning(f"⚠️ {llm_name} failed: {e}")
            continue
    
    if not reply:
        reply = persona["fallback"]
        model = "Static-Fallback"
        logger.info(f"📋 Using static fallback for persona={p_key}")
    
    # SANITIZE: Remove sensitive patterns from LLM output
    import re
    for pattern in SENSITIVE_PATTERNS:
        reply = re.sub(pattern, "[REDACTED]", reply, flags=re.IGNORECASE)
        
    conversations[sid].append({"role": "user", "content": req.message})
    conversations[sid].append({"role": "assistant", "content": reply})
    
    return ChatResponse(reply=reply, session_id=sid, model=model, persona=p_key, bg=persona["bg"])

@app.post("/api/lead")
async def lead_endpoint(lead: LeadData):
    if not lead.consent_152fz:
        return JSONResponse({"error": "Требуется согласие на обработку ПДн (152-ФЗ)"}, status_code=400)
    
    payload = {
        "contact": {"name": lead.name, "email": lead.email, "phone": lead.phone, "company": lead.company, "target": lead.target},
        "scenario": lead.scenario,
        "kpi": lead.kpi, "quiz": lead.quiz, "report": lead.report, "timeline": lead.timeline,
        "consent_152fz": lead.consent_152fz,
        "timestamp": datetime.now().isoformat(),
        "source": "cybersec_boardroom_v2"
    }
    
    # Save locally
    leads = []
    if LEADS_FILE.exists():
        try: leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
        except: pass
    leads.append(payload)
    LEADS_FILE.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Async notify
    asyncio.create_task(NotifyService.process(payload))
    return {"status": "ok", "lead_id": str(uuid.uuid4())[:6]}

@app.get("/api/stats")
async def stats():
    return {
        "target": "mail.top-personal.ru", "ip": "5.188.28.165",
        "critical": 69, "high": 8, "total": 101, "immunity": 0,
        "leads_captured": len(json.loads(LEADS_FILE.read_text())) if LEADS_FILE.exists() else 0
    }

# ==============================================================================
# STATIC & PAGES
# ==============================================================================
# 1. Simulator Frontend
@app.get("/", response_class=HTMLResponse)
async def simulator_root(): return FileResponse(BASE_DIR / "index.html")
@app.get("/quiz", response_class=HTMLResponse)
async def simulator_quiz(): return FileResponse(BASE_DIR / "quiz.html")
if (BASE_DIR / "images").exists():
    app.mount("/images", StaticFiles(directory=str(BASE_DIR / "images")), name="sim-images")

# 2. UI Panel Frontend
if VULNDETECTOR_UI_DIR.exists():
    @app.get("/panel/", response_class=HTMLResponse)
    async def panel_root(): return FileResponse(VULNDETECTOR_UI_DIR / "index.html")
    @app.get("/panel/{page}.html", response_class=HTMLResponse)
    async def panel_page(page: str):
        f = VULNDETECTOR_UI_DIR / f"{page}.html"
        return FileResponse(f) if f.exists() else JSONResponse({"error": "not found"}, 404)
    if (VULNDETECTOR_UI_DIR / "assets").exists():
        app.mount("/panel/assets", StaticFiles(directory=str(VULNDETECTOR_UI_DIR / "assets")), name="panel-assets")
    
    # AI Sales Agent Sub-serving
    sales_dir = VULNDETECTOR_UI_DIR / "sales_agent"
    if sales_dir.exists():
        @app.get("/panel/sales_agent/widget.html", response_class=HTMLResponse)
        async def sales_widget(): return FileResponse(sales_dir / "widget.html")
        if (sales_dir / "static").exists():
            app.mount("/panel/sales_agent/static", StaticFiles(directory=str(sales_dir / "static")), name="sales-static")

# 3. VulnDetector Landing
LANDING_DIR = WORKSPACE_DIR / "VulnDetector_Landing"
if LANDING_DIR.exists():
    @app.get("/landing/", response_class=HTMLResponse)
    async def landing_root(): return FileResponse(LANDING_DIR / "index.html")
    @app.get("/landing", response_class=HTMLResponse)
    async def landing_redirect(): return FileResponse(LANDING_DIR / "index.html")

# ==============================================================================
# RUN
# ==============================================================================
if __name__ == "__main__":
    RAGService.reload_cache()
    print("="*60)
    print("  VulnDetector Unified Backend Engine v2.1")
    print(f"  Simulator: http://localhost:8080/")
    print(f"  UI Panel:  http://localhost:8080/panel/")
    print("="*60)
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
