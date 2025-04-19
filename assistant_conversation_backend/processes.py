import asyncio
import psycopg
import calendar
from datetime import datetime, timedelta, time
from .database import DSN

async def process_recurring_tasks():
    """Process all recurring tasks that have task_execute_at in the past and update based on recurrence pattern."""
    try:
        async with await psycopg.AsyncConnection.connect(DSN) as conn:
            async with conn.cursor() as cur:
                # Get all recurring tasks with past execution dates
                await cur.execute("""
                    SELECT task_id, recurrence_type, recurrence_interval, recurrence_days, 
                           recurrence_month_day, task_execute_at
                    FROM tasks
                    WHERE is_recurring = TRUE 
                    AND task_execute_at < NOW()
                    AND is_completed = TRUE
                """)
                
                tasks = await cur.fetchall()
                
                for task in tasks:
                    task_id, rec_type, rec_interval, rec_days, rec_month_day, execute_at = task
                    
                    # Use current date as base for calculations
                    current_date = datetime.now()
                    
                    # Calculate the new execution date based on recurrence pattern
                    new_date = None
                    
                    if rec_type == 'daily':
                        # Use the time from execute_at but date from today
                        new_date = datetime.combine(
                            current_date.date(),
                            time(execute_at.hour, execute_at.minute, execute_at.second)
                        )
                        
                        # If that time has already passed today, move to tomorrow
                        if new_date <= current_date:
                            new_date += timedelta(days=1)
                        
                        # Add the interval for subsequent occurrences
                        if rec_interval > 1:
                            new_date += timedelta(days=rec_interval - 1)
                    
                    elif rec_type == 'weekly':
                        # Get the time component from the original execution date
                        task_time = time(execute_at.hour, execute_at.minute, execute_at.second)
                        
                        if rec_days and isinstance(rec_days, list):
                            # Find the next occurrence from today based on days of week
                            days_checked = 0
                            check_date = current_date.date()
                            
                            while days_checked < 7:  # Check a full week at most
                                # Check if current weekday matches any in recurrence_days
                                if (check_date.weekday() + 1) in rec_days:  # +1 because PostgreSQL is 1-indexed
                                    # Create datetime with the current date and original time
                                    potential_date = datetime.combine(check_date, task_time)
                                    
                                    # If it's later than now, we found our date
                                    if potential_date > current_date:
                                        new_date = potential_date
                                        break
                                
                                # Move to next day
                                check_date += timedelta(days=1)
                                days_checked += 1
                            
                            # If no valid date found in the next week, use the first recurrence day
                            if not new_date:
                                # Find the first recurrence day in the next week
                                sorted_days = sorted(rec_days)
                                target_weekday = sorted_days[0] - 1  # Convert to 0-indexed
                                
                                # Calculate days until the next occurrence of target_weekday
                                days_until = (target_weekday - current_date.weekday()) % 7
                                if days_until == 0:  # Same day, but time already passed
                                    days_until = 7
                                
                                next_date = current_date.date() + timedelta(days=days_until)
                                new_date = datetime.combine(next_date, task_time)
                        else:
                            # Default to recurring every N weeks from now
                            days_in_week = 7
                            new_date = datetime.combine(
                                current_date.date() + timedelta(days=days_in_week * rec_interval),
                                task_time
                            )
                    
                    elif rec_type == 'monthly':
                        # Get the day to use (either specified day or same as original)
                        target_day = rec_month_day if rec_month_day else execute_at.day
                        
                        # Get the time from the original execution
                        task_time = time(execute_at.hour, execute_at.minute, execute_at.second)
                        
                        # Try for current month first if day hasn't passed
                        current_month_date = None
                        try:
                            # Check if the target day in current month is still in the future
                            candidate = datetime(
                                current_date.year, current_date.month, target_day,
                                execute_at.hour, execute_at.minute, execute_at.second
                            )
                            if candidate > current_date:
                                current_month_date = candidate
                        except ValueError:
                            # Day might be invalid for current month (e.g., Feb 30)
                            pass
                        
                        if current_month_date:
                            new_date = current_month_date
                        else:
                            # Move to next month (or months based on interval)
                            target_month = current_date.month + rec_interval
                            target_year = current_date.year
                            
                            # Adjust if we crossed into a new year
                            while target_month > 12:
                                target_month -= 12
                                target_year += 1
                            
                            # Make sure the day is valid for the target month
                            last_day = calendar.monthrange(target_year, target_month)[1]
                            valid_day = min(target_day, last_day)
                            
                            # Create the new date
                            new_date = datetime(
                                target_year, target_month, valid_day,
                                execute_at.hour, execute_at.minute, execute_at.second
                            )
                    
                    elif rec_type == 'yearly':
                        # Get the time from the original execution
                        task_time = time(execute_at.hour, execute_at.minute, execute_at.second)
                        
                        # Check if this year's date has passed
                        this_year_date = None
                        try:
                            candidate = datetime(
                                current_date.year, execute_at.month, execute_at.day,
                                execute_at.hour, execute_at.minute, execute_at.second
                            )
                            if candidate > current_date:
                                this_year_date = candidate
                        except ValueError:
                            # Date might be invalid for current year (e.g., Feb 29 in non-leap year)
                            pass
                        
                        if this_year_date:
                            new_date = this_year_date
                        else:
                            # Calculate next occurrence based on interval
                            target_year = current_date.year + rec_interval
                            
                            # Handle leap year issues
                            if execute_at.month == 2 and execute_at.day == 29:
                                # Check if target year is a leap year
                                if calendar.isleap(target_year):
                                    day = 29
                                else:
                                    day = 28
                            else:
                                day = execute_at.day
                            
                            new_date = datetime(
                                target_year, execute_at.month, day,
                                execute_at.hour, execute_at.minute, execute_at.second
                            )
                    
                    elif rec_type == 'custom':
                        # For custom, we'd need specific logic based on your requirements
                        # Using a simple daily recurrence from current date as fallback
                        task_time = time(execute_at.hour, execute_at.minute, execute_at.second)
                        new_date = datetime.combine(current_date.date() + timedelta(days=1), task_time)
                    
                    # If we couldn't calculate a new date, skip this task
                    if not new_date:
                        print(f"Could not calculate new date for task {task_id}, skipping.")
                        continue
                    
                    # Update the task
                    await cur.execute("""
                        UPDATE tasks
                        SET task_execute_at = %s,
                            is_completed = FALSE,
                            task_completed_at = NULL,
                            task_status = 'scheduled'
                        WHERE task_id = %s
                    """, (new_date, task_id))
                
                # Commit all changes
                await conn.commit()
                print(f"Processed {len(tasks)} recurring tasks")
                
    except Exception as e:
        print(f"Error processing recurring tasks: {e}")

async def schedule_recurring_task_processor():
    """Schedule the recurring task processor to run at 00:01 every day."""
    while True:
        # Run the task processor immediately
        print("Running recurring task processor...")
        await process_recurring_tasks()
        
        # Calculate time until next run (00:01)
        now = datetime.now()
        target_time = datetime.combine(now.date() + timedelta(days=1), time(0, 1))
        seconds_until_target = (target_time - now).total_seconds()
        
        print(f"Next recurring task processor run in {seconds_until_target} seconds")
        
        # Wait until target time
        await asyncio.sleep(seconds_until_target)