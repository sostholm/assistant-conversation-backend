from typing import List, Optional
from pydantic import BaseModel
from ulid import ULID
from ..database import conn
from datetime import datetime

class GetTasksInput(BaseModel):
    is_completed: Optional[bool] = None
    task_execute_at_start: Optional[datetime] = None  # Changed from due_date_start
    task_execute_at_end: Optional[datetime] = None    # Changed from due_date_end
    task_status: Optional[str] = None                 # Added to match schema

class CreateTaskInput(BaseModel):
    task_short_description: str                      # Changed from task_description
    task_description: Optional[str] = None           # Added field
    task_execute_at: Optional[datetime] = None       # Changed from due_date
    task_type_id: Optional[int] = None
    task_started_for: Optional[str] = None
    task_started_by: Optional[int] = None
    task_status: Optional[str] = "pending"
    is_completed: bool = False

class TaskUpdateInput(BaseModel):
    task_id: str
    task_short_description: Optional[str] = None     # Changed from task_description
    task_description: Optional[str] = None           # Added field
    task_execute_at: Optional[datetime] = None       # Changed from due_date
    task_status: Optional[str] = None
    task_completed_at: Optional[datetime] = None
    is_completed: Optional[bool] = None

def get_tasks(is_completed: Optional[bool]=None, task_execute_at_start: Optional[datetime]=None, 
              task_execute_at_end: Optional[datetime]=None, task_status: Optional[str]=None) -> List[dict]:
    
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
        with conn.cursor() as cur:
            query = "SELECT * FROM tasks"
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            cur.execute(query, params)
            tasks = cur.fetchall()
            return tasks

def create_task(task_short_description: str, task_description: Optional[str]=None, 
                task_execute_at: Optional[datetime]=None, task_type_id: Optional[int]=None,
                task_started_for: Optional[str]=None, task_started_by: Optional[int]=None,
                task_status: str="pending", is_completed: bool=False) -> str:

    """Create a new task in the tasks table."""

    task_id = str(ULID())
    task_started_at = datetime.now()
    
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO tasks (task_id, task_type_id, task_started_for, task_started_by, 
                           task_short_description, task_description, task_status, 
                           task_started_at, task_execute_at, is_completed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING task_id;
        """, (task_id, task_type_id, task_started_for, task_started_by, 
              task_short_description, task_description, task_status, 
              task_started_at, task_execute_at, is_completed))
        task_id = cur.fetchone()[0]
        conn.commit()
        return f"Task created with ID: {task_id}"

def update_task(task_id: str, task_short_description: Optional[str]=None, 
                task_description: Optional[str]=None, task_execute_at: Optional[datetime]=None, 
                task_status: Optional[str]=None, task_completed_at: Optional[datetime]=None,
                is_completed: Optional[bool]=None) -> str:

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
    params.append(task_id)
    with conn.cursor() as cur:
        cur.execute(f"""
        UPDATE tasks
        SET {', '.join(updates)}
        WHERE task_id = %s;
        """, params)
        conn.commit()
        return "Task updated successfully"


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


def get_events(start_date_range: datetime, end_date_range: datetime,event_title: Optional[str]=None,  location: Optional[str]=None) -> List[dict]:
    
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
        with conn.cursor() as cur:
            cur.execute(f"""
            SELECT * FROM events
            WHERE {' AND '.join(where_clauses)};
            """, params)
            events = cur.fetchall()
            return events

def create_event(event_title: str, event_description: str, start_time: datetime, end_time: datetime, location: str) -> str:

    """Create a new event in the events table."""

    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO events (event_id, event_title, event_description, start_time, end_time, location)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING event_id;
        """, (str(ULID()), event_title, event_description, start_time, end_time, location))
        event_id = cur.fetchone()[0]
        conn.commit()
        return f"Event created with ID: {event_id}"

class GetShoppingListInput(BaseModel):
    is_purchased: Optional[bool] = None

class AddShoppingItemInput(BaseModel):
    item_name: str
    quantity: int

def get_shopping_list(is_purchased: Optional[bool] = None) -> List[dict]:
    
        """Fetch shopping items from the shopping list based on the provided filters."""
    
        params = []
        where_clauses = []
        if is_purchased is not None:
            where_clauses.append("is_purchased = %s")
            params.append(is_purchased)
        with conn.cursor() as cur:
            cur.execute(f"""
            SELECT * FROM shopping_list
            {('WHERE' + ' AND '.join(where_clauses)) if is_purchased is not None else ''};
            """, params)
            shopping_list = cur.fetchall()
            return shopping_list

def add_shopping_item(item_name: str, quantity: int) -> str:

    """Add a new item to the shopping list."""

    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO shopping_list (item_id, item_name, quantity, is_purchased)
        VALUES (%s, %s, %s, FALSE)
        RETURNING item_id;
        """, (str(ULID()), item_name, quantity))
        item_id = cur.fetchone()[0]
        conn.commit()
        return f"Shopping item added with ID: {item_id}"
