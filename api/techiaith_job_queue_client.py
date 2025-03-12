import json
import httpx

from dataclasses import dataclass, asdict

QUEUE_URL = "localhost:6006/"  

@dataclass
class Job:
    stt_id: str
    consumer_id: str
    callback_url: str
    priority: float


async def addJob(job):
    await sendHttpxRequest(QUEUE_URL + "AddJob", job)

async def cancelJob(job):
    await sendHttpxRequest(QUEUE_URL + "CancelJob", job)

async def sendHttpxRequest(url, job):
    json_data = json.dumps(asdict(job))
    #print (json_data)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, 
                headers={
                    "accept": "text/plain",
                    "Content-Type": "application/json"
                },
                data=json_data
        )
    