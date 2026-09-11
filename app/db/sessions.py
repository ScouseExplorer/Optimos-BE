# Alias for backwards compatibility – prefer importing from app.db.session
from app.db.session import SessionLocal, get_db, engine  # noqa: F401
