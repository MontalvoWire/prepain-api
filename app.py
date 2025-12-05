from datetime import date, datetime
import secrets
import string
from random import SystemRandom
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException, Path, Query
from pydantic import BaseModel, EmailStr

from moodle_client import MOODLE_STUDENT_ROLE_ID, call_moodle

app = FastAPI(title="PrepaIn API", version="1.0", description="Mock API alineada a openapi.yaml")

DUMMY_API_KEY = "test-api-key"
DUMMY_TOKEN = "dummy-token-123"
MOCK_TIMESTAMP = datetime(2025, 3, 10, 12, 0, 0)
MOODLE_CATEGORY_NAME = "prepain"


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
    courses: List[Course]


class LearningPath(BaseModel):
    id: str
    name: str
    image_url: Optional[str] = None
    conditioned_courses: bool
    conditioned_sections: bool
    min_progress: int
    certificate_delivery: str
    condition_delivery: str
    welcome_message: str
    is_gamified: bool
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
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


def require_api_key(api_key: Optional[str]) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="No autorizado: falta api-key")
    if api_key != DUMMY_API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado: api-key inválida")
    return api_key


def build_course(curso_id: str) -> Course:
    lessons = [
        Lesson(name="Introducción", description="Contenido de arranque", type="video", subtype="mp4"),
        Lesson(name="Ejercicios", description="Ejercicios guiados", type="quiz", subtype="form"),
    ]
    modules = [
        Module(
            id="mod-1",
            name="Módulo Demo",
            description="Módulo de ejemplo",
            lessons=lessons,
        )
    ]
    return Course(id=curso_id, name="Curso Demostración", modules=modules)


def build_learning_path(lp_id: str) -> LearningPath:
    course = build_course(f"{lp_id}-curso")
    section = Section(name="Sección Inicial", courses=[course])
    return LearningPath(
        id=lp_id,
        name="Plan Demo",
        image_url="https://placehold.co/600x400",
        conditioned_courses=False,
        conditioned_sections=False,
        min_progress=0,
        certificate_delivery="LP ONLY",
        condition_delivery="LP END",
        welcome_message="Bienvenido al plan de prueba",
        is_gamified=False,
        status="active",
        start_date=MOCK_TIMESTAMP,
        end_date=None,
        created_at=MOCK_TIMESTAMP,
        updated_at=MOCK_TIMESTAMP,
        description="Plan de carrera de demostración",
        sections=[section],
    )


def build_progress(user_id: str, lp_id: str) -> UserLMSProgressResponse:
    lesson_progress = LessonProgress(
        name="Introducción",
        description="Introducción al curso",
        userProgress=0.4,
        userScore=8.5,
    )
    module_progress = ModuleProgress(
        name="Módulo Demo",
        description="Módulo de ejemplo",
        progress=0.5,
        score=9.0,
        lessons=[lesson_progress],
    )
    course_progress = CourseProgress(
        id="curso-101",
        name="Curso Demostración",
        inscription_date=MOCK_TIMESTAMP,
        progress=0.5,
        score=9.2,
        modules=[module_progress],
    )
    section_progress = SectionProgress(name="Sección Inicial", progress=0.45, courses=[course_progress])
    lp_progress = LearningPathProgress(
        lp_id=lp_id,
        lp_name="Plan Demo",
        description="Plan de prueba",
        lp_progress=0.45,
        sections=[section_progress],
    )
    return UserLMSProgressResponse(user_id=user_id, user_name="Demo User", lps=[lp_progress])


def build_redeem_response(body: RedeemRequest) -> RedeemResponse:
    redeem_data = RedeemData(lp_id=body.lpid, lp_name="Plan Demo", user_id="user-001", dueDate=body.dueDate)
    return RedeemResponse(data=[redeem_data], status="success", mensaje="Tarjetas redimidas", token=DUMMY_TOKEN)


def _generate_moodle_password(length: int = 16) -> str:
    letters_digits = string.ascii_letters + string.digits
    specials = "*-#@!$"
    pool = letters_digits + specials
    password_chars = [secrets.choice(pool) for _ in range(max(length - 1, 1))]
    password_chars.append(secrets.choice(specials))
    SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def _to_datetime(timestamp_value: Optional[int]) -> datetime:
    if timestamp_value:
        try:
            return datetime.fromtimestamp(timestamp_value)
        except (TypeError, ValueError, OSError):
            pass
    return MOCK_TIMESTAMP


async def _get_moodle_category_id() -> int:
    categories = await call_moodle(
        "core_course_get_categories",
        {"criteria[0][key]": "name", "criteria[0][value]": MOODLE_CATEGORY_NAME},
    )
    category = next((cat for cat in categories if cat.get("name") == MOODLE_CATEGORY_NAME), None)
    if not category:
        raise HTTPException(status_code=400, detail=f"Categoría '{MOODLE_CATEGORY_NAME}' no encontrada en Moodle")
    category_id = category.get("id")
    if category_id is None:
        raise HTTPException(status_code=502, detail="Respuesta inválida de Moodle al obtener la categoría")
    return category_id


async def _get_courses_in_category(category_id: int) -> List[int]:
    courses_response = await call_moodle(
        "core_course_get_courses_by_field",
        {"field": "category", "value": category_id},
    )
    courses = courses_response.get("courses") if isinstance(courses_response, dict) else None
    if courses is None:
        raise HTTPException(status_code=502, detail="Respuesta inválida de Moodle al obtener cursos")

    course_ids = [course.get("id") for course in courses if course.get("id") is not None]
    if not course_ids:
        raise HTTPException(status_code=400, detail=f"No hay cursos en la categoría '{MOODLE_CATEGORY_NAME}'")
    return course_ids


