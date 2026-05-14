import dash
from dash import html

dash.register_page(
    __name__,
    path="/",
    title="Inicio",
    name="index"
)

async def layout():
    return html.Div(
        children=[
            html.H1(
                children="Página de inicio",
                className="text-3xl font-bold mb-4"
            ),
            html.P(
                children="Sitio de analítica de datos para el área jurídica de Liverpool...",
                className="text-lg"
            ),
            html.Img(
                src=dash.get_asset_url("images/freestocks-_3Q3tsJ01nc-unsplash.jpg"),
                className="w-1/2 mx-auto"
            )
        ]
    )