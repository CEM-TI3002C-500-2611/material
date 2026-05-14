import dash
import httpx
import pandas as pd
import dash_ag_grid as dag
import plotly.express as px
from dash import html, dcc, dash_table

dash.register_page(
    __name__,
    path="/tableros",
    title="Tableros de visualización",
    name="tableros"
)

async def layout():
    API_URL = "http://localhost:8000"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/first_rows")
            response.raise_for_status()
            first_rows = response.json()
    except Exception as e:
        first_rows = []
    df = pd.DataFrame(first_rows)
    clases = df["clase"].value_counts().reset_index()
    fig = px.bar(
        data_frame=clases,
        x="clase",
        y="count"
    )
    return html.Div(
        children=[
            html.H1(
                children="Tableros de visualización",
                className="text-3xl font-bold mb-4"
            ),
            html.H2(
                children="Primeras filas de la tabla marcas con Dash Table",
                className="text-2xl font-semibold mb-2"
            ),
            dash_table.DataTable(data=df.to_dict(orient="records"), page_size=5),
            html.H2(
                children="Primeras filas de la tabla marcas con Dash AG Grid",
                className="text-2xl font-semibold mb-2"
            ),
            dag.AgGrid(
                rowData=df.to_dict(orient="records"),
                columnDefs=[
                    {"field": col, "sortable": True, "filter": True}
                    for col in df.columns
                ],
                columnSize="responsiveSizeToFit",
                dashGridOptions={
                    "pagination": True,
                    "paginationPageSize": 5
                }
            ),
            html.H2(
                children="Gráfica de aparición de clases",
                className="text-2xl font-semibold mb-2"
            ),
            dcc.Graph(
                figure=fig
            )
        ]
    )