"""CV_MK V3 AI Career Engine."""
import os
from typing import Dict

from openai import AsyncOpenAI

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

DOMAIN_GUIDES: Dict[str, str] = {
    "it": "software engineering, architecture, stack depth, reliability, performance, delivery metrics",
    "design": "portfolio impact, UX process, design systems, research, conversion and usability outcomes",
    "marketing": "ROAS, CTR, CPA, CAC, conversion, attribution, campaign scale and revenue impact",
    "product": "roadmaps, discovery, prioritization, activation, retention, experiments and business outcomes",
    "finance": "IFRS/GAAP, reporting, forecasting, controls, audit, budgeting and measurable financial impact",
    "logistics": "SCM, WMS/TMS, inventory, OTIF, lead time, cost reduction, warehouse and transport KPIs",
    "sales": "pipeline, quota, win rate, ACV, revenue, conversion, retention and account growth",
    "hr": "time-to-hire, retention, sourcing, ATS, onboarding, hiring volume and quality metrics",
    "education": "curriculum, pedagogy, learner outcomes, assessment, classroom or training scale",
    "engineering": "CAD/BIM, standards, safety, tolerances, project delivery, quality and productivity",
    "energy": "generation, grid, solar/wind, O&M, safety, efficiency and technical compliance",
    "construction": "BIM, drawings, trades, schedule, budget, safety, quality, quantities and project phases",
    "medical": "clinical scope, patient safety, protocols, documentation, outcomes and regulated practice",
    "legal": "contracts, compliance, research, disputes, risk reduction and jurisdiction-specific work",
    "hospitality": "guest satisfaction, occupancy, service quality, upselling, hygiene and operations",
    "security": "risk, incident response, access control, monitoring, compliance and safety procedures",
    "transport": "licenses, routes, safety, punctuality, vehicle classes, mileage and delivery performance",
    "agriculture": "crop/livestock work, machinery, yields, harvest volume, quality and safety",
    "freelance": "client outcomes, scope ownership, delivery speed, repeat business and portfolio evidence",
    "startup": "traction, growth, fundraising, product-market fit, team leadership and unit economics",
    "general": "role-relevant responsibilities, tools, measurable outcomes and evidence of reliability",
}

def detect_domain(job: str) -> str:
    j = (job or "").lower()
    rules = {
        "construction": ["construction","builder","tiler","painter","drywall","строител","плиточ","маляр","quruv","kafel","gips"],
        "transport": ["driver","taxi","водител","такси","haydov"],
        "logistics": ["warehouse","logistic","supply","склад","логист","ombor"],
        "hospitality": ["hotel","cook","chef","restaurant","повар","отел","oshpaz"],
        "it": ["developer","engineer","devops","data","ai","frontend","backend","software","it "],
        "design": ["design","ux","ui","graphic","motion"],
        "marketing": ["marketing","smm","seo","performance","media buyer"],
        "sales": ["sales","business development","account manager","продаж"],
        "hr": ["recruit","talent","hr ","human resources"],
        "finance": ["account","finance","bank","ifrs","бухгалтер"],
        "medical": ["doctor","nurse","medical","clinical","врач","мед"],
        "education": ["teacher","trainer","lecturer","учител","преподав"],
        "legal": ["lawyer","legal","compliance","юрист"],
        "agriculture": ["farm","agri","harvest","ферм","сельск","qishloq"],
        "startup": ["founder","co-founder","startup"],
    }
    for domain, needles in rules.items():
        if any(n in j for n in needles):
            return domain
    return "general"

def _language_name(code: str) -> str:
    return {"uz":"Uzbek","ru":"Russian","en":"English"}.get(code, "English")

def build_prompt(data: dict, artifact: str = "cv") -> str:
    domain = detect_domain(data.get("job", ""))
    guide = DOMAIN_GUIDES[domain]
    lang = _language_name(data.get("lang", "en"))
    artifact_rules = {
        "cv": "Use sections: NAME, TARGET ROLE, PROFESSIONAL SUMMARY, CORE SKILLS, EXPERIENCE, EDUCATION, LANGUAGES, CERTIFICATIONS.",
        "cover_letter": "Write a concise cover letter with no invented company name. Use a neutral greeting and 3-5 short paragraphs.",
        "linkedin": "Write a LinkedIn headline plus an About section. Keep it keyword-rich, credible and concise.",
        "portfolio": "Write a professional portfolio/profile description focused on services, strengths and evidence from supplied facts.",
        "skills": "Return an ATS-oriented skills summary grouped into hard skills, tools/domain skills and soft skills. Do not invent tools.",
        "job_title": "Return 5 realistic ATS-friendly target job titles matching the supplied experience. No ranking and no inflated seniority.",
    }
    return f"""Create a {artifact} in {lang} for the candidate below.
Target role: {data.get('job','')}
Domain guidance: {guide}

Candidate facts:
Name: {data.get('full_name','')}
Location: {data.get('address','')}
Experience: {data.get('experience','')}
Education: {data.get('education','')}
Skills: {data.get('skills','')}
Languages: {data.get('languages','')}
Certifications: {data.get('certifications','')}
Candidate summary/raw notes: {data.get('summary','')}

Rules:
- Do not invent employers, dates, degrees, certifications, numbers, or achievements.
- If metrics are missing, strengthen wording without fabricating metrics.
- Make the CV ATS-friendly: plain headings, standard job-title keywords, no tables or decorative symbols.
- Use concise HR-grade language and domain-relevant hard skills.
- Separate facts from inferred wording; never claim unprovided experience.
- {artifact_rules.get(artifact, artifact_rules["cv"])}
- Keep the result ready to paste directly into Telegram or a job portal.
"""

async def generate_artifact(data: dict, artifact: str = "cv") -> str:
    if not _client:
        return fallback_cv(data) if artifact == "cv" else ""
    response = await _client.responses.create(
        model=MODEL,
        instructions="You are a senior international recruiter and ATS resume writer. Be precise and never fabricate candidate facts.",
        input=build_prompt(data, artifact),
    )
    return response.output_text.strip()

def fallback_cv(data: dict) -> str:
    labels = {
        "uz": ("PROFESSIONAL PROFIL", "ASOSIY KO'NIKMALAR", "TAJRIBA", "TA'LIM", "TILLAR", "SERTIFIKATLAR"),
        "ru": ("ПРОФЕССИОНАЛЬНЫЙ ПРОФИЛЬ", "КЛЮЧЕВЫЕ НАВЫКИ", "ОПЫТ", "ОБРАЗОВАНИЕ", "ЯЗЫКИ", "СЕРТИФИКАТЫ"),
        "en": ("PROFESSIONAL SUMMARY", "CORE SKILLS", "EXPERIENCE", "EDUCATION", "LANGUAGES", "CERTIFICATIONS"),
    }
    a,b,c,d,e,f = labels.get(data.get("lang","en"), labels["en"])
    parts = [
        str(data.get("full_name","")).upper(),
        data.get("job",""),
        "",
        a, data.get("summary",""),
        "", b, data.get("skills",""),
        "", c, data.get("experience",""),
        "", d, data.get("education",""),
        "", e, data.get("languages",""),
    ]
    if data.get("certifications"):
        parts += ["", f, data.get("certifications","")]
    return "\n".join(x for x in parts if x is not None).strip()
