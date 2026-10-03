from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.entities import *
SERVICES=['Databricks','Microsoft Fabric','Power BI','Data Engineering','Data Migration','SQL Server Modernization','Cloud Migration','AI Applications','AI Agents','Automation','Power Platform','Dynamics 365','Custom Application Development','IT Consulting','Offshore Development']
KEYS={'Databricks':['databricks','lakehouse','spark'],'Microsoft Fabric':['fabric','onelake'],'Power BI':['power bi','business intelligence','dashboard'],'Data Engineering':['data engineering','etl','data platform'],'AI Applications':['generative ai',' ai ','automation','agent'],'Dynamics 365':['dynamics 365'],'Power Platform':['power platform','power automate'],'Custom Application Development':['application development','software development','web application']}
def log(db,name,inp,out,status='SUCCESS'):
    r=AgentRun(agent_name=name,input_json=inp,output_json=out,status=status); db.add(r); db.commit(); return r
def discover(db:Session):
    samples=[
      ('Example Ireland Analytics Ltd','Power BI and Microsoft Fabric modernization partner','Ireland','https://demo.vtabsquare.local/opportunities/ireland-fabric','Seeking an external implementation partner for Power BI, Microsoft Fabric and data engineering modernization.'),
      ('Northstar Data Council','Databricks lakehouse migration services','United Kingdom','https://demo.vtabsquare.local/opportunities/uk-databricks','Public procurement notice for Databricks migration, Spark modernization and managed data engineering.'),
      ('Harbor Digital Authority','AI automation and application development RFP','Australia','https://demo.vtabsquare.local/opportunities/au-ai','RFP for secure AI workflow automation and custom web application development.')]
    made=[]
    for company,title,country,url,desc in samples:
        existing=db.query(Opportunity).filter(Opportunity.source_url==url).first()
        if existing: made.append(existing); continue
        c=db.query(Company).filter(Company.name==company).first() or Company(name=company,country=country,website='https://example.invalid')
        db.add(c); db.flush(); o=Opportunity(company_id=c.id,title=title,source_name='DEMO Public Procurement Feed',source_url=url,country=country,published_date=date.today(),closing_date=date.today()+timedelta(days=30),description=desc); db.add(o); db.flush(); made.append(o)
    db.commit(); log(db,'Opportunity Discovery Agent',{'mode':'demo'},{'discovered':len(made)})
    return made
def qualify(db,o):
    text=((o.title or '')+' '+(o.description or '')).lower(); matches=[s for s,ks in KEYS.items() if any(k in text for k in ks)]
    tech=min(25,10+5*len(matches)); service=min(20,8+4*len(matches)); commercial=15; geo=10; buyer=8; fresh=10; strategic=8; score=tech+service+commercial+geo+buyer+fresh+strategic
    if o.closing_date and o.closing_date < date.today(): score=0; status='REJECTED'; reason='Deadline has passed.'
    elif not matches: score=0; status='REJECTED'; reason='No supported VTAB capability match.'
    else: status='QUALIFIED' if score>=65 else 'UNDER_REVIEW'; reason=f"Relevant because the requirement maps to VTAB capabilities: {', '.join(matches)}."
    o.qualification_score=score; o.qualification_status=status; o.business_fit='HIGH' if score>=80 else ('MEDIUM' if score>=65 else 'LOW'); o.pipeline_status=status; o.matched_services=matches; o.relevance_reason=reason; db.commit(); log(db,'Qualification Agent',{'opportunity_id':o.id},{'score':score,'matched_services':matches,'status':status}); return o
def research(db,o):
    from app.services.source_evidence import fetch_evidence
    company=db.get(Company,o.company_id)
    if not company: raise ValueError('Opportunity has no associated company. Review source evidence first.')
    evidence=fetch_evidence(o.source_url)
    summary=evidence['text'][:2000] or o.description or 'No source description is available.'
    out={'company_name':company.name,'country':company.country,'company_summary':summary,
         'known_facts':['Company identity is taken from the opportunity record and requires human review.'],
         'inferences':[],'sources':[o.source_url], 'evidence_status':evidence['status'],
         'message':'Source evidence fetched.' if evidence['status']=='FETCHED' else 'External evidence unavailable; stored opportunity context returned.'}
    o.pipeline_status='RESEARCHING';db.commit();log(db,'Company Research Agent',{'opportunity_id':o.id},out);return out

