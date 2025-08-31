from fastapi import FastAPI
from pydantic import BaseModel
from workers.worker import run_extraction

app = FastAPI()


class ExtractRequest(BaseModel):
    prompt: str
    url: str


@app.post("/extract")
async def extract(req: ExtractRequest):
    result = await run_extraction(req.prompt, req.url)
    return result
