import enum, uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Date, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.db import Base

def uid(): return str(uuid.uuid4())
class Pipeline(str,enum.Enum):
    DISCOVERED='DISCOVERED'; UNDER_REVIEW='UNDER_REVIEW'; QUALIFIED='QUALIFIED'; REJECTED='REJECTED'; RESEARCHING='RESEARCHING'; CONTACT_IDENTIFIED='CONTACT_IDENTIFIED'; OUTREACH_READY='OUTREACH_READY'; CONTACTED='CONTACTED'; RESPONDED='RESPONDED'; ENGAGED='ENGAGED'; WON='WON'; LOST='LOST'; CLOSED='CLOSED'
class Company(Base):
    __tablename__='companies'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); name:Mapped[str]=mapped_column(String(255),index=True); website:Mapped[str|None]=mapped_column(String(255)); country:Mapped[str|None]=mapped_column(String(255)); description:Mapped[str|None]=mapped_column(Text)
class Opportunity(Base):
    __tablename__='opportunities'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); company_id:Mapped[str|None]=mapped_column(ForeignKey('companies.id')); title:Mapped[str]=mapped_column(String(255),index=True); reference_number:Mapped[str|None]=mapped_column(String(255),index=True); source_name:Mapped[str]=mapped_column(String(255)); source_url:Mapped[str]=mapped_column(String(2048),unique=True); country:Mapped[str]=mapped_column(String(255),index=True); published_date:Mapped[date|None]=mapped_column(Date); closing_date:Mapped[date|None]=mapped_column(Date); description:Mapped[str]=mapped_column(Text); qualification_score:Mapped[int|None]=mapped_column(Integer); qualification_status:Mapped[str]=mapped_column(String(255),default='PENDING'); business_fit:Mapped[str|None]=mapped_column(String(255)); pipeline_status:Mapped[str]=mapped_column(String(255),default=Pipeline.DISCOVERED.value,index=True); matched_services:Mapped[list]=mapped_column(JSON,default=list); relevance_reason:Mapped[str|None]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Contact(Base):
    __tablename__='contacts'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); company_id:Mapped[str]=mapped_column(ForeignKey('companies.id')); full_name:Mapped[str]=mapped_column(String(255)); title:Mapped[str]=mapped_column(String(255)); email:Mapped[str|None]=mapped_column(String(255),index=True); email_verification_status:Mapped[str]=mapped_column(String(255),default='UNVERIFIED'); do_not_contact:Mapped[bool]=mapped_column(Boolean,default=False)
class OutreachDraft(Base):
    __tablename__='outreach_drafts'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); opportunity_id:Mapped[str]=mapped_column(ForeignKey('opportunities.id')); contact_id:Mapped[str|None]=mapped_column(ForeignKey('contacts.id')); subject:Mapped[str]=mapped_column(String(255)); body_text:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(255),default='WAITING_APPROVAL',index=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class AgentRun(Base):
    __tablename__='agent_runs'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); agent_name:Mapped[str]=mapped_column(String(255),index=True); input_json:Mapped[dict]=mapped_column(JSON); output_json:Mapped[dict]=mapped_column(JSON); status:Mapped[str]=mapped_column(String(255)); duration_ms:Mapped[int]=mapped_column(Integer,default=0); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Suppression(Base):
    __tablename__='suppression_list'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); email:Mapped[str]=mapped_column(String(255),unique=True,index=True); reason:Mapped[str]=mapped_column(String(255)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Communication(Base):
    __tablename__='communications'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); opportunity_id:Mapped[str]=mapped_column(ForeignKey('opportunities.id')); direction:Mapped[str]=mapped_column(String(255)); subject:Mapped[str]=mapped_column(String(255)); body:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(255)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class KnowledgeDocument(Base):
    __tablename__='knowledge_documents'; id:Mapped[str]=mapped_column(String(255),primary_key=True,default=uid); title:Mapped[str]=mapped_column(String(255)); category:Mapped[str]=mapped_column(String(255)); content:Mapped[str]=mapped_column(Text); approved:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
