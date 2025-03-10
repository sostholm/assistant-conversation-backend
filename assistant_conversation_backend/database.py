import psycopg
import os
from datetime import datetime
from .data_models import Message, AI, Device
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
    conversation_id CHAR(26) PRIMARY KEY,
    summary TEXT
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
CREATE TABLE IF NOT EXISTS users (
    user_id CHAR(26) PRIMARY KEY,
    user_profile_id INTEGER REFERENCES user_profile(user_profile_id)
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
    CREATE INDEX IF NOT EXISTS idx_articles_embedding ON articles USING hnsw (embedding vector_ip_ops);
    --sql
    CREATE INDEX IF NOT EXISTS idx_questions_embedding ON questions USING hnsw (embedding vector_ip_ops);
    """
)

# Create default roles if they don't exist
cur.execute("""
--sql
INSERT INTO user_roles (role_name, role_description)
VALUES 
('admin', 'Admin role, have all the permissions'),
('user', 'User role, have limited permissions'),
('guest', 'Guest role, have very limited permissions')
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

async def store_message(message: str) -> None:
    message_datetime = datetime.now()
    database_message = Message(date_sent=message_datetime, content=message)
    
    async with await psycopg.AsyncConnection.connect(DSN) as conn:
        async with conn.cursor() as cur:
            # Get valid user IDs from the database
            # Convert message to Message object
            # Store in database
            await cur.execute(
                """
                INSERT INTO messages (date_sent, content)
                VALUES (%s, %s)
                """,
                (
                    database_message.date_sent,
                    database_message.content,
                )
            )

        # Commit the transaction
        await conn.commit()



async def get_ai(ai_id, conn) -> AI:
    try:
        async with conn.cursor() as cur:
            # Fetch the AI from the database
            await cur.execute("""
                SELECT * FROM ai
                WHERE ai_id = %s
            """, (ai_id,))

            ai = await cur.fetchone()

        if ai:
            return AI(ai_id=ai[0], ai_name=ai[1], ai_base_prompt=ai[2])
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
                SELECT message_id, date_sent, content
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


@dataclass
class UserProfile:
    user_id: str
    user_type_id: int
    user_profile_id: int
    full_name: str
    nick_name: str
    email: str
    phone_number: str
    character_sheet: str
    life_style_and_preferences: str
    role_name: str
    role_description: str

async def get_all_users_and_profiles(conn: psycopg.AsyncConnection) -> list[UserProfile]:
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT u.user_id, u.user_type_id, up.user_profile_id, up.full_name, up.nick_name, up.email, up.phone_number, up.character_sheet, up.life_style_and_preferences, ur.role_name, ur.role_description
                FROM users u
                LEFT JOIN user_profile up ON u.user_profile_id = up.user_profile_id
                LEFT JOIN user_roles ur ON up.user_role_id = ur.role_id
                """
            )

            rows = await cur.fetchall()
            return [
                UserProfile(
                    user_id=row[0],
                    user_type_id=row[1],
                    user_profile_id=row[2],
                    full_name=row[3],
                    nick_name=row[4],
                    email=row[5],
                    phone_number=row[6],
                    character_sheet=row[7],
                    life_style_and_preferences=row[8],
                    role_name=row[9],
                    role_description=row[10]
                )
                for row in rows
            ]
    except psycopg.Error as e:
        print("Error occurred while fetching all users and their profiles.")
        print(e)
        return []

# Get all devices

async def get_all_devices(conn: psycopg.AsyncConnection) -> list[Device]:
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM devices
                """
            )

            rows = await cur.fetchall()
            return [
                Device(
                    id=row[0],
                    device_name=row[1],
                    device_type_id=row[2],
                    unique_identifier=row[3],
                    ip_address=row[4],
                    mac_address=row[5],
                    location=row[6],
                    status=row[7],
                    registered_at=row[8],
                    last_seen_at=row[9]
                )
                for row in rows
            ]
    except psycopg.Error as e:
        print("Error occurred while fetching all devices.")
        print(e)
        return []