from datetime import datetime
from app.models.entities import Opportunity, Communication
from app.models.sales_agent import ClientCasebook, CasebookEvent


def case_for(db, opportunity_id, create=False):
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity or not opportunity.company_id:
        return None
    case = db.query(ClientCasebook).filter_by(company_id=opportunity.company_id).first()
    if not case and create:
        case = ClientCasebook(company_id=opportunity.company_id)
        db.add(case)
        db.flush()
        # Include earlier outbound attempts when the first response opens a case.
        ids = [o.id for o in db.query(Opportunity).filter_by(company_id=case.company_id).all()]
        for communication in db.query(Communication).filter(Communication.opportunity_id.in_(ids)).all():
            add_event(db, case, communication.opportunity_id, 'communication:' + communication.id,
                      communication.direction, communication.subject, communication.body,
                      {'delivery_status': communication.status}, communication.created_at)
    return case


def add_event(db, case, opportunity_id, key, kind, subject='', body='', details=None, when=None):
    if db.query(CasebookEvent).filter_by(event_key=key).first():
        return
    db.add(CasebookEvent(casebook_id=case.id, opportunity_id=opportunity_id,
                        event_key=key, kind=kind, subject=subject[:1000], body=body,
                        details=details or {}, created_at=when or datetime.utcnow()))
    case.updated_at = datetime.utcnow()


def record_inbound(db, response):
    case = case_for(db, response.opportunity_id, create=True)
    if not case:
        return
    when = response.received_at
    if when:
        from datetime import timezone
        when = when.astimezone(timezone.utc).replace(tzinfo=None) if when.tzinfo else when
    add_event(db, case, response.opportunity_id, 'inbound:' + response.id, 'CLIENT_REPLY',
              response.subject, response.body_text,
              {'sender': response.sender_email, 'classification': response.classification}, when)


def record_action(db, opportunity_id, key, kind, subject='', body='', details=None):
    case = case_for(db, opportunity_id)
    if case:
        add_event(db, case, opportunity_id, key, kind, subject, body, details)
