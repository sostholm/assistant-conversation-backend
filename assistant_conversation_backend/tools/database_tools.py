from typing import Optional, List, Union
from pydantic import BaseModel
from ulid import ULID
from ..database import DSN
import psycopg
from datetime import datetime

# Database connection utilities
async def get_connection():
    return await psycopg.AsyncConnection.connect(DSN)

# Models remain the same
class GetTasksInput(BaseModel):
    is_completed: Optional[bool] = None
    task_execute_at_start: Optional[datetime] = None  # Changed from due_date_start
    task_execute_at_end: Optional[datetime] = None    # Changed from due_date_end
    task_status: Optional[str] = None                 # Added to match schema
    is_recurring: Optional[bool] = None               # Added for recurring tasks

class CreateTaskInput(BaseModel):
    task_short_description: str                      # Changed from task_description
    task_description: Optional[str] = None           # Added field
    task_execute_at: Optional[datetime] = None       # Changed from due_date
    task_type_id: Optional[int] = None
    task_started_for: Optional[str] = None
    task_started_by: Optional[int] = None
    task_status: Optional[str] = "pending"
    task_log: Optional[str] = None                   # Added field
    is_completed: bool = False
    is_recurring: bool = False                       # Added for recurring tasks
    recurrence_type: Optional[str] = None            # Added field
    recurrence_interval: Optional[int] = None        # Added field
    recurrence_days: Optional[List[int]] = None      # Added field
    recurrence_month_day: Optional[int] = None       # Added field
    recurrence_end_type: Optional[str] = None        # Added field
    recurrence_end_date: Optional[datetime] = None   # Added field
    recurrence_end_count: Optional[int] = None       # Added field
    parent_task_id: Optional[str] = None             # Added field

class TaskUpdateInput(BaseModel):
    task_id: str
    task_short_description: Optional[str] = None     # Changed from task_description
    task_description: Optional[str] = None           # Added field
    task_execute_at: Optional[datetime] = None       # Changed from due_date
    task_status: Optional[str] = None
    task_log: Optional[str] = None                   # Added field
    task_completed_at: Optional[datetime] = None
    is_completed: Optional[bool] = None
    is_recurring: Optional[bool] = None              # Added for recurring tasks
    recurrence_type: Optional[str] = None            # Added field
    recurrence_interval: Optional[int] = None        # Added field
    recurrence_days: Optional[List[int]] = None      # Added field
    recurrence_month_day: Optional[int] = None       # Added field
    recurrence_end_type: Optional[str] = None        # Added field
    recurrence_end_date: Optional[datetime] = None   # Added field
    recurrence_end_count: Optional[int] = None       # Added field
    parent_task_id: Optional[str] = None             # Added field

async def get_tasks(is_completed: Optional[bool]=None, task_execute_at_start: Optional[datetime]=None, 
              task_execute_at_end: Optional[datetime]=None, task_status: Optional[str]=None,
              is_recurring: Optional[bool]=None) -> list[dict]:
    
    """Fetch tasks from the tasks table based on the provided filters."""
    
    params = []
    where_clauses = []
    if is_completed is not None:
        where_clauses.append("is_completed = %s")
        params.append(is_completed)
    if task_execute_at_start is not None:
        where_clauses.append("task_execute_at >= %s")
        params.append(task_execute_at_start)
    if task_execute_at_end is not None:
        where_clauses.append("task_execute_at <= %s")
        params.append(task_execute_at_end)
    if task_status is not None:
        where_clauses.append("task_status = %s")
        params.append(task_status)
    if is_recurring is not None:
        where_clauses.append("is_recurring = %s")
        params.append(is_recurring)
        
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            query = "SELECT * FROM tasks"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            await cur.execute(query, params)
            tasks = await cur.fetchall()
            return tasks

