import psycopg
import os
from datetime import datetime
from .data_models import Message, AI
from dataclasses import dataclass

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_ADDRESS = os.getenv("DATABASE_ADDRESS", "192.168.0.218")
DATABASE_NAME = os.getenv("DATABASE_NAME", "assistant_v2")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")

conn = psycopg.connect(
    dbname=DATABASE_NAME,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=DATABASE_ADDRESS,
    port=DATABASE_PORT
)

DSN = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{DATABASE_ADDRESS}:{DATABASE_PORT}/{DATABASE_NAME}"
)

cur = conn.cursor()

# Enable the vector extension
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")


cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id CHAR(26) PRIMARY KEY
    summary TEXT,
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS user_roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(255) UNIQUE,
    role_description TEXT
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS user_profile (
    user_profile_id SERIAL PRIMARY KEY,
    full_name VARCHAR(255),
    nick_name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(20),
    character_sheet TEXT,
    life_style_and_preferences TEXT,
    user_role_id INTEGER REFERENCES user_roles(role_id)
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS ai (
    ai_id SERIAL PRIMARY KEY,
    ai_name VARCHAR(255) UNIQUE,
    ai_base_prompt TEXT
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS tools (
    tool_id SERIAL PRIMARY KEY,
    tool_name VARCHAR(255) UNIQUE,
    tool_description TEXT
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS user_types (
    user_type_id SERIAL PRIMARY KEY,
    user_type_name VARCHAR(255) UNIQUE
);
""")


cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS users (
    user_id CHAR(26) PRIMARY KEY,
    user_type_id INTEGER REFERENCES user_types(user_type_id),
    user_profile_id INTEGER REFERENCES user_profile(user_profile_id),
    ai_profile_id INTEGER REFERENCES ai(ai_id),
    tool_profile_id INTEGER REFERENCES tools(tool_id)
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id CHAR(26) REFERENCES conversations(conversation_id),
    from_user CHAR(26) REFERENCES users(user_id),
    to_user CHAR(26) REFERENCES users(user_id),
    from_device_id INTEGER REFERENCES devices(id),
    date_sent TIMESTAMP DEFAULT NOW(),
    content TEXT
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS device_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    device_name VARCHAR(100) NOT NULL,
    device_type_id INTEGER NOT NULL REFERENCES device_types(id),
    unique_identifier UUID NOT NULL UNIQUE,
    ip_address INET,
    mac_address MACADDR,
    location VARCHAR(100),  -- e.g., 'Living Room', 'Bedroom'
    status VARCHAR(50) DEFAULT 'active',
    registered_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS user_devices (
    user_id INTEGER REFERENCES user_profile(user_profile_id),
    device_id INTEGER REFERENCES devices(id),
    PRIMARY KEY (user_id, device_id)
);
""")


cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS voice_recognition (
    voice_recognition_id SERIAL PRIMARY KEY,
    user_id CHAR(26) REFERENCES users(user_id),
    voice_recognition BYTEA,
    recorded_on INTEGER REFERENCES devices(id)
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS task_types (
    task_type_id SERIAL PRIMARY KEY,
    task_type_name VARCHAR(255) UNIQUE
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS tasks (
    task_id CHAR(26) PRIMARY KEY,
    task_type_id INTEGER REFERENCES task_types(task_type_id),
    task_started_for CHAR(26) REFERENCES users(user_id),
    task_started_by INTEGER REFERENCES ai(ai_id),
    task_description TEXT,
    task_status VARCHAR(50),
    task_log TEXT,
    task_started_at TIMESTAMP,
    task_completed_at TIMESTAMP,
    task_execute_at TIMESTAMP,
    is_completed BOOLEAN
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS events (
    event_id CHAR(26) PRIMARY KEY,
    event_title VARCHAR(255),
    event_description TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    location VARCHAR(255)
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS articles (
    article_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    ts_content TSVECTOR,
    embedding VECTOR(1536)
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS questions (
    question_id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    ts_question TSVECTOR,
    embedding VECTOR(1536)
);
""")

cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS article_questions (
    article_id INTEGER REFERENCES articles(article_id),
    question_id INTEGER REFERENCES questions(question_id),
    PRIMARY KEY (article_id, question_id)
);
""")


cur.execute("""
--sql
CREATE OR REPLACE FUNCTION update_articles_tsvector() RETURNS trigger AS $$
BEGIN
    NEW.ts_content := to_tsvector('english', NEW.title || ' ' || NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")


cur.execute("""
--sql
CREATE OR REPLACE TRIGGER articles_tsvector_trigger
BEFORE INSERT OR UPDATE ON articles
FOR EACH ROW EXECUTE PROCEDURE update_articles_tsvector();
""")

cur.execute("""
--sql
CREATE OR REPLACE FUNCTION update_questions_tsvector() RETURNS trigger AS $$
BEGIN
    NEW.ts_question := to_tsvector('english', NEW.question_text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")

cur.execute("""
--sql
CREATE OR REPLACE TRIGGER questions_tsvector_trigger
BEFORE INSERT OR UPDATE ON questions
FOR EACH ROW EXECUTE PROCEDURE update_questions_tsvector();
""")

# Create full text search indexes

cur.execute(
    """
    --sql
    CREATE INDEX IF NOT EXISTS idx_articles_ts_content ON articles USING GIN(ts_content);
    --sql
    CREATE INDEX IF NOT EXISTS idx_questions_ts_question ON questions USING GIN(ts_question);
    """
)

# Create embeddings indexes

cur.execute(
    """
    --sql
    CREATE INDEX IF NOT EXISTS idx_articles_embedding ON articles USING ivfflat (embedding) WITH (lists = 100);
    --sql
    CREATE INDEX IF NOT EXISTS idx_questions_embedding ON questions USING ivfflat (embedding) WITH (lists = 100);
    """
)

# Create default roles if they don't exist
cur.execute("""
--sql
INSERT INTO user_roles (role_name, role_description)
VALUES 
('admin', 'Admin role, have all the permissions'),
('user', 'User role, have limited permissions'),
('guest', 'Guest role, have very limited permissions'),
('ai', 'AI role, have most of the permissions')
ON CONFLICT (role_name) DO NOTHING;
""")

# Create default user types if they don't exist
cur.execute("""
--sql
INSERT INTO user_types (user_type_name)
VALUES 
('human'),
('ai'),
('tool')
ON CONFLICT (user_type_name) DO NOTHING;
""")


# Commit the transaction
conn.commit()

# def add_or_update_conversation(conversation_id, messages: list[Message]) -> bool:
#     try:
#         # Insert conversation if it doesn't exist
#         cur.execute("""
#             INSERT INTO conversations (conversation_id)
#             VALUES (%s)
#             ON CONFLICT (conversation_id) DO NOTHING
#         """, (conversation_id,))

#         # Insert messages
#         for message in messages:
#             cur.execute("""
#                 INSERT INTO messages (conversation_id, from_user, to_user, date_sent, content)
#                 VALUES (%s, %s, %s, %s)
#             """, (conversation_id, message.from_user, message.to_user, message.date_sent, message.content))

#     except psycopg.Error as e:
#         print("Error occurred while updating the conversation.")
#         print(e)
#         return False

#     # Commit the transaction
#     conn.commit()

#     return True

async def get_users_by_nicknames(conn: psycopg.AsyncConnection, nicknames: list[str]) -> list:
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM user_profile
                WHERE nick_name = ANY(%s)
                """,
                (nicknames,)
            )

            users = await cur.fetchall()
            return users

    except psycopg.Error as e:
        print("Error occurred while fetching the users by nicknames.")
        print(e)
        return []

async def add_or_update_conversation(
    conn: psycopg.AsyncConnection,
    message: Message
) -> bool:
    try:
        async with conn.cursor() as cur:
            # Insert conversation if it doesn't exist
            await cur.execute(
                """
                INSERT INTO conversations (conversation_id)
                VALUES (%s)
                ON CONFLICT (conversation_id) DO NOTHING
                """,
                (message.conversation_id,)
            )

            # Insert messages
            await cur.execute(
                """
                INSERT INTO messages (conversation_id, from_user, to_user, date_sent, content)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    message.conversation_id,
                    message.from_user,
                    message.to_user,
                    message.date_sent,
                    message.content,
                )
            )

        # Commit the transaction
        await conn.commit()
        return True

    except psycopg.Error as e:
        print("Error occurred while updating the conversation.")
        print(e)
        return False

async def store_message(message: str, sender, recipient) -> None:
    message_datetime = datetime.now()
    database_message = Message(from_user=sender.value, to_user=recipient.value, date_sent=message_datetime, content=message)
    
    async with await psycopg.AsyncConnection.connect(DSN) as conn:
        await add_or_update_conversation(conn, database_message)

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

async def get_last_n_messages(conn: psycopg.AsyncConnection, n: int) -> list[Message]:
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT message_id, conversation_id, from_user, to_user, date_sent, content
                FROM messages
                ORDER BY date_sent DESC
                LIMIT %s
                """,
                (n)
            )

            rows = await cur.fetchall()
            return [Message(*row) for row in rows]

    except psycopg.Error as e:
        print("Error occurred while fetching the messages.")
        print(e)
        return []


# async def get_all_users_and_profiles(conn: psycopg.AsyncConnection) -> list:
#     try:
#         async with conn.cursor() as cur:
#             await cur.execute(
#                 """
#                 SELECT u.user_id, u.user_type_id, u.user_profile_id, u.ai_profile_id, u.tool_profile_id,
#                         up.full_name, up.nick_name, up.email, up.phone_number, up.character_sheet, up.life_style_and_preferences,
#                         ur.role_name, ur.role_description,
#                         ai.ai_name, ai.ai_base_prompt,
#                         t.tool_name, t.tool_description,
#                         ut.user_type_name
#                 FROM users u
#                 LEFT JOIN user_profile up ON u.user_profile_id = up.user_profile_id
#                 LEFT JOIN user_roles ur ON up.user_role_id = ur.role_id
#                 LEFT JOIN ai ON u.ai_profile_id = ai.ai_id
#                 LEFT JOIN tools t ON u.tool_profile_id = t.tool_id
#                 LEFT JOIN user_types ut ON u.user_type_id = ut.user_type_id
#                 """
#             )

#             rows = await cur.fetchall()
#             return rows

#     except psycopg.Error as e:
#         print("Error occurred while fetching all users and their profiles.")
#         print(e)
#         return []

@dataclass
class UserProfile:
    user_id: str
    user_type_id: int
    user_profile_id: int
    ai_profile_id: int
    tool_profile_id: int
    full_name: str
    nick_name: str
    email: str
    phone_number: str
    character_sheet: str
    life_style_and_preferences: str
    role_name: str
    role_description: str
    ai_name: str
    ai_base_prompt: str
    tool_name: str
    tool_description: str
    user_type_name: str

async def get_all_users_and_profiles(conn: psycopg.AsyncConnection) -> list[UserProfile]:
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT u.user_id, u.user_type_id, u.user_profile_id, u.ai_profile_id, u.tool_profile_id,
                        up.full_name, up.nick_name, up.email, up.phone_number, up.character_sheet, up.life_style_and_preferences,
                        ur.role_name, ur.role_description,
                        ai.ai_name, ai.ai_base_prompt,
                        t.tool_name, t.tool_description,
                        ut.user_type_name
                FROM users u
                LEFT JOIN user_profile up ON u.user_profile_id = up.user_profile_id
                LEFT JOIN user_roles ur ON up.user_role_id = ur.role_id
                LEFT JOIN ai ON u.ai_profile_id = ai.ai_id
                LEFT JOIN tools t ON u.tool_profile_id = t.tool_id
                LEFT JOIN user_types ut ON u.user_type_id = ut.user_type_id
                """
            )

            rows = await cur.fetchall()
            return [UserProfile(*row) for row in rows]

    except psycopg.Error as e:
        print("Error occurred while fetching all users and their profiles.")
        print(e)
        return []