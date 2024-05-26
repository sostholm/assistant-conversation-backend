# from pymongo import MongoClient
# from pymongo.errors import DuplicateKeyError

# # Connect to your MongoDB database
# client = MongoClient('mongodb://192.168.0.218:27017/')
# db = client['assistant_conversation']  # replace with your database name
# conversation_collection = db['conversations']  # replace with your collection name

# A function that inserts a conversation into the database


import psycopg
import os
from dataclasses import dataclass

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
# Connect to your PostgreSQL database
conn = psycopg.connect(
    dbname="assistant",
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host="192.168.0.218",
    port="5432"
)

# Create a cursor object
cur = conn.cursor()

# Define your schema
create_conversations_table_query = """
--sql
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id CHAR(26) PRIMARY KEY
);
"""

create_messages_table_query = """
--sql
CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id CHAR(26) REFERENCES conversations(conversation_id),
    role VARCHAR(50),
    content TEXT
);
"""

create_user_profile_table_query = """
--sql
CREATE TABLE IF NOT EXISTS user_profile (
    user_id CHAR(26) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(20),
    character_sheet TEXT,
    life_style_and_preferences TEXT
);
"""

create_tasks_table_query = """
--sql
CREATE TABLE IF NOT EXISTS tasks (
    task_id CHAR(26) PRIMARY KEY,
    task_description TEXT,
    due_date TIMESTAMP,
    is_completed BOOLEAN
);
"""

create_events_table_query = """
--sql
CREATE TABLE IF NOT EXISTS events (
    event_id CHAR(26) PRIMARY KEY,
    event_title VARCHAR(255),
    event_description TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    location VARCHAR(255)
);
"""

create_shopping_list_table_query = """
--sql
CREATE TABLE IF NOT EXISTS shopping_list (
    item_id CHAR(26) PRIMARY KEY,
    item_name VARCHAR(255),
    quantity INT,
    is_purchased BOOLEAN
);
"""

create_ai_table_query = """
--sql
CREATE TABLE IF NOT EXISTS ai (
    ai_id SERIAL PRIMARY KEY,
    ai_name VARCHAR(255),
    ai_base_prompt TEXT
);
"""

@dataclass
class AI:
    ai_id: int
    ai_name: str
    ai_base_prompt: str

# Execute the queries
cur.execute(create_conversations_table_query)
cur.execute(create_messages_table_query)
cur.execute(create_user_profile_table_query)
cur.execute(create_tasks_table_query)
cur.execute(create_events_table_query)
cur.execute(create_shopping_list_table_query)
cur.execute(create_ai_table_query)

# Commit the transaction
conn.commit()

def add_or_update_conversation(conversation_id, messages):
    try:
        # Insert conversation if it doesn't exist
        cur.execute("""
            INSERT INTO conversations (conversation_id)
            VALUES (%s)
            ON CONFLICT (conversation_id) DO NOTHING
        """, (conversation_id,))

        # Insert messages
        for message in messages:
            cur.execute("""
                INSERT INTO messages (conversation_id, role, content)
                VALUES (%s, %s, %s)
            """, (conversation_id, message['role'], message['content']))

    except psycopg.Error as e:
        print("Error occurred while updating the conversation.")
        print(e)
        return False

    # Commit the transaction
    conn.commit()

    return True

def get_ai(ai_id) -> AI:
    try:
        cur.execute("""
            SELECT * FROM ai
            WHERE ai_id = %s
        """, (ai_id,))

        ai = cur.fetchone()

        if ai:
            return AI(*ai)
        else:
            return None

    except psycopg.Error as e:
        print("Error occurred while fetching the AI.")
        print(e)
        return None