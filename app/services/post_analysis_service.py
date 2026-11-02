from fastapi import HTTPException, status
import httpx

from app.core.config import settings


class PostAnalysisService:
    @staticmethod
    def analyze(content: str) -> dict:
        if settings.POST_ANALYSIS_SERVICE_URL:
            return PostAnalysisService._analyze_remote(content)
        return PostAnalysisService._analyze_local(content)

    @staticmethod
    def _analyze_remote(content: str) -> dict:
        url = f"{settings.POST_ANALYSIS_SERVICE_URL.rstrip('/')}/analyze"
        try:
            with httpx.Client(timeout=settings.MICROSERVICE_TIMEOUT_SECONDS) as client:
                response = client.post(url, json={"content": content})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Post-analysis service request failed: {exc}",
            ) from exc

        data = response.json()
        required = {"summary", "topic", "post_format", "hook_type", "media_type"}
        if not required.issubset(data):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Post-analysis service response missing required fields",
            )

        return {
            "provider": "post-analysis-service",
            "summary": data["summary"],
            "topic": data["topic"],
            "post_format": data["post_format"],
            "hook_type": data["hook_type"],
            "media_type": data["media_type"],
            "confidence": data.get("confidence"),
        }

    @staticmethod
    def _analyze_local(content: str) -> dict:
        lowered = content.lower()
        topic = "general"
        if "product" in lowered:
            topic = "product"
        elif "sales" in lowered:
            topic = "sales"
        elif "career" in lowered:
            topic = "career"

        post_format = "text"
        if "\n\n" in content:
            post_format = "structured"

        hook_type = "question" if "?" in content[:140] else "statement"
        media_type = "text"

        summary = (
            "Post emphasizes practical experience and can be strengthened with concrete metrics "
            "and one explicit call-to-action."
        )

        return {
            "provider": "local-fallback",
            "summary": summary,
            "topic": topic,
            "post_format": post_format,
            "hook_type": hook_type,
            "media_type": media_type,
            "confidence": 0.55,
        }