async def create_task(task_short_description: str, task_description: Optional[str]=None, 
                task_execute_at: Optional[datetime]=None, task_type_id: Optional[int]=None,
                task_started_for: Optional[str]=None, task_started_by: Optional[int]=None,
                task_status: str="pending", task_log: Optional[str]=None,
                is_completed: bool=False, is_recurring: bool=False,
                recurrence_type: Optional[str]=None, recurrence_interval: Optional[int]=None,
                recurrence_days: Optional[List[int]]=None, recurrence_month_day: Optional[int]=None,
                recurrence_end_type: Optional[str]=None, recurrence_end_date: Optional[datetime]=None,
                recurrence_end_count: Optional[int]=None, parent_task_id: Optional[str]=None) -> str:

    """Create a new task in the tasks table."""

    task_id = str(ULID())
    task_started_at = datetime.now()
    
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
            INSERT INTO tasks (task_id, task_type_id, task_started_for, task_started_by, 
                            task_short_description, task_description, task_status, task_log,
                            task_started_at, task_execute_at, is_completed,
                            is_recurring, recurrence_type, recurrence_interval, recurrence_days,
                            recurrence_month_day, recurrence_end_type, recurrence_end_date,
                            recurrence_end_count, parent_task_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING task_id;
            """, (task_id, task_type_id, task_started_for, task_started_by, 
                task_short_description, task_description, task_status, task_log,
                task_started_at, task_execute_at, is_completed,
                is_recurring, recurrence_type, recurrence_interval, recurrence_days,
                recurrence_month_day, recurrence_end_type, recurrence_end_date,
                recurrence_end_count, parent_task_id))
            result = await cur.fetchone()
            task_id = result[0]
            await conn.commit()
            return f"Task created with ID: {task_id}"

async def update_task(task_id: str, task_short_description: Optional[str]=None, 
                task_description: Optional[str]=None, task_execute_at: Optional[datetime]=None, 
                task_status: Optional[str]=None, task_log: Optional[str]=None,
                task_completed_at: Optional[datetime]=None, is_completed: Optional[bool]=None,
                is_recurring: Optional[bool]=None, recurrence_type: Optional[str]=None,
                recurrence_interval: Optional[int]=None, recurrence_days: Optional[List[int]]=None,
                recurrence_month_day: Optional[int]=None, recurrence_end_type: Optional[str]=None,
                recurrence_end_date: Optional[datetime]=None, recurrence_end_count: Optional[int]=None,
                parent_task_id: Optional[str]=None) -> str:

    """Update a task in the tasks table."""

    updates = []
    params = []
    if task_short_description is not None:
        updates.append("task_short_description = %s")
        params.append(task_short_description)
    if task_description is not None:
        updates.append("task_description = %s")
        params.append(task_description)
    if task_execute_at is not None:
        updates.append("task_execute_at = %s")
        params.append(task_execute_at)
    if task_status is not None:
        updates.append("task_status = %s")
        params.append(task_status)
    if task_log is not None:
        updates.append("task_log = %s")
        params.append(task_log)
    if task_completed_at is not None:
        updates.append("task_completed_at = %s")
        params.append(task_completed_at)
    if is_completed is not None:
        updates.append("is_completed = %s")
        params.append(is_completed)
        # If task is being marked as completed and no completion time is provided
        if is_completed and task_completed_at is None:
            updates.append("task_completed_at = %s")
            params.append(datetime.now())
    if is_recurring is not None:
        updates.append("is_recurring = %s")
        params.append(is_recurring)
    if recurrence_type is not None:
        updates.append("recurrence_type = %s")
        params.append(recurrence_type)
    if recurrence_interval is not None:
        updates.append("recurrence_interval = %s")
        params.append(recurrence_interval)
    if recurrence_days is not None:
        updates.append("recurrence_days = %s")
        params.append(recurrence_days)
    if recurrence_month_day is not None:
        updates.append("recurrence_month_day = %s")
        params.append(recurrence_month_day)
    if recurrence_end_type is not None:
        updates.append("recurrence_end_type = %s")
        params.append(recurrence_end_type)
    if recurrence_end_date is not None:
        updates.append("recurrence_end_date = %s")
        params.append(recurrence_end_date)
    if recurrence_end_count is not None:
        updates.append("recurrence_end_count = %s")
        params.append(recurrence_end_count)
    if parent_task_id is not None:
        updates.append("parent_task_id = %s")
        params.append(parent_task_id)
        
    params.append(task_id)
    
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"""
            UPDATE tasks
            SET {', '.join(updates)}
            WHERE task_id = %s;
            """, params)
            await conn.commit()
            return "Task updated successfully"

async def complete_task(task_id: str) -> str:
    """
    Simple helper function to mark a task as completed.
    
    Args:
        task_id: The ID of the task to mark as completed
        
    Returns:
        A string message indicating the task was completed
    """
    # Use update_task function to mark the task as completed
    current_time = datetime.now()
    return await update_task(
        task_id=task_id,
        is_completed=True,
        task_completed_at=current_time,
        task_status="completed"
    )

async def create_daily_greeting_task(
    task_execute_at: datetime, 
    task_started_for: str = None,
    task_started_by: int = None
) -> str:
    """
    Create a daily recurring task for greeting Sam with weather and news.
    
    Args:
        task_execute_at: When the task should execute (time of day)
        task_started_for: User ID the task is for (Sam)
        task_started_by: AI ID that started the task
        
    Returns:
        A string message with the created task ID
    """
    return await create_task(
        task_short_description="Morning greeting with weather and news",
        task_description=(
            "Greet Sam with today's weather forecast and share an interesting news item. "
            "Say good morning, provide the current weather and forecast for the day, "
            "and mention one interesting news story that Sam might find relevant."
        ),
        task_execute_at=task_execute_at,
        task_started_for=task_started_for,
        task_started_by=task_started_by,
        is_recurring=True,
        recurrence_type="daily",
        recurrence_interval=1,
        recurrence_end_type="never"
    )

# Event models remain the same
class GetEventInput(BaseModel):
    event_title: Optional[str] = None
    start_date_range: datetime
    end_date_range: datetime
    location: Optional[str] = None

class CreateEventInput(BaseModel):
    event_title: str
    event_description: str
    start_time: datetime
    end_time: datetime
    location: str

class UpdateEventInput(BaseModel):
    event_id: str
    event_title: Optional[str] = None
    event_description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None

async def get_events(start_date_range: datetime, end_date_range: datetime,
              event_title: Optional[str]=None, location: Optional[str]=None) -> list[dict]:
    
    """Fetch events from the events table based on the provided filters."""
    
    params = []
    where_clauses = []
    if event_title is not None:
        where_clauses.append("event_title = %s")
        params.append(event_title)
    where_clauses.append("start_time >= %s")
    params.append(start_date_range)
    where_clauses.append("end_time <= %s")
    params.append(end_date_range)
    if location is not None:
        where_clauses.append("location = %s")
        params.append(location)
        
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            query = "SELECT * FROM events"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            await cur.execute(query, params)
            events = await cur.fetchall()
            return events

async def create_event(event_title: str, event_description: str, start_time: datetime, end_time: datetime, location: str) -> str:

    """Create a new event in the events table."""

    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
            INSERT INTO events (event_id, event_title, event_description, start_time, end_time, location)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING event_id;
            """, (str(ULID()), event_title, event_description, start_time, end_time, location))
            result = await cur.fetchone()
            event_id = result[0]
            await conn.commit()
            return f"Event created with ID: {event_id}"

