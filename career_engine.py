"""CV_MK Free Career Engine — fully local, no paid API."""
from typing import Dict

DOMAIN_SKILLS: Dict[str, list[str]] = {
    "construction": ["Quality workmanship", "Safety awareness", "Technical drawings", "Site coordination"],
    "transport": ["Safe driving", "Route planning", "Punctuality", "Vehicle care"],
    "logistics": ["Warehouse operations", "Inventory handling", "Order accuracy", "Safety procedures"],
    "hospitality": ["Customer service", "Hygiene standards", "Teamwork", "Service quality"],
    "it": ["Problem solving", "Technical documentation", "Testing", "Version control"],
    "sales": ["Customer communication", "Lead handling", "Negotiation", "Follow-up"],
    "hr": ["Candidate screening", "Communication", "Coordination", "Documentation"],
    "general": ["Reliability", "Teamwork", "Communication", "Time management"],
}

def detect_domain(job: str) -> str:
    j=(job or "").lower()
    rules={
        "construction":["construction","builder","tiler","painter","drywall","quruv","kafel","gips","строител","плиточ","маляр"],
        "transport":["driver","taxi","haydov","водител","такси"],
        "logistics":["warehouse","logistic","supply","ombor","склад","логист"],
        "hospitality":["hotel","cook","chef","restaurant","oshpaz","повар","отел"],
        "it":["developer","engineer","devops","frontend","backend","software","data","ai"],
        "sales":["sales","account manager","business development","продаж"],
        "hr":["recruit","talent","human resources"],
    }
    for domain,words in rules.items():
        if any(w in j for w in words):
            return domain
    return "general"

def fallback_cv(data: dict) -> str:
    lang=data.get("lang","en")
    labels={
        "uz":("PROFESSIONAL PROFIL","ASOSIY KO'NIKMALAR","TAJRIBA","TA'LIM","TILLAR","SERTIFIKATLAR"),
        "ru":("ПРОФЕССИОНАЛЬНЫЙ ПРОФИЛЬ","КЛЮЧЕВЫЕ НАВЫКИ","ОПЫТ","ОБРАЗОВАНИЕ","ЯЗЫКИ","СЕРТИФИКАТЫ"),
        "en":("PROFESSIONAL SUMMARY","CORE SKILLS","EXPERIENCE","EDUCATION","LANGUAGES","CERTIFICATIONS"),
    }
    a,b,c,d,e,f=labels.get(lang,labels["en"])
    domain=detect_domain(data.get("job",""))
    entered=[x.strip() for x in str(data.get("skills","")).replace("\n",",").split(",") if x.strip()]
    defaults=DOMAIN_SKILLS.get(domain,DOMAIN_SKILLS["general"])
    skills=entered or defaults
    parts=[
        str(data.get("full_name","")).upper(),
        str(data.get("job","")),
        "",
        a, str(data.get("summary","")),
        "", b, " • ".join(skills),
        "", c, str(data.get("experience","")),
        "", d, str(data.get("education","")),
        "", e, str(data.get("languages","")),
    ]
    if data.get("certifications"):
        parts += ["",f,str(data.get("certifications",""))]
    return "\n".join(parts).strip()
