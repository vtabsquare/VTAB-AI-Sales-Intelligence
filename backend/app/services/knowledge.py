"""Approval-filtered, local retrieval with deterministic chunk indexing."""
import re
from app.core.config import settings
from app.models.entities import KnowledgeDocument
from app.models.intelligence import KnowledgeChunk

def reindex(db, document):
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id==document.id).delete()
    text=document.content
    for position,start in enumerate(range(0,len(text),1200)):
        db.add(KnowledgeChunk(document_id=document.id,position=position,content=text[start:start+1400]))
    db.commit()

def retrieve(db, query, limit=6):
    terms=set(re.findall(r'\w{3,}',query.lower()))
    chunks=db.query(KnowledgeChunk,KnowledgeDocument).join(KnowledgeDocument,KnowledgeChunk.document_id==KnowledgeDocument.id).filter(KnowledgeDocument.approved.is_(True)).all()
    if not settings.demo_mode: chunks=[(c,d) for c,d in chunks if d.category!='DEMO']
    ranked=sorted([(len(terms & set(re.findall(r'\w{3,}',c.content.lower()))),c,d) for c,d in chunks],key=lambda x:(-x[0],x[1].position))
    return [{'document_id':d.id,'title':d.title,'category':d.category,'content':c.content,'retrieval_score':score,'retrieval_method':'LEXICAL','approved':True} for score,c,d in ranked[:limit] if score>0]
