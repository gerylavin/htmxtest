from sqlmodel import Field, SQLModel, Column, JSON
from typing import List
from datetime import datetime

class ModelsTams(SQLModel, table=True):
    
    #By TAMS:
    id: str = Field(primary_key=True)
    projectName:str = Field(index=True)
    name: str 
    baseModel: str = Field(index=True)
    modelType:str = Field(index=True)
    description:str | None =Field(default=None)
    triggerWords:str | None =Field(default=None)
    showcaseImageUrls: List[str] = Field(default=[],sa_column=Column(JSON))
    
    #By myself:
    stack_order:int | None = Field(default=None)
    is_liked:bool | None = Field(default=False)
    total_used :int | None = Field(default=0)
    added_at: datetime = Field(default_factory=datetime.now)
    
    
