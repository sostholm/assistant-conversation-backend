import psycopg
import os
import logging
from datetime import datetime
from .data_models import Message, AI, Device
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_ADDRESS = os.getenv("DATABASE_ADDRESS", "192.168.0.218")
DATABASE_NAME = os.getenv("DATABASE_NAME", "assistant_v3")
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
CREATE TABLE IF NOT EXISTS user_devices (
    user_id CHAR(26) REFERENCES users(user_id),
    device_id INTEGER REFERENCES devices(id),
    PRIMARY KEY (user_id, device_id)
);
""")


cur.execute("""
--sql
CREATE TABLE IF NOT EXISTS voice_recognition (
    voice_recognition_id SERIAL PRIMARY KEY,
    user_id CHAR(26) REFERENCES users(user_id),
    ai_id INTEGER REFERENCES ai(ai_id),
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
    task_short_description VARCHAR(255),
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


# Commit the transaction
conn.commit()


async def get_users_by_nicknames(conn: psycopg.AsyncConnection, nicknames: list[str]) -> list:
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM users
                WHERE nick_name = ANY(%s)
                """,
                (nicknames,)
            )

            users = await cur.fetchall()
            logger.info("Fetched %d users by nicknames: %s", len(users), nicknames)
            return users

    except psycopg.Error as e:
        logger.error("Error occurred while fetching the users by nicknames: %s", e)
        return []

async def store_message(message: str) -> None:
    try:
        async with await psycopg.AsyncConnection.connect(DSN) as conn:
            async with conn.cursor() as cur:
                # Get valid user IDs from the database
                # Store in database
                await cur.execute(
                    """
                    INSERT INTO messages (content)
                    VALUES (%s)
                    """,
                    (
                        message,
                    )
                )

            # Commit the transaction
            await conn.commit()
            logger.info("Message stored successfully: %s", message)
    except psycopg.Error as e:
        logger.error("Error occurred while storing the message: %s", e)



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
            logger.info("Fetched AI with ID: %s", ai_id)
            return AI(ai_id=ai[0], ai_name=ai[1], ai_base_prompt=ai[2])
        else:
            logger.warning("No AI found with ID: %s", ai_id)
            return None

    except psycopg.Error as e:
        logger.error("Error occurred while fetching the AI: %s", e)
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
                (n,)
            )

            rows = await cur.fetchall()
            logger.info("Fetched the last %d messages", n)
            return [
                Message(
                    message_id=row[0],
                    date_sent=row[1],
                    content=row[2]
                )
                for row in rows
            ]

    except psycopg.Error as e:
        logger.error("Error occurred while fetching the messages: %s", e)
        return []


@dataclass
class UserProfile:
    user_id: str
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
                SELECT u.user_id, u.full_name, u.nick_name, u.email, u.phone_number, u.character_sheet, u.life_style_and_preferences, ur.role_name, ur.role_description
                FROM users u
                LEFT JOIN user_roles ur ON u.user_role_id = ur.role_id
                """
            )

            rows = await cur.fetchall()
            logger.info("Fetched %d user profiles", len(rows))
            return [
                UserProfile(
                    user_id=row[0],
                    full_name=row[1],
                    nick_name=row[2],
                    email=row[3],
                    phone_number=row[4],
                    character_sheet=row[5],
                    life_style_and_preferences=row[6],
                    role_name=row[7],
                    role_description=row[8]
                )
                for row in rows
            ]
    except psycopg.Error as e:
        logger.error("Error occurred while fetching all users and their profiles: %s", e)
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
            logger.info("Fetched %d devices", len(rows))
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
        logger.error("Error occurred while fetching all devices: %s", e)
        return []


# Get all tasks for the next 24 hours

@dataclass
class Task:
    task_id: str
    task_type_id: int
    task_started_for: str
    task_started_by: int
    task_short_description: str
    task_description: str
    task_status: str
    task_log: str
    task_started_at: datetime
    task_completed_at: datetime
    task_execute_at: datetime
    is_completed: bool

async def get_tasks_for_next_24_hours(conn: psycopg.AsyncConnection) -> list[Task]:
    
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM tasks
                WHERE task_execute_at BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
                AND task_completed_at IS NULL
                """
            )

            rows = await cur.fetchall()
            logger.info("Fetched %d tasks for the next 24 hours", len(rows))
            return [
                Task(
                    task_id=row[0],
                    task_type_id=row[1],
                    task_started_for=row[2],
                    task_started_by=row[3],
                    task_short_description=row[4],
                    task_description=row[5],
                    task_status=row[6],
                    task_log=row[7],
                    task_started_at=row[8],
                    task_completed_at=row[9],
                    task_execute_at=row[10],
                    is_completed=row[11]
                )
                for row in rows
            ]
    except psycopg.Error as e:
        logger.error("Error occurred while fetching tasks for the next 24 hours: %s", e)
        return []


async def get_device_by_id(
    conn: psycopg.AsyncConnection,
    device_id: int
) -> Device:
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, device_name, device_type_id, unique_identifier, ip_address, mac_address, location, status, registered_at, last_seen_at
                FROM devices
                WHERE id = %s
                """,
                (device_id,)
            )
            row = await cur.fetchone()
            if row:
                return Device(*row)
            else:
                return None

    except psycopg.Error as e:
        print("Error occurred while fetching the device.")
        print(e)
        return None