async def _get_or_create_user(body: RedeemRequest) -> int:
    users = await call_moodle(
        "core_user_get_users_by_field",
        {"field": "email", "values[0]": body.userEmail},
    )
    if isinstance(users, list) and users:
        user_id = users[0].get("id")
        if user_id is None:
            raise HTTPException(status_code=502, detail="Usuario encontrado sin id en Moodle")
        return user_id

    password = _generate_moodle_password()
    created_users = await call_moodle(
        "core_user_create_users",
        {
            "users[0][username]": body.userEmail,
            "users[0][password]": password,
            "users[0][firstname]": body.firstName,
            "users[0][lastname]": body.lastName,
            "users[0][email]": body.userEmail,
            "users[0][auth]": "manual",
            "users[0][lang]": "es_mx",
        },
    )

    if not isinstance(created_users, list) or not created_users:
        raise HTTPException(status_code=502, detail="No se pudo crear el usuario en Moodle")

    user_id = created_users[0].get("id")
    if user_id is None:
        raise HTTPException(status_code=502, detail="Respuesta inválida de Moodle al crear usuario")
    return user_id


async def _enrol_user_to_courses(user_id: int, course_ids: List[int]) -> None:
    enrolments = {}
    for idx, course_id in enumerate(course_ids):
        enrolments[f"enrolments[{idx}][roleid]"] = MOODLE_STUDENT_ROLE_ID
        enrolments[f"enrolments[{idx}][userid]"] = user_id
        enrolments[f"enrolments[{idx}][courseid]"] = course_id

    await call_moodle("enrol_manual_enrol_users", enrolments)


async def handle_moodle_enrollment(body: RedeemRequest) -> None:
    category_id = await _get_moodle_category_id()
    course_ids = await _get_courses_in_category(category_id)
    user_id = await _get_or_create_user(body)
    await _enrol_user_to_courses(user_id, course_ids)


async def _fetch_moodle_courses(category_id: int) -> List[dict]:
    courses_response = await call_moodle(
        "core_course_get_courses_by_field",
        {"field": "category", "value": category_id},
    )
    courses = courses_response.get("courses") if isinstance(courses_response, dict) else None
    if courses is None:
        raise HTTPException(status_code=502, detail="Respuesta inválida de Moodle al obtener cursos")
    return courses


def _map_moodle_course_to_learning_path(course: dict) -> LearningPath:
    course_id = str(course.get("id"))
    name = course.get("fullname") or course.get("shortname") or course_id
    description = course.get("summary") or ""
    start_date = _to_datetime(course.get("startdate") or course.get("timecreated"))
    end_date = _to_datetime(course.get("enddate")) if course.get("enddate") else None
    created_at = _to_datetime(course.get("timecreated"))
    updated_at = _to_datetime(course.get("timemodified"))

    course_model = Course(id=course_id, name=name, modules=[])
    section = Section(name=course.get("shortname") or name, courses=[course_model])

    return LearningPath(
        id=course_id,
        name=name,
        image_url=None,
        conditioned_courses=False,
        conditioned_sections=False,
        min_progress=0,
        certificate_delivery="LP ONLY",
        condition_delivery="LP END",
        welcome_message="",
        is_gamified=False,
        status="active",
        start_date=start_date,
        end_date=end_date,
        created_at=created_at,
        updated_at=updated_at,
        description=description,
        sections=[section],
    )


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/cursos", response_model=LearningPathsResponse)
async def cursos(
    lp_id: Optional[str] = Query(default=None, alias="lp-id", description="Opcional: filtra por lp-id"),
    api_key: Optional[str] = Header(default=None, alias="api-key"),
):
    require_api_key(api_key)
    category_id = await _get_moodle_category_id()
    courses = await _fetch_moodle_courses(category_id)
    learning_paths = [_map_moodle_course_to_learning_path(course) for course in courses]

    if lp_id:
        learning_paths = [lp for lp in learning_paths if lp.id == lp_id]

    pagination = Pagination(total=len(learning_paths), pages=1, page=1, limit=len(learning_paths))
    return LearningPathsResponse(data=learning_paths, pagination=pagination)


@app.get("/cursos/{cursoId}", response_model=Course)
def curso(
    cursoId: str = Path(..., description="ID del curso"),
    api_key: Optional[str] = Header(default=None, alias="api-key"),
):
    require_api_key(api_key)
    return build_course(cursoId)


@app.get("/user-lms-progress", response_model=UserLMSProgressResponse)
def progress(
    user_id: str = Query(..., alias="user-id"),
    lp_id: str = Query(..., alias="lp-id"),
    api_key: Optional[str] = Header(default=None, alias="api-key"),
):
    require_api_key(api_key)
    return build_progress(user_id, lp_id)


@app.post("/redeem", response_model=RedeemResponse)
async def redeem(body: RedeemRequest, api_key: Optional[str] = Header(default=None, alias="api-key")):
    require_api_key(api_key)
    await handle_moodle_enrollment(body)
    return build_redeem_response(body)


@app.post("/token", response_model=TokenValidation)
def token(token: Optional[str] = Header(default=None)):
    if not token or token != DUMMY_TOKEN:
        raise HTTPException(status_code=400, detail="Token inválido o faltante")
    return TokenValidation(user_id="user-001", lp_id="lp-001")
