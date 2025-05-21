from http.client import HTTPResponse
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic_core._pydantic_core import ValidationError
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import MovieListResponseSchema, MovieDetailSchema, MovieCreateSchema, MovieListItemSchema, \
    MovieUpdateSchema

router = APIRouter()


# Write your code here
@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=20),
        db: AsyncSession = Depends(get_db)
):
    total_result = await db.execute(
        select(func.count()).select_from(MovieModel)
    )
    total_items = total_result.scalar_one_or_none()
    total_pages = (total_items + per_page - 1) // per_page

    offset = (page - 1) * per_page
    result = await db.execute(
        select(MovieModel).offset(offset).limit(per_page).order_by(-MovieModel.id)
    )
    movies_page = result.scalars().all()

    if not movies_page:
        raise HTTPException(status_code=404, detail="No movies found.")

    return {
        "movies": [MovieDetailSchema.model_validate(movie.__dict__) for movie in movies_page],
        "prev_page": f"/theater/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        "next_page": f"/theater/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.post("/movies/", response_model=MovieListItemSchema, status_code=201)
async def create_movie(movie_create: MovieCreateSchema,  db: AsyncSession = Depends(get_db)):
    movie = await db.execute(select(MovieModel).where(
        and_(
            MovieModel.name == movie_create.name,
            MovieModel.date == movie_create.date
        )
    ))
    movie_result = movie.scalar_one_or_none()
    if movie_result is not None:
        raise HTTPException(status_code=409,
                            detail=f"A movie with the name '{movie_create.name}' and release date '{movie_create.date}' already exists.")

    country = await db.execute(select(CountryModel).where(CountryModel.code == movie_create.country))
    country_result = country.scalar_one_or_none()
    if country_result is None:
        country_result = CountryModel(code=movie_create.country)
        db.add(country_result)
        await db.flush()

    genres_list = []
    for genre_name in movie_create.genres:
        get_genre = await db.execute(select(GenreModel).where(GenreModel.name == genre_name))
        result_genre = get_genre.scalar_one_or_none()
        if not result_genre:
            result_genre = GenreModel(name=genre_name)
            db.add(result_genre)
        genres_list.append(result_genre)

    actors_list = []
    for actor_name in movie_create.actors:
        get_actor = await db.execute(select(ActorModel).where(ActorModel.name == actor_name))
        result_actor = get_actor.scalar_one_or_none()
        if not result_actor:
            result_actor = ActorModel(name=actor_name)
            db.add(result_actor)
        actors_list.append(result_actor)

    languages_list = []
    for language_name in movie_create.languages:
        language = await db.execute(select(LanguageModel).where(LanguageModel.name == language_name))
        result_language = language.scalar_one_or_none()
        if not result_language:
            result_language = LanguageModel(name=language_name)
            db.add(result_language)
        languages_list.append(result_language)

    await db.flush()
    dict_movie = dict(
        name=movie_create.name,
        date=movie_create.date,
        score=movie_create.score,
        overview=movie_create.overview,
        status=movie_create.status,
        budget=movie_create.budget,
        revenue=movie_create.revenue,
        country_id=country_result.id,
        country=country_result,
        genres=genres_list,
        actors=actors_list,
        languages=languages_list,
    )

    existing_movie = await db.scalar(
        select(MovieModel).where(MovieModel.name == movie_create.name, MovieModel.date == movie_create.date)
    )
    if not existing_movie:
        movie_create = MovieModel(
            **dict_movie
        )
        db.add(movie_create)
        await db.flush()
    else:
        raise HTTPException(status_code=400, detail="Movie already exists.")

    await db.commit()
    movie_with_relations = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_create.id)
    )
    movie_full = movie_with_relations.scalar_one()
    return movie_full


@router.get("/movies/{movie_id}/", response_model=MovieListItemSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    movie_result = result.scalar_one_or_none()
    if not movie_result:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    return MovieListItemSchema.from_orm(movie_result)


@router.delete("/movies/{movie_id}/")
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))

    result_movie = movie.scalar_one_or_none()
    if not result_movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    await db.delete(result_movie)
    await db.commit()
    return JSONResponse(status_code=204, content={"message": "Movie deleted."})


@router.patch("/movies/{movie_id}/")
async def update_movie(movie_id: int, movie: MovieUpdateSchema, db: AsyncSession = Depends(get_db)):
    db_movie = await db.execute(select(MovieModel).options(
        selectinload(MovieModel.country),
        selectinload(MovieModel.genres),
        selectinload(MovieModel.actors),
        selectinload(MovieModel.languages),
    ).where(MovieModel.id == movie_id))
    movie_result = db_movie.scalar_one_or_none()
    if not movie_result:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    update_data = movie.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(movie_result, key, value)

    await db.commit()
    await db.refresh(movie_result)
    return {"detail": "Movie updated successfully."}
