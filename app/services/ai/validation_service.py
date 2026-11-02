class ValidationService:
    GENERIC_PHRASES = [
        "unlock your potential",
        "in today's fast-paced world",
        "game-changer",
        "never give up",
        "dream big",
        "synergy",
    ]

    @staticmethod
    def evaluate(text: str) -> dict:
        lowered = text.lower()
        generic_hits = [phrase for phrase in ValidationService.GENERIC_PHRASES if phrase in lowered]

        return {
            "is_generic": len(generic_hits) >= 2,
            "generic_hits": generic_hits,
        }
