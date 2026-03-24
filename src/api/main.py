from env import load_application_dotenv

load_application_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.auth import router as auth_router
from api.routes.runs import router as runs_router

app = FastAPI(
    title="Cerevyn Agent API",
    version="0.1.0",
    description="Web API for the Cerevyn autonomous meeting assistant.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router)
app.include_router(auth_router)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
