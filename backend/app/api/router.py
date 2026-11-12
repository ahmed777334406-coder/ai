from fastapi import APIRouter
from app.api.routes import auth, listings, ai, matches, claims, notifications, admin

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(listings.router)
api_router.include_router(ai.router)
api_router.include_router(matches.router)
api_router.include_router(claims.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
