from db.connection import get_pool

def register_user(username: str, password: str):
    pool = get_pool()
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING users_id",
            (username, password)
        )
        conn.commit()
        user_id = cursor.fetchone()[0]
        return user_id
    
def get_user_by_username(username: str):
    pool = get_pool()
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user:
            return {
                "users_id": user[0],
                "username": user[1],
                "hashed_password": user[2]
            }
        return None