from fastapi import FastAPI,Request,HTTPException, Query,Form
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from contextlib import asynccontextmanager
from sqlmodel import Session,select,func,update
from database import SessionDep, create_db_and_tables
from models import ModelsTams
from dotenv import load_dotenv
import os
import httpx
import asyncio
import json
from fastapi.staticfiles import StaticFiles
from typing import Annotated

load_dotenv()

TAMS_TOKEN=os.environ['TAMS_TOKEN']
TAMS_URL=os.environ['TAMS_URL']

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
    
app=FastAPI(lifespan=lifespan)
jinja = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get('/',response_class=HTMLResponse)
async def home(request:Request,session:SessionDep):
    tenObjects=firstTenModels(session=session)
  
    print(tenObjects)
    for i in tenObjects:
        print(i.showcaseImageUrls[0])
    
    return jinja.TemplateResponse(request,"index.html",context={"tenObjects":tenObjects})

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
    
    is_liked(session=session,is_liked=True,projectName=projectName,)
    
    return jinja.TemplateResponse(request,"components/active_favorite_button.html",context={
            "object": {
                "projectName": projectName
            }
        })

@app.delete("/api/favorite/",response_class=HTMLResponse)
async def delete_api_favorite(request:Request,projectName:str,session:SessionDep):
    is_liked(session=session,is_liked=False,projectName=projectName)
    
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
    
    
    model_exists=check_models_db(modelId=modelId,session=session)
    
    
    if model_exists is None:
        try:
            model_data=await fetch_model_data(modelId=modelId)
            try:
                add_model=add_models_db(modelstams=model_data['model'],session=session)
                return jinja.TemplateResponse(request,"toast.html",context={"message":"Model added sucessfully","status":200})
                #return "<div>Data model berhasil ditambah!</div>"
            except Exception as e:
                print(e)
                
        except Exception as e:
            print(e)
        
    else:
        print("Model exists")
        return jinja.TemplateResponse(request,"toast.html",context={"message":"Model exists","status":409})
        # raise HTTPException(
        #     status_code=409, 
        #     detail="Model exists"
        # )
        

@app.get('/api/stack-order-card/{projectName}',response_class=HTMLResponse)
async def stack_order_card(
    request:Request,
    projectName: str,
    targetId:str, 
    session:SessionDep):
    statement=select(ModelsTams.id,ModelsTams.projectName,ModelsTams.name,ModelsTams.stack_order).where(ModelsTams.projectName == projectName)
    result=session.exec(statement).all()
    
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
    
    result=get_items_by_id(session=session,modelId=modelId)
    
    return jinja.TemplateResponse(
        request,
        "components/changed_card.html",
        context={
            "object": result[0]
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
def add_models_db(modelstams:dict, session:Session):
    max_stack_order=select(func.max(ModelsTams.stack_order)).where(ModelsTams.projectName == modelstams['projectName']).scalar_subquery()
    
    query_like_by_projectName=select(func.max(ModelsTams.is_liked).over(partition_by=ModelsTams.projectName)).where(ModelsTams.projectName == modelstams['projectName'])
    list_like_by_projectName=session.exec(query_like_by_projectName).all()
    if list_like_by_projectName != []:
        like_by_projectName = list_like_by_projectName[0]
    else:
        like_by_projectName = False
    
    new_model=ModelsTams(stack_order=func.coalesce(max_stack_order, 0)+1,is_liked=like_by_projectName,**modelstams)
    
    try:
        session.add(new_model)
        
    except Exception as e:
        print(e)
    else:
        print("Model added sucessfully")
        
    session.commit()
    session.refresh(new_model)
    
    return new_model

def check_models_db(modelId:str, session:Session):
    
    model=session.get(ModelsTams,modelId)
    
    return model

def firstTenModels(session:Session):
    statement=select(ModelsTams.id,ModelsTams.projectName,ModelsTams.name,ModelsTams.showcaseImageUrls,ModelsTams.is_liked).distinct().where(ModelsTams.stack_order == 1).limit(20)
    result=session.exec(statement).all()
    
    return result

def is_liked(session:Session,is_liked:bool,projectName:str):   
    statement=update(ModelsTams).where(ModelsTams.projectName == projectName).values(is_liked=is_liked)
    result=session.exec(statement)
    session.commit()

    
    return result

def get_items_by_id(session:Session,modelId:str):
    statement=select(ModelsTams.id,ModelsTams.projectName,ModelsTams.name,ModelsTams.showcaseImageUrls,ModelsTams.is_liked).where(ModelsTams.id == modelId)
    result=session.exec(statement).all()
    
    return result

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=8000,
        host="127.0.0.1",
        reload=True
    )