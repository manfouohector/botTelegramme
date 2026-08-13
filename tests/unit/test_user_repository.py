"""Tests unitaires — UserRepository."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repository import UserRepository


class TestUserRepository:
    def test_get_or_create_new_user(self, db_session):
        repo = UserRepository(db_session)
        user, created = repo.get_or_create(987654321, username="johndoe", first_name="John")
        assert created is True
        assert user.telegram_id == 987654321
        assert user.username == "johndoe"
        assert user.first_name == "John"

    def test_get_or_create_existing_user(self, db_session):
        repo = UserRepository(db_session)
        first, created_first = repo.get_or_create(111, username="alice")
        second, created_second = repo.get_or_create(111, username="alice")
        assert created_first is True
        assert created_second is False
        assert first.id == second.id

    def test_updates_profile_on_returning_user(self, db_session):
        repo = UserRepository(db_session)
        user, _ = repo.get_or_create(222, username="old_name", first_name="Old")
        updated, created = repo.get_or_create(222, username="new_name", first_name="New")
        assert created is False
        assert updated.id == user.id
        assert updated.username == "new_name"
        assert updated.first_name == "New"

    def test_get_by_telegram_id(self, db_session):
        repo = UserRepository(db_session)
        assert repo.get_by_telegram_id(999) is None
        user, _ = repo.get_or_create(999)
        assert repo.get_by_telegram_id(999).id == user.id

    def test_unique_telegram_id(self, db_session):
        from app.models.user import User

        db_session.add(User(telegram_id=555))
        db_session.add(User(telegram_id=555))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()
