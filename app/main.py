from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.routes import router

app = FastAPI(title="FastAPI OCR API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="FastAPI OCR API",
        version="0.1.0",
        openapi_version="3.0.3",
        routes=app.routes,
    )

    body_schema = openapi_schema["components"]["schemas"].get(
        "Body_ocr_both_ocr_both_post"
    )

    if body_schema:
        # Make both fields optional in Swagger
        body_schema.pop("required", None)

        body_schema["properties"]["cccd_files"] = {
            "title": "Cccd Files",
            "type": "array",
            "items": {
                "type": "string",
                "format": "binary",
            },
        }

        body_schema["properties"]["gpkd_files"] = {
            "title": "Gpkd Files",
            "type": "array",
            "items": {
                "type": "string",
                "format": "binary",
            },
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
