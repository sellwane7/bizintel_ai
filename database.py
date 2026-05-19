import sqlite3

DB = "bizintel.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT,
            surname TEXT,
            phone TEXT,
            password TEXT,
            fav_language TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            report_text TEXT,
            report_json TEXT,
            filename TEXT,
            total_records INTEGER,
            positive INTEGER,
            negative INTEGER,
            neutral INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def create_user(email, name, surname, phone, password, fav_language):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO users
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, name, surname, phone, password, fav_language))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def get_user(identifier):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT * FROM users
        WHERE email = ? OR phone = ?
    """, (identifier, identifier))

    user = c.fetchone()
    conn.close()

    return user


def update_password(email, new_password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        UPDATE users
        SET password = ?
        WHERE email = ?
    """, (new_password, email))

    conn.commit()
    conn.close()


def delete_user_account(email):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM history WHERE email = ?", (email,))
    c.execute("DELETE FROM users WHERE email = ?", (email,))

    conn.commit()
    conn.close()


def save_history(email, report_text, report_json,
                 filename="", total=0, pos=0, neg=0, neu=0):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO history
        (email, report_text, report_json, filename,
        total_records, positive, negative, neutral)

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        email, report_text, report_json,
        filename, total, pos, neg, neu
    ))

    conn.commit()
    conn.close()


def get_history(email):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT * FROM history
        WHERE email = ?
        ORDER BY timestamp DESC
    """, (email,))

    data = c.fetchall()

    conn.close()

    return data


def delete_history(history_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "DELETE FROM history WHERE id = ?",
        (history_id,)
    )

    conn.commit()
    conn.close()