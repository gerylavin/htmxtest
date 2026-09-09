from sqlmodel import select,func,update
from sqlmodel.ext.asyncio.session import AsyncSession
from models import ModelsTams

#----------------- DB FUNCTION------------------------
async def stack_order_popup_db(session:AsyncSession,projectName:str):
    statement=select(ModelsTams.id,ModelsTams.projectName,ModelsTams.name,ModelsTams.stack_order).where(ModelsTams.projectName == projectName)
    result=(await session.exec(statement)).all()
    
    return result

async def page_of_a_model_db(session:AsyncSession,modelId:str):
    statement=select(ModelsTams).where(ModelsTams.id == modelId)
    result1=await session.scalar(statement)
    
    projectName=result1.projectName
    
    statement2=select(ModelsTams.name,ModelsTams.id,ModelsTams.stack_order).where(ModelsTams.projectName == projectName).order_by(ModelsTams.stack_order)
    result2=(await session.exec(statement2)).all()
    
    return result1,result2
    
async def add_models_db(modelstams:dict, session:AsyncSession):
    max_stack_order=select(func.max(ModelsTams.stack_order)).where(ModelsTams.projectName == modelstams['projectName']).scalar_subquery()
    
    query_like_by_projectName=select(func.max(ModelsTams.is_liked).over(partition_by=ModelsTams.projectName)).where(ModelsTams.projectName == modelstams['projectName'])
    list_like_by_projectName= (await session.exec(query_like_by_projectName)).all()
    if list_like_by_projectName != []:
        like_by_projectName = list_like_by_projectName[0]
    else:
        like_by_projectName = False
    
    new_model=ModelsTams(stack_order=func.coalesce(max_stack_order, 0)+1,is_liked=like_by_projectName,**modelstams)
    
    try:
        await session.add(new_model)
        
    except Exception as e:
        print(e)
    else:
        print("Model added sucessfully")
        
    await session.commit()
    await session.refresh(new_model)
    
    return new_model

async def check_models_db(modelId:str, session:AsyncSession):
    
    model=await session.get(ModelsTams,modelId)
    
    return model

async def firstLoadModels(session:AsyncSession):
    statement=select(ModelsTams.id,ModelsTams.projectName,ModelsTams.name,ModelsTams.showcaseImageUrls,ModelsTams.is_liked).distinct().where(ModelsTams.stack_order == 1).limit(20)
    result=(await session.exec(statement)).all()
    
    return result

async def is_liked(session:AsyncSession,is_liked:bool,projectName:str):   
    statement=update(ModelsTams).where(ModelsTams.projectName == projectName).values(is_liked=is_liked)
    result= await session.exec(statement)
    await session.commit()

    
    return result

async def get_items_by_id(session:AsyncSession,modelId:str):
    statement=select(ModelsTams.id,ModelsTams.projectName,ModelsTams.name,ModelsTams.showcaseImageUrls,ModelsTams.is_liked).where(ModelsTams.id == modelId)
    result=(await session.exec(statement)).all()
    
    return result