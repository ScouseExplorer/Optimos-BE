from pydantic import BaseModel


class PostAnalysisRequest(BaseModel):
    save_to_post: bool = True


class PostAnalysisResponse(BaseModel):
    provider: str
    summary: str
    topic: str | None = None
    post_format: str | None = None
    hook_type: str | None = None
    media_type: str | None = None
    confidence: float | None = None
