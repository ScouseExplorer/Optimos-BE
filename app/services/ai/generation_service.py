import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class GenerationService:
    DEFAULT_MODEL = "gpt-5"

    @staticmethod
    def generate(context: dict) -> dict:
        if settings.AI_SERVICE_URL:
            return GenerationService._generate_remote(context)

        personal = context.get("personal_context", {})
        profile = personal.get("profile", {})
        display_name = profile.get("display_name") or "there"
        bio = profile.get("bio") or ""
        prompt = context.get("user_prompt", "")

        opening = f"Here is a personalized post idea for you, {display_name}:"
        body = (
            f"\n\nHook: A practical lesson I learned while building in public."
            f"\n\nCore: {prompt}."
            f"\nUse one concrete experience from your own work and explain what changed because of it."
            f"\n\nCTA: Ask your network for one contrasting perspective."
        )
        if bio:
            body += f"\n\nGrounding note from your profile: {bio}"

        text = opening + body
        return {
            "model": GenerationService.DEFAULT_MODEL,
            "text": text,
            "input_tokens": max(1, len(str(context).split())),
            "output_tokens": max(1, len(text.split())),
            "estimated_cost": 0.0,
        }

    @staticmethod
    def _generate_remote(context: dict) -> dict:
        url = f"{settings.AI_SERVICE_URL.rstrip('/')}/generate"

        try:
            with httpx.Client(timeout=settings.MICROSERVICE_TIMEOUT_SECONDS) as client:
                response = client.post(url, json={"context": context})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service request failed: {exc}",
            ) from exc

        data = response.json()
        required = {"model", "text", "input_tokens", "output_tokens", "estimated_cost"}
        if not required.issubset(data):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI service response missing required fields",
            )

        return {
            "model": data["model"],
            "text": data["text"],
            "input_tokens": data["input_tokens"],
            "output_tokens": data["output_tokens"],
            "estimated_cost": data["estimated_cost"],
        }

    @staticmethod
    def refine_with_grounding(text: str, context: dict) -> str:
        personal = context.get("personal_context", {})
        profile = personal.get("profile", {})
        bio = profile.get("bio")
        if bio:
            return text + f"\n\nAdd this personal anchor explicitly: {bio}"
        return text + "\n\nAdd one concrete personal anecdote before posting."
