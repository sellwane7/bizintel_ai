import bcrypt

from database import (
    create_user,
    get_user,
    update_password,
    delete_user_account
)


def hash_password(password):
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()


def verify_password(password, hashed):
    return bcrypt.checkpw(
        password.encode(),
        hashed.encode()
    )


def register(email, name, surname, phone, password, fav_language):
    return create_user(
        email,
        name,
        surname,
        phone,
        hash_password(password),
        fav_language
    )


def login(email, password):
    user = get_user(email)

    if not user:
        return False, None

    if verify_password(password, user[4]):
        return True, user

    return False, None


def reset_password(email, new_password):
    update_password(
        email,
        hash_password(new_password)
    )