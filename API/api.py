# api.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from renderer import render_filtered_view_base64


class FilterModel(BaseModel):
    layers: Optional[List[str]] = None
    types: Optional[List[str]] = None
    ids: Optional[List[str]] = None


class RenderRequest(BaseModel):
    data: Dict[str, Any]             # The CAD JSON object
    filters: Optional[FilterModel] = None
    show_background: bool = True


class RenderResponse(BaseModel):
    image_base64: str


app = FastAPI(
    title="CAD Renderer API",
    description="Render filtered CAD JSON into a base64 PNG image.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/render", response_model=RenderResponse)
def render_view(req: RenderRequest):
    """
    Render a filtered CAD image and return base64 PNG.
    """
    filters_dict = req.filters.dict() if req.filters else None

    result = render_filtered_view_base64(
        json_path_or_data=req.data,
        filters=filters_dict,
        show_background=req.show_background
    )

    return RenderResponse(**result)