async def update_event(event_id: str, event_title: Optional[str]=None, event_description: Optional[str]=None,
                start_time: Optional[datetime]=None, end_time: Optional[datetime]=None,
                location: Optional[str]=None) -> str:
    
    """Update an event in the events table."""
    
    updates = []
    params = []
    if event_title is not None:
        updates.append("event_title = %s")
        params.append(event_title)
    if event_description is not None:
        updates.append("event_description = %s")
        params.append(event_description)
    if start_time is not None:
        updates.append("start_time = %s")
        params.append(start_time)
    if end_time is not None:
        updates.append("end_time = %s")
        params.append(end_time)
    if location is not None:
        updates.append("location = %s")
        params.append(location)
        
    params.append(event_id)
    
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"""
            UPDATE events
            SET {', '.join(updates)}
            WHERE event_id = %s;
            """, params)
            await conn.commit()
            return "Event updated successfully"

# Shopping list models remain the same
class GetShoppingListInput(BaseModel):
    is_purchased: Optional[bool] = None

class AddShoppingItemInput(BaseModel):
    item_name: str
    quantity: int

class UpdateShoppingItemInput(BaseModel):
    item_id: str
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    is_purchased: Optional[bool] = None

async def get_shopping_list(is_purchased: Optional[bool] = None) -> list[dict]:
    
    """Fetch shopping items from the shopping list based on the provided filters."""
    
    params = []
    where_clauses = []
    if is_purchased is not None:
        where_clauses.append("is_purchased = %s")
        params.append(is_purchased)
        
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            query = "SELECT * FROM shopping_list"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            await cur.execute(query, params)
            shopping_list = await cur.fetchall()
            return shopping_list

async def add_shopping_item(item_name: str, quantity: int) -> str:

    """Add a new item to the shopping list."""

    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
            INSERT INTO shopping_list (item_id, item_name, quantity, is_purchased)
            VALUES (%s, %s, %s, FALSE)
            RETURNING item_id;
            """, (str(ULID()), item_name, quantity))
            result = await cur.fetchone()
            item_id = result[0]
            await conn.commit()
            return f"Shopping item added with ID: {item_id}"

async def update_shopping_item(item_id: str, item_name: Optional[str]=None, 
                         quantity: Optional[int]=None, is_purchased: Optional[bool]=None) -> str:
    
    """Update a shopping item in the shopping list."""
    
    updates = []
    params = []
    if item_name is not None:
        updates.append("item_name = %s")
        params.append(item_name)
    if quantity is not None:
        updates.append("quantity = %s")
        params.append(quantity)
    if is_purchased is not None:
        updates.append("is_purchased = %s")
        params.append(is_purchased)
        
    params.append(item_id)
    
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"""
            UPDATE shopping_list
            SET {', '.join(updates)}
            WHERE item_id = %s;
            """, params)
            await conn.commit()
            return "Shopping item updated successfully"