def find_contact(db,o):
    from app.services.source_evidence import fetch_evidence
    company=db.get(Company,o.company_id)
    if not company: raise ValueError('Opportunity has no associated company. Review source evidence first.')
    contact=db.query(Contact).filter(Contact.company_id==company.id).first()
    evidence={'emails':[],'status':'EXISTING_CONTACT'}
    if not contact or not contact.email:
        evidence=fetch_evidence(o.source_url)
        # Multiple published mailboxes require human selection, rather than guessing a recipient.
        email=evidence['emails'][0] if len(evidence['emails'])==1 else None
        if not contact:
            contact=Contact(company_id=company.id,full_name='Procurement Team',title='IT Procurement',email=email,email_verification_status='UNVERIFIED');db.add(contact)
        elif email:
            contact.email=email;contact.email_verification_status='UNVERIFIED'
    o.pipeline_status='CONTACT_IDENTIFIED';db.commit()
    log(db,'Contact Research Agent',{'opportunity_id':o.id},{'contact_id':contact.id,'email':contact.email,'source_url':o.source_url,'evidence_status':evidence['status'],'published_candidates':evidence['emails'],'rule':'Published evidence only; human verification is still required'})
    return contact

def draft(db,o):
    c=db.get(Company,o.company_id); contact=find_contact(db,o); services=', '.join(o.matched_services or [])
    subject=f'{c.name} — support for {o.title}'
    body=f"Hello {contact.full_name},\n\nWe identified your published requirement: {o.title}. Based on the requirement, VTAB Square may be able to support the work through {services}.\n\nWe would be glad to understand the procurement process and discuss where our engineering team could contribute.\n\nRegards,\nBusiness Development Team\nVTAB Square Private Limited"
    d=OutreachDraft(opportunity_id=o.id,contact_id=contact.id,subject=subject,body_text=body,status='WAITING_APPROVAL'); db.add(d); o.pipeline_status='OUTREACH_READY'; db.commit(); log(db,'Outreach Agent',{'opportunity_id':o.id},{'draft_id':d.id,'status':d.status}); return d
def send(db, d):
    """
    Final outbound delivery service.

    Safety checks are intentionally repeated here even though the API route
    also validates them. This prevents another caller from bypassing the
    human-control rules by calling the service directly.
    """
    if d.status != 'APPROVED':
        raise ValueError('Approval required before send')

    contact = db.get(Contact, d.contact_id) if d.contact_id else None

    if not contact:
        raise ValueError('Recipient contact is required before send')

    if contact.do_not_contact:
        raise ValueError('Recipient is suppressed')

    if not contact.email:
        raise ValueError('Recipient email is required before send')

    from app.core.config import settings

    verification_status = (
        contact.email_verification_status or ''
    ).strip().upper()

    allowed_verification_statuses = {'VERIFIED', 'HUMAN_VERIFIED'}

    if (
        settings.app_env.strip().lower()
        in {'development', 'local', 'test'} and settings.demo_mode
    ):
        allowed_verification_statuses.add('TEST_VERIFIED')

    if verification_status not in allowed_verification_statuses:
        raise ValueError(
            'Recipient email must be verified before send'
        )

    from sqlalchemy import func
    if db.query(Suppression).filter(func.lower(Suppression.email)==contact.email.lower()).first():
        raise ValueError('Recipient is on the suppression list')
    from app.services.email_sender import (
        EmailDeliveryError,
        send_email,
    )

    from sqlalchemy import update
    claimed = db.execute(update(OutreachDraft).where(OutreachDraft.id==d.id, OutreachDraft.status=='APPROVED').values(status='SENDING'))
    if claimed.rowcount != 1:
        db.rollback()
        raise ValueError('Draft is already being sent or is no longer approved')
    db.commit()
    try:
        delivery = send_email(
            recipient_email=contact.email,
            subject=d.subject,
            body_text=d.body_text,
        )
    except EmailDeliveryError as exc:
        d.status = 'SEND_FAILED'
        db.commit()
        log(
            db,
            'Outbound Email Agent',
            {
                'draft_id': d.id,
                'recipient': contact.email,
            },
            {
                'status': 'FAILED',
                'reason': str(exc),
            },
            status='FAILED',
        )
        raise ValueError(str(exc)) from exc

    delivery_status = delivery['status']

    d.status = 'SENT'

    db.add(
        Communication(
            opportunity_id=d.opportunity_id,
            direction='OUTBOUND',
            subject=d.subject,
            body=d.body_text,
            status=delivery_status,
        )
    )

    o = db.get(Opportunity, d.opportunity_id)
    o.pipeline_status = 'CONTACTED'

    db.commit()

    log(
        db,
        'Outbound Email Agent',
        {
            'draft_id': d.id,
            'recipient': contact.email,
        },
        {
            'status': delivery_status,
            'provider': delivery['provider'],
            'demo_mode': delivery['demo_mode'],
        },
    )

    return {
        **delivery,
        'draft_id': d.id,
        'message': (
            'Demo mode: outreach was simulated; no real email was sent.'
            if delivery['demo_mode']
            else (
                'Microsoft Graph accepted the outbound message. '
                'The request was accepted for processing.'
            )
        ),
    }
