import asyncio

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ServicePulse test target")


class Scenario(BaseModel):
    status: int = Field(default=200, ge=200, le=599)
    delay: float = Field(default=0, ge=0, le=180)
    body: str = Field(default="ServicePulse ready", max_length=2000)
    redirect: str | None = Field(default=None, max_length=2048)


scenarios: dict[str, Scenario] = {}


@app.put("/control/{name}")
async def configure(name: str, scenario: Scenario):
    scenarios[name] = scenario
    return scenario


@app.get("/target/{name}")
async def target(name: str):
    scenario = scenarios.get(name, Scenario()).model_copy()
    await asyncio.sleep(scenario.delay)
    if scenario.redirect:
        return RedirectResponse(scenario.redirect, status_code=302)
    return PlainTextResponse(scenario.body, status_code=scenario.status)
