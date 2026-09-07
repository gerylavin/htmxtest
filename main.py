from fastapi import FastAPI,Request,HTTPException, Query
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from contextlib import asynccontextmanager
from sqlmodel import Session,select,func
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

@app.post('/add-models')
def add_models(modelstams:ModelsTams, session:SessionDep):
    return add_models_db(modelstams=modelstams,session=session)
    
# @app.get('/add-models-ui/')
# async def add_models_ui(
#     request:Request, 
#     session:SessionDep):
#     modelId_dict=await request.json()
#     modelId=str(modelId_dict['modelId'])
    
    
#     model_exists=check_models_db(modelId=modelId,session=session)
#     print(model_exists,type(model_exists))
    
#     if model_exists is None:
#         try:
#             model_data=await fetch_model_data(modelId=modelId)
            
#             try:
#                 return add_models_db(modelstams=model_data['model'],session=session)
#             except Exception as e:
#                 print(e)
                
#         except Exception as e:
#             print(e)
        
#     else:
#         raise HTTPException(
#             status_code=409, 
#             detail="Model sudah ada di database."
#         )
    
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
                return jinja.TemplateResponse(request,"toast.html")
            except Exception as e:
                print(e)
                
        except Exception as e:
            print(e)
        
    else:
        print("Model exists")
        raise HTTPException(
            status_code=409, 
            detail="Model exists"
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
    new_model=ModelsTams(stack_order=func.coalesce(max_stack_order, 0)+1,**modelstams)
    
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
    statement=select(ModelsTams.projectName,ModelsTams.name,ModelsTams.showcaseImageUrls).distinct().where(ModelsTams.stack_order == 1).limit(10)
    result=session.exec(statement).all()
    
    return result

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=8000,
        host="127.0.0.1",
        reload=True
    )