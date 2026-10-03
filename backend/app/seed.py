"""Explicit demo seed command: never run against live mode."""
from app.core.config import settings
from app.models.db import SessionLocal
from app.models.entities import KnowledgeDocument
from app.services.knowledge import reindex

def seed_demo(db):
    if not settings.demo_mode:
        raise ValueError('Demo seeding requires DEMO_MODE=true.')
    from app.services.global_discovery import seed_defaults
    seed_defaults(db)
    doc=db.query(KnowledgeDocument).filter(KnowledgeDocument.title=='DEMO — VTAB capability fixture').first()
    if not doc:
        doc=KnowledgeDocument(title='DEMO — VTAB capability fixture',category='DEMO',approved=True,content='Synthetic demonstration capability catalog: Power BI, Microsoft Fabric, Databricks, Data Engineering, AI Applications, Dynamics 365, Power Platform, Custom Application Development. No customer references or certifications are asserted. Replace with reviewed company evidence before live qualification.')
        db.add(doc);db.commit();reindex(db,doc)
    from app.services.engine import discover
    return discover(db)

if __name__=='__main__':
    with SessionLocal() as db:
        print(f'Seeded {len(seed_demo(db))} labeled demo opportunities.')
