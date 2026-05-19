"""User repository — wraps raw SQLAlchemy CRUD."""

from sqlalchemy.orm import Session

from app.server.models.user import UserModel


class UserRepository:
    """Data-access layer for users table."""

    def __init__(self, db: Session):
        self._db = db

    def get_by_username(self, username: str) -> UserModel | None:
        return self._db.query(UserModel).filter(UserModel.username == username).first()

    def get_by_email(self, email: str) -> UserModel | None:
        return self._db.query(UserModel).filter(UserModel.email == email).first()

    def get_by_id(self, user_id: str) -> UserModel | None:
        return self._db.query(UserModel).filter(UserModel.id == user_id).first()

    def create(self, model: UserModel) -> UserModel:
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model
