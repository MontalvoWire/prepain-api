from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Query, Path
from pydantic import BaseModel, EmailStr

app = FastAPI(title="PrepaIn API", version="1.0", description="Mock API")

DUMMY_API_KEY = "test-api-key"
DUMMY_TOKEN = "dummy-token-123"

class Pagination(BaseModel):
    total: int
    pages: int
    page: int
    limit: int

class Lesson(BaseModel):
    name: str
    description: str
    type: str
    subtype: str

class Module(BaseModel):
    id: str
    name: str
    description: str
    lessons: List[Lesson]

class Course(BaseModel):
    id: str
    name: str
    modules: List[Module]

class Section(BaseModel):
    name: str
    description: Optional[str]=None
    courses: List[Course]

class LearningPath(BaseModel):
    id: str
    name: str
    image_url: Optional[str]=None
    conditioned_courses: bool
    conditioned_sections: bool
    min_progress: int
    certificate_delivery: str
    condition_delivery: str
    welcome_message: str
    is_gamified: bool
    status: str
    start_date: datetime
    end_date: Optional[datetime]=None
    created_at: datetime
    updated_at: datetime
    description: str
    sections: List[Section]

class LearningPathsResponse(BaseModel):
    data: List[LearningPath]
    pagination: Pagination

class LessonProgress(BaseModel):
    name: str
    description: str
    userProgress: float
    userScore: float

class ModuleProgress(BaseModel):
    name: str
    description: str
    progress: float
    score: float
    lessons: List[LessonProgress]

class CourseProgress(BaseModel):
    id: str
    name: str
    inscription_date: datetime
    progress: float
    score: float
    modules: List[ModuleProgress]

class SectionProgress(BaseModel):
    name: str
    progress: float
    courses: List[CourseProgress]

class LearningPathProgress(BaseModel):
    lp_id: str
    lp_name: str
    description: str
    lp_progress: float
    sections: List[SectionProgress]

class UserLMSProgressResponse(BaseModel):
    user_id: str
    user_name: str
    lps: List[LearningPathProgress]

class RedeemRequest(BaseModel):
    cardCodes: List[str]
    firstName: str
    lastName: str
    userEmail: EmailStr
    dueDate: date
    lpid: str

class RedeemData(BaseModel):
    lp_id: str
    lp_name: str
    user_id: str
    dueDate: date

class RedeemResponse(BaseModel):
    data: List[RedeemData]
    status: str
    mensaje: str
    token: str

class TokenValidation(BaseModel):
    user_id: str
    lp_id: str

def require_api_key(api_key: str):
    if api_key != DUMMY_API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")

@app.get("/")
def root():
    return {"status":"ok"}

@app.get("/cursos", response_model=LearningPathsResponse)
def cursos(lp_id: str=Query(..., alias="lp-id"), api_key: str=Header(..., alias="api-key")):
    require_api_key(api_key)
    now=datetime.now()
    lp=LearningPath(
        id=lp_id, name="Plan Demo", image_url=None,
        conditioned_courses=False, conditioned_sections=False, min_progress=0,
        certificate_delivery="LP ONLY", condition_delivery="LP END",
        welcome_message="Hola", is_gamified=False, status="active",
        start_date=now, end_date=None, created_at=now, updated_at=now,
        description="Demo", sections=[]
    )
    return LearningPathsResponse(data=[lp], pagination=Pagination(total=1,pages=1,page=1,limit=10))

@app.get("/cursos/{cursoId}", response_model=Course)
def curso(cursoId: str, api_key: str=Header(..., alias="api-key")):
    require_api_key(api_key)
    return Course(id=cursoId, name="Curso Demo", modules=[])

@app.get("/user-lms-progress", response_model=UserLMSProgressResponse)
def progress(user_id: str=Query(..., alias="user-id"), lp_id: str=Query(..., alias="lp-id"), api_key: str=Header(..., alias="api-key")):
    require_api_key(api_key)
    return UserLMSProgressResponse(user_id=user_id, user_name="Demo", lps=[])

@app.post("/redeem", response_model=RedeemResponse)
def redeem(body: RedeemRequest, api_key: str=Header(..., alias="api-key")):
    require_api_key(api_key)
    data=RedeemData(lp_id=body.lpid, lp_name="Demo LP", user_id="1", dueDate=body.dueDate)
    return RedeemResponse(data=[data], status="success", mensaje="ok", token=DUMMY_TOKEN)

@app.post("/token", response_model=TokenValidation)
def token(token: str = Header(...)):
    if token!=DUMMY_TOKEN:
        raise HTTPException(status_code=400, detail="Token inválido")
    return TokenValidation(user_id="1", lp_id="1")
