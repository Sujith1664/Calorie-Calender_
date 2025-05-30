import sqlite3

DATABASE = "database.db"

def initialize_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone INTEGER NOT NULL
        )
    """)
    
    # Create meals table
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone INTEGER NOT NULL,
            meal TEXT NOT NULL,
            quantity INTEGER NOT NULL
        )
    ''')
    
    # Create daily_goals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_goals (
            phone TEXT PRIMARY KEY,
            morning_activity TEXT,
            morning_goal TEXT,
            afternoon_activity TEXT,
            afternoon_goal TEXT,
            evening_activity TEXT,
            evening_goal TEXT,
            night_activity TEXT,
            night_goal TEXT
        )
    """)
    
    # Create calorie_goals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calorie_goals (
            phone TEXT PRIMARY KEY,
            daily_goal INTEGER NOT NULL DEFAULT 2000,
            current_calories INTEGER DEFAULT 0
        )
    """)
    
    # Create weekly_calories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_calories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            date TEXT NOT NULL,
            day_name TEXT NOT NULL,
            calories INTEGER NOT NULL
        )
    """)
    
    # Create exercises table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            calories_burned INTEGER NOT NULL,
            date TEXT NOT NULL
        )
    """)
    
    # Create monthly_goals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_goals (
            phone TEXT PRIMARY KEY,
            target INTEGER NOT NULL DEFAULT 60000
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    initialize_database()


import sqlite3

DATABASE = "database.db"

def initialize_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone INTEGER NOT NULL
        )
    """)
    
    # Create meals table
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone INTEGER NOT NULL,
            meal TEXT NOT NULL,
            quantity INTEGER NOT NULL
        )
    ''')
    
    # Create daily_goals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_goals (
            phone TEXT PRIMARY KEY,
            morning_activity TEXT,
            morning_goal TEXT,
            afternoon_activity TEXT,
            afternoon_goal TEXT,
            evening_activity TEXT,
            evening_goal TEXT,
            night_activity TEXT,
            night_goal TEXT
        )
    """)
    
    # Create calorie_goals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calorie_goals (
            phone TEXT PRIMARY KEY,
            daily_goal INTEGER NOT NULL DEFAULT 2000,
            current_calories INTEGER DEFAULT 0
        )
    """)
    
    # Create weekly_calories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_calories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            date TEXT NOT NULL,
            day_name TEXT NOT NULL,
            calories INTEGER NOT NULL
        )
    """)
    
    # Create exercises table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            calories_burned INTEGER NOT NULL,
            date TEXT NOT NULL
        )
    """)
    
    # Create monthly_goals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_goals (
            phone TEXT PRIMARY KEY,
            target INTEGER NOT NULL DEFAULT 60000
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    initialize_database()