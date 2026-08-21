from fastapi import APIRouter
from .endpoints import auth, oauth, users, profiles, resume, interview, admin, hr, student
from .endpoints import voice as voice
from .endpoints import hiring_workflow
from .endpoints import memory
from .endpoints import health

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(resume.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(interview.router, prefix="/interview", tags=["interview"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(hr.router, prefix="/hr", tags=["hr"])
api_router.include_router(student.router, prefix="/student", tags=["student"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(hiring_workflow.router, prefix="/hiring", tags=["hiring-workflow"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
