import joblib
import os
import pandas as pd
from dotenv import load_dotenv

from contextlib import asynccontextmanager
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal

from google import genai
from google.genai import types

class StudentModel(BaseModel):
    gender: Literal["male", "female"]
    race_ethnicity: Literal["group A", "group B", "group C", "group D", "group E"]
    parental_level_of_education: str
    lunch: str
    test_preparation_course: str
    math_score: int = Field(ge=0, le=100)
    reading_score: int = Field(ge=0, le=100)
    writing_score: int = Field(ge=0, le=100)
    
class RenovationPredictionModel(BaseModel):
    ventas_totales: int
    ingresos: float
    antiguedad_marca: int
    numero_leads_web: int
    calificacion_promedio_productos: float
    numero_devoluciones: int
    participacion_mercado: float
    participacion_mercado_promedio: float
    
class GeminiChatModel(BaseModel):
    prompt: str
    
load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
GOOGLE_GENAI_API_KEY = os.getenv('GOOGLE_GENAI_API_KEY')

conn_string = (
    f"host={DB_HOST} "
    f"port={DB_PORT} "
    f"dbname={DB_NAME} "
    f"user={DB_USER} "
    f"password={DB_PASSWORD}"
)

pool = AsyncConnectionPool(conninfo=conn_string, open=False)
client = genai.Client(api_key=GOOGLE_GENAI_API_KEY)

async def get_shema_description() -> str:
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """)
            rows = await cur.fetchall()
    tables: Dict[str, Any] = {}
    for row in rows:
        table_name = row["table_name"]
        col = f"{row['column_name']} ({row['data_type']})"
        tables.setdefault(table_name, []).append(col)
    lines = ["Esquema de la base de datos:"]
    for table, cols in tables.items():
        lines.append(f"- {table}:")
        for col in cols:
            lines.append(f"  - {col}")
    return "\n".join(lines)

def _is_safe_query(query: str) -> bool:
    normalized = query.strip().lower()
    forbidden =("insert", "update", "delete", "drop", "alter", "truncate", "create", "grant", "revoke", "copy")
    if not normalized.startswith("select"):
        return False
    return not any(word in normalized for word in forbidden)

async def query_database(query: str) -> str:
    """
    Ejecuta una consulta SQL de solo lectura en la base de datos y devuelve los resultados en formato JSON.
    Args:
        query (str): La consulta SQL a ejecutar. Debe ser una consulta SELECT.
    """
    if not _is_safe_query(query):
        return "Error: Consulta no permitida. Solo se permiten consultas SELECT."

    try:
        async with pool.connection() as conn:
            conn.row_factory = dict_row
            async with conn.cursor() as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
                return json.dumps(rows, default=str)
    except Exception as e:
        return f"Error al ejecutar la consulta: {str(e)}"

def predict_renovation_tool(
    ventas_totales: int,
    ingresos: float,
    antiguedad_marca: int,
    numero_leads_web: int,
    calificacion_promedio_productos: float,
    numero_devoluciones: int,
    participacion_mercado: float,
    participacion_mercado_promedio: float,
) -> str:
    """
    Realiza una predicción de renovación de marca ante el IMPI para una marca usando el modelo de machine learning.
    Úsala cuando el usuario proporcione datos de una marca y quiera saber si renovará su contrato.
    Args:
        ventas_totales: Número total de ventas de la marca.
        ingresos: Ingresos totales de la marca.
        antiguedad_marca: Años de antigüedad de la marca.
        numero_leads_web: Número de leads generados por web.
        calificacion_promedio_productos: Calificación promedio de los productos (0-5).
        numero_devoluciones: Número de devoluciones registradas.
        participacion_mercado: Participación actual en el mercado (fracción entre 0 y 1).
        participacion_mercado_promedio: Participación promedio histórica en el mercado.
    Returns:
        Resultado de la predicción como cadena de texto.
    """
    input_data = pd.DataFrame([{
        "ventas_totales": ventas_totales,
        "ingresos": ingresos,
        "antiguedad_marca": antiguedad_marca,
        "numero_leads_web": numero_leads_web,
        "calificacion_promedio_productos": calificacion_promedio_productos,
        "numero_devoluciones": numero_devoluciones,
        "participacion_mercado": participacion_mercado,
        "participacion_mercado_promedio": participacion_mercado_promedio,
    }])
    prediction = app.state.modelo_renovacion.predict(input_data)[0]
    return f"Predicción de renovación: {prediction}"

async def chat_with_gemini(prompt: str, schema_description: str) -> str:
    MODEL = "gemini-2.5-flash"
    SYSTEM_PROMPT = """
Eres un asistente de inteligencia artificial especializado en análisis de datos y generación de insights a partir de conjuntos de datos. 
Tu tarea es ayudar a los usuarios a comprender mejor sus datos, identificar patrones, tendencias y relaciones entre variables, 
y proporcionar recomendaciones basadas en el análisis.
"""
    config = types.GenerateContentConfig(
        system_instruction=f"{SYSTEM_PROMPT}\n{schema_description}",
        tools=[query_database, predict_renovation_tool],
    )
    response = await client.aio.models.generate_content(
        model=MODEL,
        config=config,
        contents=prompt,
    )
    return response.text
        
async def predict_renovation(data: RenovationPredictionModel):
    input_data = pd.DataFrame([data.model_dump()])
    prediction = app.state.modelo_renovacion.predict(input_data)[0]
    return {"prediccion": prediction}

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.df = pd.read_csv("exams.csv")
    await pool.open()
    app.state.schema_description = await get_shema_description()
    app.state.model = joblib.load("modelo_renovacion.joblib")
    print("Connection pool opened and model loaded...")
    yield
    await pool.close()
    print("Connection pool closed...")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def get_index():
    return "Hola, soy la ruta principal."

@app.get("/top_5_math_scores")
def get_top_5_math_scores():
    return app.state.df["math score"].nlargest(5).to_list()

@app.get("/race_ethnicity_means")
def get_race_ethnicity_means():
    return app.state.df.groupby("race/ethnicity")[["math score", "reading score", "writing score"]].mean().reset_index().to_dict(orient="records")

# Parámetros de ruta (path parameters)
@app.get("/race_ethnicity/{group}")
def get_race_ethnicity(group : str):
    group = group.upper()
    if group not in ["A", "B", "C", "D", "E"]:
        return "El grupo debe ser A, B, C, D o E."
    return app.state.df.loc[app.state.df["race/ethnicity"] == f"group {group}"].describe().reset_index().to_dict(orient="records")

# Parámetros de consulta (query parameters)
# Se utilizan mucho para personalizar listados order, límite
# Si se combinan los dos tipos de parámetros, primero se listan
# los parámetros de ruta y después los de consulta
@app.get("/sample")
def get_sample(order : str = "asc", limit : int = 5):
    if limit <= 0: 
        limit = 5
    if order == "desc":
        return app.state.df.tail(limit).to_dict(orient="records")
    return app.state.df.head(limit).to_dict(orient="records")

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

@app.post("/predict_brand_renovation")
async def post_predict_brand_renovation(data: RenovationPredictionModel):
    pred_df = pd.DataFrame([data.model_dump()])
    predicted_class = app.state.model.predict(pred_df)[0]
    probability = app.state.model.predict_proba(pred_df)[0]
    return {
        "renovacion": predicted_class,
        "probabilidad": probability.tolist()
    }
    
@app.post("/chat")
async def chat(prompt: GeminiChatModel):
    response = await chat_with_gemini(prompt.prompt, app.state.schema_description)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)