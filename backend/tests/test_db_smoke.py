from sqlalchemy import select

from kupto.models import User


async def test_can_store_and_read_user(session):
    session.add(User(login="ala", password_hash="x"))
    await session.commit()

    users = (await session.scalars(select(User))).all()

    assert [u.login for u in users] == ["ala"]


async def test_tables_are_truncated_between_tests(session):
    assert (await session.scalars(select(User))).all() == []
