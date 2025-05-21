import datetime
from typing import List, Optional

from pydantic import BaseModel, confloat, root_validator

from database.models import MovieStatusEnum


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str

    model_config = {
        "from_attributes": True
    }


class MovieListResponseSchema(BaseModel):
    movies: List[MovieDetailSchema]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int


class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


class ActorSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


class LanguageSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


class CountrySchema(BaseModel):
    id: int
    code: str
    name: str | None

    model_config = {
        "from_attributes": True
    }


class MovieIDSchema(BaseModel):
    id: int


class MovieBaseSchema(BaseModel):
    name: str
    date: datetime.date
    score: float = confloat(ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = confloat(ge=0)
    revenue: float = confloat(ge=0)


class MovieListItemSchema(MovieBaseSchema, MovieIDSchema):
    country: CountrySchema
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    languages: List[LanguageSchema]

    model_config = {
        "from_attributes": True
    }


class MovieCreateSchema(MovieBaseSchema):
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]

    @root_validator(pre=True)
    def check_required_fields(cls, values):
        required_fields = [
            "name", "date", "score", "overview", "status", "budget",
            "revenue", "country", "genres", "actors", "languages"
        ]
        missing = [field for field in required_fields if field not in values]
        if missing:
            raise ValueError("Invalid input data.")
        return values


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[datetime.date] = None
    score: Optional[confloat(ge=0, le=100)] = None
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[confloat(ge=0)] = None
    revenue: Optional[confloat(ge=0)] = None
