from pydantic import BaseModel, ConfigDict, field_validator
from datetime import date
class OpportunityOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    closing_date:date|None=None
    id:str; title:str; source_name:str; source_url:str; country:str; description:str; qualification_score:int|None=None; qualification_status:str; business_fit:str|None=None; pipeline_status:str; matched_services:list[str]=[]; relevance_reason:str|None=None

    @field_validator('matched_services', mode='before')
    @classmethod
    def nullable_services(cls, value):
        return [] if value is None else value

class SendConfirmation(BaseModel):
    confirmed: bool = False

class DraftUpdate(BaseModel): subject:str|None=None; body_text:str|None=None
class ReplyIn(BaseModel): opportunity_id:str; subject:str='Re: Opportunity'; body:str
