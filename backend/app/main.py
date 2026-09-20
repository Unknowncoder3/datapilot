from fastapi import FastAPI
from app.api.routes import router
from app.db.database import Base, engine
from app.models.dataset import Dataset

app = FastAPI(title="DataPilot API", version="0.1.0")
Base.metadata.create_all(bind=engine)
app.include_router(router, prefix="/api/v1")
