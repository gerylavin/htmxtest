from fastapi import FastAPI,Request,HTTPException, Query,Form
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from contextlib import asynccontextmanager

from database import SessionDep, create_db_and_tables,engine
from models import ModelsTams
from TAMS_functions import fetch_model_data
from db_functions import (
    stack_order_popup_db,
    page_of_a_model_db,
    add_models_db,
    check_models_db,
    firstLoadModels,
    is_liked,
    get_items_by_id
)
import json
from fastapi.staticfiles import StaticFiles
from typing import Annotated



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
    tenObjects=await firstLoadModels(session=session)
    
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
async def stack_order_popup(
    request:Request,
    projectName: str,
    targetId:str, 
    session:SessionDep):
    
    result=await stack_order_popup_db(session=session,projectName=projectName)
    
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
    full_data_model,version_orderby_stackorder = await page_of_a_model_db(session=session,modelId=modelId)
    
    return jinja.TemplateResponse(
        request,
        "pages/projectName.html",
        context={
            "ModelsTams":full_data_model,
            "version_orderby_stackorder":version_orderby_stackorder,
            "targetId":modelId
        }
        
    )
    


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