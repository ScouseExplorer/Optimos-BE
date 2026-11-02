from sqlalchemy.orm import Session

from app.models.chat import Chat
from app.models.profile import UserProfile


class PersonalDataRetriever:
    @staticmethod
    def retrieve(db: Session, user_id: int, query: str) -> dict:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        recent_chats = (
            db.query(Chat)
            .filter(Chat.user_id == user_id)
            .order_by(Chat.created_at.desc())
            .limit(5)
            .all()
        )

        return {
            "query": query,
            "profile": {
                "display_name": profile.display_name if profile else None,
                "bio": profile.bio if profile else None,
                "timezone": profile.timezone if profile else None,
                "language": profile.language if profile else None,
            },
            "recent_interactions": [
                {
                    "user_message": c.user_message,
                    "ai_response": c.ai_response,
                }
                for c in recent_chats
            ],
        }
