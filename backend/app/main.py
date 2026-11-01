from fastapi import FastAPI

from app.api.routes import router
from app.api.analytics_routes import router as analytics_router
from app.api.business_intelligence_routes import router as business_intelligence_router
from app.db.database import Base, engine
from app.models.dataset import Dataset

app = FastAPI(title="DataPilot API", version="0.2.0")

Base.metadata.create_all(bind=engine)

app.include_router(router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1/analytics")
app.include_router(business_intelligence_router, prefix="/api/v1/analytics")
