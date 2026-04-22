import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal

class StudentModel(BaseModel):
    gender: Literal["male", "female"]
    race_ethnicity: Literal["group A", "group B", "group C", "group D", "group E"]
    parental_level_of_education: str
    lunch: str
    test_preparation_course: str
    math_score: int = Field(ge=0, le=100)
    reading_score: int = Field(ge=0, le=100)
    writing_score: int = Field(ge=0, le=100)
    
load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

conn_string = (
    f"host={DB_HOST} "
    f"port={DB_PORT} "
    f"dbname={DB_NAME} "
    f"user={DB_USER} "
    f"password={DB_PASSWORD}"
)

pool = AsyncConnectionPool(conninfo=conn_string, open=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    print("Connection pool initialized...")
    yield
    await pool.close()
    print("Connection pool closed...")

df = pd.read_csv("exams.csv")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def get_index():
    return "Hola, soy la ruta principal."

@app.get("/top_5_math_scores")
def get_top_5_math_scores():
    return df["math score"].nlargest(5).to_list()

@app.get("/race_ethnicity_means")
def get_race_ethnicity_means():
    return df.groupby("race/ethnicity")[["math score", "reading score", "writing score"]].mean().reset_index().to_dict(orient="records")

# Parámetros de ruta (path parameters)
@app.get("/race_ethnicity/{group}")
def get_race_ethnicity(group : str):
    group = group.upper()
    if group not in ["A", "B", "C", "D", "E"]:
        return "El grupo debe ser A, B, C, D o E."
    return df.loc[df["race/ethnicity"] == f"group {group}"].describe().reset_index().to_dict(orient="records")

# Parámetros de consulta (query parameters)
# Se utilizan mucho para personalizar listados order, límite
# Si se combinan los dos tipos de parámetros, primero se listan
# los parámetros de ruta y después los de consulta
@app.get("/sample")
def get_sample(order : str = "asc", limit : int = 5):
    if limit <= 0: 
        limit = 5
    if order == "desc":
        return df.tail(limit).to_dict(orient="records")
    return df.head(limit).to_dict(orient="records")

@app.post("/student")
def post_student(student : StudentModel):
    new_row = pd.DataFrame([{
        "gender": student.gender,
        "race/ethnicity": student.race_ethnicity,
        "parental level of education": student.parental_level_of_education,
        "lunch": student.lunch,
        "test preparation course": student.test_preparation_course,
        "math score": student.math_score,
        "reading score": student.reading_score,
        "writing score": student.writing_score
    }])
    return new_row.to_dict(orient="records")

@app.get("/first_rows")
async def get_first_rows():
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        async with conn.cursor() as cur:
            res = await cur.execute("SELECT * from marcas LIMIT 10")
            return await res.fetchall()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)