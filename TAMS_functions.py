from dotenv import load_dotenv
import os
import httpx

load_dotenv()

TAMS_TOKEN=os.environ['TAMS_TOKEN']
TAMS_URL=os.environ['TAMS_URL']
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