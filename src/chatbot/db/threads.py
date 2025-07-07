from db.connection import get_pool
from langgraph.checkpoint.postgres import PostgresSaver

def get_threads_db(user_id: str):
    pool = get_pool()
    with pool.connection() as conn:
        print(f"Fetching threads for user_id: {user_id}", flush=True)
        cursor = conn.cursor()
        cursor.execute("SELECT thread_id, title FROM users_threads WHERE user_id = %s", (user_id,))
        threads = cursor.fetchall()
        print(f"Threads fetched: {threads}", flush=True)
        response = []
        for thread in threads:
            response.append({
                "id": thread[0],
                "title": thread[1]
            })
        return response

def create_thread(user_id: str):
    pool = get_pool()
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users_threads (user_id) VALUES (%s) RETURNING thread_id", (user_id,))
        thread_id = cursor.fetchone()[0]
        conn.commit()
        return thread_id
    
def delete_thread(thread_id: str):
    pool = get_pool()
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users_threads WHERE thread_id = %s", (thread_id,))
        conn.commit()
        return {"message": "Thread deleted successfully"}

def get_thread_messages(thread_id: str):
    pool = get_pool()
    checkpoint=PostgresSaver(pool)
    cp=checkpoint.get(config={"configurable":{"thread_id": thread_id}})
    print(f"Fetching checkpoint: {cp['channel_values']["messages"]}", flush=True)
    return cp["channel_values"]["messages"]


