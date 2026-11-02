from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.ai.generation_service import GenerationService
from app.services.ai.validation_service import ValidationService
from app.services.chat_service import ChatService
from app.services.feature_gate_service import FeatureGateService
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.personal_data_retriever import PersonalDataRetriever
from app.services.subscription_service import SubscriptionService
from app.services.usage_service import UsageService


class AIOrchestrator:
    @staticmethod
    def generate_post_idea(db: Session, user_id: int, prompt: str, request_id: str) -> object:
        existing_chat = ChatService.get_chat_by_request_id(db, user_id, request_id)
        if existing_chat:
            return existing_chat

        if not SubscriptionService.check_message_limit(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly message limit reached for this plan",
            )

        reservation = None
        credits_charged = 0

        try:
            reservation = FeatureGateService.assert_and_reserve(
                db=db,
                user_id=user_id,
                feature_key="generate_post",
                request_id=request_id,
                description="AI generation request",
            )
            if reservation and reservation.amount < 0:
                credits_charged = abs(reservation.amount)

            personal_context = PersonalDataRetriever.retrieve(db, user_id, prompt)
            context = ContextBuilder.build(personal_context, prompt)

            generation = GenerationService.generate(context)
            response_text = generation["text"]

            validation = ValidationService.evaluate(response_text)
            if validation["is_generic"]:
                response_text = GenerationService.refine_with_grounding(response_text, context)

            chat = ChatService.create_chat(
                db=db,
                user_id=user_id,
                user_message=prompt,
                ai_response=response_text,
                tokens_used=generation["output_tokens"],
                request_id=request_id,
            )

            SubscriptionService.increment_message_usage(db, user_id, tokens=1)

            FeatureGateService.settle_if_reserved(db, reservation, user_id)

            UsageService.record_usage(
                db=db,
                user_id=user_id,
                action="generate_post",
                model=generation["model"],
                status="success",
                credits_charged=credits_charged,
                input_tokens=generation["input_tokens"],
                output_tokens=generation["output_tokens"],
                estimated_cost=generation["estimated_cost"],
                request_id=request_id,
            )
            return chat

        except HTTPException as exc:
            FeatureGateService.release_if_reserved(db, reservation, user_id)

            UsageService.record_usage(
                db=db,
                user_id=user_id,
                action="generate_post",
                model=GenerationService.DEFAULT_MODEL,
                status="failed",
                credits_charged=0,
                request_id=request_id,
                error_message=exc.detail if isinstance(exc.detail, str) else "Request failed",
            )
            raise

        except Exception:
            FeatureGateService.release_if_reserved(db, reservation, user_id)

            UsageService.record_usage(
                db=db,
                user_id=user_id,
                action="generate_post",
                model=GenerationService.DEFAULT_MODEL,
                status="failed",
                credits_charged=0,
                request_id=request_id,
                error_message="Unexpected server error during AI orchestration",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI operation failed",
            )
