import dash
from dash import Dash, html, dcc

external_sytlesheets = []
external_scripts = [
    {"src": "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"}
]

app = Dash(
    __name__,
    external_stylesheets=external_sytlesheets,
    external_scripts=external_scripts,
    title="Mi sitio en Dash",
    update_title="Cargando sitio...",
    use_async=True,
    use_pages=True,
    # suppress_callback_exceptions=True # Usar cuando se tenga la versión final del proyecto
)

header = html.Header(
    children=[
        dcc.Link(
            children="Inicio",
            href="/",
            className="font-bold text-xl"
        ),
        dcc.Link(
            children="Tableros",
            href="/tableros",
            className="font-bold text-xl"
        ),
    ],
    className="p-4 bg-pink-500 text-white text-center"
)

footer = html.Footer(
    children="2026 Liverpool - Todos los derechos reservados",
    className="p-4 bg-gray-200 text-white text-center"
)

app.layout = html.Div(
    children=[
        header,
        dash.page_container,
        # chatbot, # si quieren que se vea la ventana del chatbot en todas las páginas
        footer
    ]
)

if __name__ == "__main__":
    # Quitar debug=True cuanto ya se tenga el proyecto listo
    app.run(debug=True)