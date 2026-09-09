from fastapi import FastAPI,Request,HTTPException, Query,Form
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from contextlib import asynccontextmanager
from sqlmodel import select,func,update
from database import SessionDep, create_db_and_tables,engine
from models import ModelsTams
from dotenv import load_dotenv
import os
import httpx
import asyncio
import json
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from sqlmodel.ext.asyncio.session import AsyncSession

load_dotenv()

TAMS_TOKEN=os.environ['TAMS_TOKEN']
TAMS_URL=os.environ['TAMS_URL']

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield
    
    await engine.dispose()
    
app=FastAPI(lifespan=lifespan)
jinja = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
# 2. Register fungsi sebagai filter Jinja2


@app.get('/',response_class=HTMLResponse)
async def home(request:Request,session:SessionDep):
    tenObjects=await firstTenModels(session=session)
  
    print(tenObjects)
    for i in tenObjects:
        print(i.showcaseImageUrls[0])
    
    return jinja.TemplateResponse(request,"index.html",context={"tenObjects":tenObjects})

@app.get("/api/projectname/",response_class=HTMLResponse)
async def get_modal(request:Request):
    return jinja.TemplateResponse(request,"pages/projectName.html")

@app.get("/modal",response_class=HTMLResponse)
async def get_modal(request:Request):
    return jinja.TemplateResponse(request,"create_modal.html")

@app.get("/addmodal",response_class=HTMLResponse)
async def get_modal(request:Request):
    return jinja.TemplateResponse(request,"manage_modal.html")

@app.post('/add-models/')
def add_models(modelstams:ModelsTams, session:SessionDep):
    return add_models_db(modelstams=modelstams,session=session)
    
@app.post("/api/favorite/",response_class=HTMLResponse)
async def api_favorite(request:Request,session:SessionDep,projectName:str=Form(...)):
    
    await is_liked(session=session,is_liked=True,projectName=projectName,)
    
    return jinja.TemplateResponse(request,"components/active_favorite_button.html",context={
            "object": {
                "projectName": projectName
            }
        })

@app.delete("/api/favorite/",response_class=HTMLResponse)
async def delete_api_favorite(request:Request,projectName:str,session:SessionDep):
    await is_liked(session=session,is_liked=False,projectName=projectName)
    
    return jinja.TemplateResponse(request,"components/inactive_favorite_button.html",context={
            "object": {
                "projectName": projectName
            }
        })

    
@app.get('/add-models-ui/',response_class=HTMLResponse)
async def add_models_ui(
    request:Request,
    modelId: Annotated[str, Query(max_length=50)], 
    session:SessionDep):
    
    modelId=str(modelId)
    
    
    model_exists=await check_models_db(modelId=modelId,session=session)
    
    
    if model_exists is None:
        try:
            model_data=await fetch_model_data(modelId=modelId)
            try:
                add_model=await add_models_db(modelstams=model_data['model'],session=session)
                return jinja.TemplateResponse(request,"toast.html",context={"message":"Model added sucessfully","status":200})

            except Exception as e:
                print(e)
                
        except Exception as e:
            print(e)
        
    else:
        print("Model exists")
        
        return jinja.TemplateResponse(request,"toast.html",context={"message":"Model exists","status":409})
   
        

@app.get('/api/stack-order-card/{projectName}',response_class=HTMLResponse)
async def stack_order_card(
    request:Request,
    projectName: str,
    targetId:str, 
    session:SessionDep):
    statement=select(ModelsTams.id,ModelsTams.projectName,ModelsTams.name,ModelsTams.stack_order).where(ModelsTams.projectName == projectName)
    result=(await session.exec(statement)).all()
    
    return jinja.TemplateResponse(
        request,
        "components/stack_order_popup.html",
        context={
            "list_names_by_projectName":result,
            "targetId":targetId
        }
    )
    
@app.get('/api/change-card/',response_class=HTMLResponse)
async def change_card(request:Request,modelId:str,session:SessionDep):
    
    result=await get_items_by_id(session=session,modelId=modelId)
    
    return jinja.TemplateResponse(
        request,
        "components/models_index.html",
        context={
            "object": result[0]
        }
        
    )
    
@app.get('/api/models/{modelId}',response_class=HTMLResponse)
async def page_of_a_model(request:Request,modelId:str,session:SessionDep):
    statement=select(ModelsTams).where(ModelsTams.id == modelId)
    result=await session.scalar(statement)
    projectName=result.projectName
    print("projectname",projectName)
    statement2=select(ModelsTams.name,ModelsTams.id,ModelsTams.stack_order).where(ModelsTams.projectName == projectName).order_by(ModelsTams.stack_order)
    version_orderby_stackorder=(await session.exec(statement2)).all()
    
    return jinja.TemplateResponse(
        request,
        "pages/projectName.html",
        context={
            "ModelsTams":result,
            "version_orderby_stackorder":version_orderby_stackorder,
            "targetId":modelId
        }
        
    )
    
#----------------- TAMS FUNCTION------------------------
async def fetch_model_data(modelId):
    url=f"{TAMS_URL}/v1/models/{modelId}"
    headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {TAMS_TOKEN}'
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url=url,headers=headers)
        return response.json()



#----------------- DB FUNCTION------------------------
async def add_models_db(modelstams:dict, session:AsyncSession):
    max_stack_order=await select(func.max(ModelsTams.stack_order)).where(ModelsTams.projectName == modelstams['projectName']).scalar_subquery()
    
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

async def firstTenModels(session:AsyncSession):
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

#----------------- HELPER FUNCTION------------------------
# 1. Bikin fungsi helper format angka
def format_k(value: int | float) -> str:
    try:
        val = float(value)
        if val >= 1_000_000:
            formatted = f"{val / 1_000_000:.1f}M"
        elif val >= 1_000:
            formatted = f"{val / 1_000:.1f}k"
        else:
            return str(value)
        
        # Hapus desimal .0 kalau angkanya bulat (misal 15.0k -> 15k)
        return formatted.replace(".0", "")
    except (ValueError, TypeError):
        return str(value)

jinja.env.filters["format_k"] = format_k
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=8000,
        host="127.0.0.1",
        reload=True
    )