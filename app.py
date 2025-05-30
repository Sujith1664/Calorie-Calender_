from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import sqlite3
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['SESSION_TYPE'] = 'filesystem'
DATABASE = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone INTEGER NOT NULL,
                meal TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                date TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    else:
        # Check and add missing columns
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(meals)")
        columns = [col[1] for col in cursor.fetchall()]
        if "date" not in columns:
            cursor.execute("ALTER TABLE meals ADD COLUMN date TEXT")
        
        conn.commit()
        conn.close()

def update_calorie_goals_schema():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if the table already has the correct schema
    cursor.execute("PRAGMA table_info(calorie_goals)")
    columns = [col[1] for col in cursor.fetchall()]
    if "date" not in columns:
        # Add the `date` column if it doesn't exist
        cursor.execute("ALTER TABLE calorie_goals ADD COLUMN date TEXT")

    # Update rows with NULL or missing `date` values
    today = datetime.today().strftime('%Y-%m-%d')
    cursor.execute("UPDATE calorie_goals SET date = ? WHERE date IS NULL", (today,))

    # Check if the UNIQUE constraint exists
    cursor.execute("PRAGMA index_list(calorie_goals)")
    indexes = [index[1] for index in cursor.fetchall()]
    if "unique_phone_date" not in indexes:
        # Recreate the table with the UNIQUE constraint
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calorie_goals_new (
                phone INTEGER NOT NULL,
                daily_goal INTEGER NOT NULL,
                current_calories INTEGER NOT NULL,
                date TEXT NOT NULL,
                UNIQUE(phone, date)
            )
        """)
        cursor.execute("""
            INSERT INTO calorie_goals_new (phone, daily_goal, current_calories, date)
            SELECT phone, daily_goal, current_calories, date FROM calorie_goals
        """)
        cursor.execute("DROP TABLE calorie_goals")
        cursor.execute("ALTER TABLE calorie_goals_new RENAME TO calorie_goals")

    conn.commit()
    conn.close()

# Initialize database when app starts
initialize_database()
update_calorie_goals_schema()

@app.route('/')
def home():
    if 'phone' not in session:
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor()
    phone = session.get('phone')
    goals = {}
    calorie_data = {'daily_goal': 2000, 'current_calories': 0}
    recent_meals = []
    recent_exercises = []

    user_id = session.get('user_id')
    if user_id:
        cursor.execute("SELECT username, password, phone FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        username = user[0] if user else ""
        password = user[1] if user else ""
        phone = user[2] if user else ""
    
        # Filter recent meals to show only today's meals, limit to last 5
        today = datetime.today().strftime('%Y-%m-%d')
        cursor.execute(""" 
            SELECT meal, quantity 
            FROM meals 
            WHERE phone = ? AND date = ? 
            ORDER BY id DESC 
            LIMIT 5
        """, (phone, today))
        recent_meals = cursor.fetchall()  
    
        cursor.execute("SELECT * FROM daily_goals WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row:
            goals = {
                'phone': row[0],
                'morning_activity': row[1],
                'morning_goal': row[2],
                'afternoon_activity': row[3],
                'afternoon_goal': row[4],
                'evening_activity': row[5],
                'evening_goal': row[6],
                'night_activity': row[7],
                'night_goal': row[8]
            }
            
        # Fix the query for daily calories
        cursor.execute("""
            SELECT daily_goal, current_calories 
            FROM calorie_goals 
            WHERE phone = ? AND date = ?
        """, (phone, today))
        calorie_result = cursor.fetchone()
        if calorie_result:
            calorie_data = {
                'daily_goal': calorie_result[0],
                'current_calories': calorie_result[1]
            }

        # Fetch recent exercises with date
        cursor.execute("""
            SELECT exercise_name, duration, calories_burned, date 
            FROM exercises
            WHERE phone = ?
            ORDER BY date DESC, id DESC
            LIMIT 5
        """, (phone,))
        recent_exercises = cursor.fetchall()
        
        return render_template("home.html", **goals, username=username, 
                             password=password, recent_meals=recent_meals,
                             calorie_data=calorie_data, recent_exercises=recent_exercises)    
    return render_template("home.html", **goals, calorie_data=calorie_data, recent_exercises=recent_exercises)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        phone = request.form["phone"]
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, phone) VALUES (?, ?, ?)", (username, password, phone))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists!"
        finally:
            conn.close()
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"]
        password = request.form["password"]
        
        # Debugging: print the phone and password input
        print(f"Phone: {phone}, Password: {password}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if phone and password match in database
        cursor.execute("SELECT * FROM users WHERE phone = ? AND password = ?", (phone, password))
        user = cursor.fetchone()
        
        # Debugging: print the user fetched from DB
        print(f"User fetched: {user}")
        
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["phone"] = user["phone"]
            return redirect("/")
        else:
            print("Login failed!")  # Debugging: Check if login fails
            return "Invalid credentials!"
    
    return render_template("login.html")

@app.route('/check_login')
def check_login():
    if 'user' in session:
        print("entered")
        return jsonify({'logged_in': True, 'user_id': session['user_id']})
    else:
        print("time4")
        return jsonify({'logged_in': False})

@app.route('/add-meal', methods=['POST'])
def add_meal():
    meal = request.form['meal']
    quantity = int(request.form['quantity'])
    phone = session["phone"]
    today = datetime.today().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert the meal into the meals table with the date
        cursor.execute("INSERT INTO meals (meal, quantity, phone, date) VALUES (?, ?, ?, ?)", 
                       (meal, quantity, phone, today))
        
        # First check if there's an entry for today
        cursor.execute("""
            SELECT current_calories FROM calorie_goals 
            WHERE phone = ? AND date = ?
        """, (phone, today))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute("""
                UPDATE calorie_goals 
                SET current_calories = current_calories + ?
                WHERE phone = ? AND date = ?
            """, (quantity, phone, today))
        else:
            # Create new entry
            cursor.execute("""
                INSERT INTO calorie_goals (phone, daily_goal, current_calories, date)
                VALUES (?, 2000, ?, ?)
            """, (phone, quantity, today))
        
        # Update weekly calories
        cursor.execute("""
            INSERT INTO weekly_calories (phone, date, calories)
            VALUES (?, ?, ?)
            ON CONFLICT(phone, date) DO UPDATE SET
            calories = calories + ?
        """, (phone, today, quantity, quantity))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

    return redirect('/')

@app.route('/add-exercise', methods=['POST'])
def add_exercise():
    if 'phone' not in session:
        return redirect('/login')

    phone = session['phone']
    exercise_name = request.form['exercise_name']
    duration = int(request.form['duration'])
    calories_burned = int(request.form['calories_burned'])
    date = datetime.today().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO exercises (phone, exercise_name, duration, calories_burned, date)
        VALUES (?, ?, ?, ?, ?)
    """, (phone, exercise_name, duration, calories_burned, date))
    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/set_goals', methods=['POST'])
def set_goals():
    phone = session['phone']
    conn = get_db_connection()
    cursor = conn.cursor()

    if 'clear' in request.form:
        cursor.execute("DELETE FROM daily_goals WHERE phone = ?", (phone,))
        conn.commit()
        return redirect(url_for('home'))

    values = (
        request.form['morning_activity'],
        request.form['morning_goal'],
        request.form['afternoon_activity'],
        request.form['afternoon_goal'],
        request.form['evening_activity'],
        request.form['evening_goal'],
        request.form['night_activity'],
        request.form['night_goal'],
        phone
    )

    cursor.execute(""" 
        INSERT INTO daily_goals ( 
            morning_activity, morning_goal, afternoon_activity, afternoon_goal, 
            evening_activity, evening_goal, night_activity, night_goal, phone 
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) 
        ON CONFLICT(phone) DO UPDATE SET
            morning_activity = excluded.morning_activity,
            morning_goal = excluded.morning_goal,
            afternoon_activity = excluded.afternoon_activity,
            afternoon_goal = excluded.afternoon_goal,
            evening_activity = excluded.evening_activity,
            evening_goal = excluded.evening_goal,
            night_activity = excluded.night_activity,
            night_goal = excluded.night_goal
    """, values)
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/save', methods=['POST'])
def save():
    phone = session.get('phone')
    if not phone:
        return redirect('/login')

    new_username = request.form.get('username')
    new_password = request.form.get('password')
    profile_photo = request.files.get('profile_photo')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get current username and password
    cursor.execute("SELECT username, password FROM users WHERE phone = ?", (phone,))
    current_user = cursor.fetchone()
    current_username = current_user['username'] if current_user else None
    current_password = current_user['password'] if current_user else None

    # Use current values if not changed
    final_username = new_username if new_username else current_username
    final_password = new_password if new_password else current_password

    # Only check for conflict if username is being changed
    if final_username != current_username:
        cursor.execute("SELECT id FROM users WHERE username = ?", (final_username,))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            return "Username already exists! Please choose another username."

    # Handle profile photo upload
    photo_path = None
    if profile_photo and profile_photo.filename != '':
        filename = secure_filename(profile_photo.filename)
        upload_folder = os.path.join('static', 'profile_photos')
        os.makedirs(upload_folder, exist_ok=True)
        photo_path = os.path.join(upload_folder, f"{phone}_{filename}")
        profile_photo.save(photo_path)
        photo_path = photo_path.replace("\\", "/")
        cursor.execute(
            "UPDATE users SET profile_photo = ? WHERE phone = ?",
            (photo_path, phone)
        )

    # Update username and password if changed (but not photo here)
    if final_username != current_username or final_password != current_password:
        cursor.execute(
            "UPDATE users SET username = ?, password = ? WHERE phone = ?",
            (final_username, final_password, phone)
        )

    conn.commit()
    conn.close()

    return redirect('/')

@app.route("/logout")
def logout():
    session.clear()
    session.pop("phone", None)
    return redirect("/")

@app.route('/set_calorie_goal', methods=['POST'])
def set_calorie_goal():
    phone = session.get('phone')
    if not phone:
        return redirect('/login')
    
    daily_goal = int(request.form.get('daily_goal', 2000))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(""" 
        INSERT INTO calorie_goals (phone, daily_goal, current_calories) 
        VALUES (?, ?, (SELECT COALESCE(current_calories, 0) FROM calorie_goals WHERE phone = ?)) 
        ON CONFLICT(phone) DO UPDATE SET 
        daily_goal = excluded.daily_goal 
    """, (phone, daily_goal, phone))
    
    conn.commit()
    conn.close()
    
    return redirect('/')

@app.route('/clear_calorie_data', methods=['POST'])
def clear_calorie_data():
    if 'phone' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        calories_to_remove = int(data.get('calories_to_remove', 0))
        phone = session['phone']
        today = datetime.today().strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update daily calories
        cursor.execute("""
            UPDATE calorie_goals 
            SET current_calories = MAX(0, COALESCE(current_calories, 0) - ?) 
            WHERE phone = ?
        """, (calories_to_remove, phone))
        
        # Update weekly calories for today
        cursor.execute("""
            UPDATE weekly_calories 
            SET calories = MAX(0, calories - ?) 
            WHERE phone = ? AND date = ?
        """, (calories_to_remove, phone, today))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Calories removed successfully'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': 'Error occurred'}), 500

@app.route('/api/weekly-calories')
def get_weekly_calories():
    if 'phone' not in session:
        return jsonify({
            'days': [],
            'calories_intake': [],
            'calories_burned': []
        })

    phone = session['phone']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get dates for the current week (Monday to Sunday)
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    dates = [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    day_names = [(monday + timedelta(days=i)).strftime('%a, %d') for i in range(7)]

    # Initialize data arrays
    calories_intake = [0] * 7
    calories_burned = [0] * 7

    # Get calories intake
    cursor.execute("""
        SELECT date, SUM(calories) as total_calories
        FROM weekly_calories
        WHERE phone = ? AND date >= ? AND date <= ?
        GROUP BY date
    """, (phone, dates[0], dates[-1]))
    
    for row in cursor.fetchall():
        try:
            index = dates.index(row[0])
            calories_intake[index] = row[1]
        except ValueError:
            continue

    # Get calories burned
    cursor.execute("""
        SELECT date, SUM(calories_burned) as total_burned
        FROM exercises
        WHERE phone = ? AND date >= ? AND date <= ?
        GROUP BY date
    """, (phone, dates[0], dates[-1]))
    
    for row in cursor.fetchall():
        try:
            index = dates.index(row[0])
            calories_burned[index] = row[1]
        except ValueError:
            continue

    conn.close()

    return jsonify({
        'days': day_names,
        'calories_intake': calories_intake,
        'calories_burned': calories_burned
    })

@app.route('/api/user-stage')
def get_user_stage():
    if 'phone' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    phone = session['phone']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last 30 days of data
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    
    # Get calorie intake consistency
    cursor.execute("""
        SELECT COUNT(DISTINCT date) as active_days,
               AVG(calories) as avg_calories
        FROM weekly_calories 
        WHERE phone = ? AND date >= ?
    """, (phone, thirty_days_ago.strftime('%Y-%m-%d')))
    calorie_stats = cursor.fetchone()
    
    # Get exercise consistency
    cursor.execute("""
        SELECT COUNT(DISTINCT date) as exercise_days,
               AVG(calories_burned) as avg_burned
        FROM exercises 
        WHERE phone = ? AND date >= ?
    """, (phone, thirty_days_ago.strftime('%Y-%m-%d')))
    exercise_stats = cursor.fetchone()
    
    conn.close()
    
    # Calculate stage based on activity
    active_days = calorie_stats[0] if calorie_stats[0] else 0
    exercise_days = exercise_stats[0] if exercise_stats[0] else 0
    avg_calories = calorie_stats[1] if calorie_stats[1] else 0
    avg_burned = exercise_stats[1] if exercise_stats[1] else 0
    
    # Define stage criteria
    stages = {
        'Beginner': 'Just starting your health journey',
        'Consistent Tracker': 'Regularly tracking meals and exercises',
        'Active Achiever': 'Maintaining balanced diet and exercise routine',
        'Health Champion': 'Exceptional dedication to health goals',
        'Wellness Master': 'Mastered the art of healthy living'
    }
    
    # Determine user's stage
    if active_days < 7:
        current_stage = 'Beginner'
    elif active_days < 14:
        current_stage = 'Consistent Tracker'
    elif active_days < 21:
        current_stage = 'Active Achiever'
    elif active_days < 28:
        current_stage = 'Health Champion'
    else:
        current_stage = 'Wellness Master'
    
    return jsonify({
        'stage': current_stage,
        'description': stages[current_stage],
        'stats': {
            'active_days': active_days,
            'exercise_days': exercise_days,
            'avg_calories': round(avg_calories, 2),
            'avg_burned': round(avg_burned, 2)
        }
    })

@app.route('/api/average-calories')
def get_average_calories():
    if 'phone' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    phone = session['phone']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get average daily calories for the last 30 days
    cursor.execute("""
        SELECT AVG(calories) as avg_calories
        FROM weekly_calories 
        WHERE phone = ? 
        AND date >= date('now', '-30 days')
    """, (phone,))
    avg_calories = cursor.fetchone()[0] or 0
    
    # Get average daily calories burned for the last 30 days
    cursor.execute("""
        SELECT AVG(calories_burned) as avg_burned
        FROM exercises 
        WHERE phone = ? 
        AND date >= date('now', '-30 days')
    """, (phone,))
    avg_burned = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return jsonify({
        'avg_calories': round(avg_calories, 2),
        'avg_burned': round(avg_burned, 2)
    })
@app.route('/schedule')
def schedule():
    phone = session.get('phone')
    if not phone:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM daily_goals WHERE phone = ?", (phone,))
    row = cursor.fetchone()

    schedule_data = {
        'morning': {'activity': row['morning_activity'], 'goal': row['morning_goal']} if row else {'activity': '', 'goal': ''},
        'afternoon': {'activity': row['afternoon_activity'], 'goal': row['afternoon_goal']} if row else {'activity': '', 'goal': ''},
        'evening': {'activity': row['evening_activity'], 'goal': row['evening_goal']} if row else {'activity': '', 'goal': ''},
        'night': {'activity': row['night_activity'], 'goal': row['night_goal']} if row else {'activity': '', 'goal': ''}
    }

    conn.close()
    return render_template('schedule.html', schedule=schedule_data)


@app.route('/api/monthly-progress', methods=['GET'])
def monthly_progress():
    if 'phone' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    phone = session['phone']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current month's calories gained
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute("""
        SELECT COALESCE(SUM(calories), 0) as total_calories
        FROM weekly_calories 
        WHERE phone = ? AND strftime('%Y-%m', date) = ?
    """, (phone, current_month))
    total_calories = cursor.fetchone()[0] or 0
    
    # Get the number of active days (days with logged data)
    cursor.execute("""
        SELECT COUNT(DISTINCT date) as active_days
        FROM weekly_calories
        WHERE phone = ? AND strftime('%Y-%m', date) = ?
    """, (phone, current_month))
    active_days = cursor.fetchone()[0] or 0
    
    # Calculate average daily calories
    avg_daily_calories = total_calories / active_days if active_days > 0 else 0
    
    # Get current month's calories burned
    cursor.execute("""
        SELECT COALESCE(SUM(calories_burned), 0) as total_burned
        FROM exercises 
        WHERE phone = ? AND strftime('%Y-%m', date) = ?
    """, (phone, current_month))
    total_burned = cursor.fetchone()[0] or 0
    
    # Process data for the chart
    dates = []
    daily_calories = []
    daily_burned = []
    
    # Get all dates in the current month
    current_date = datetime.now()
    first_day = current_date.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    date_range = [(first_day + timedelta(days=x)).strftime('%Y-%m-%d') 
                 for x in range((last_day - first_day).days + 1)]
    
    # Initialize data arrays with zeros
    cursor.execute("""
        SELECT date, SUM(calories) as total_calories
        FROM weekly_calories
        WHERE phone = ? AND date BETWEEN ? AND ?
        GROUP BY date
    """, (phone, date_range[0], date_range[-1]))
    calories_dict = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute("""
        SELECT date, SUM(calories_burned) as total_burned
        FROM exercises
        WHERE phone = ? AND date BETWEEN ? AND ?
        GROUP BY date
    """, (phone, date_range[0], date_range[-1]))
    burned_dict = {row[0]: row[1] for row in cursor.fetchall()}
    
    for date in date_range:
        dates.append(date)
        daily_calories.append(calories_dict.get(date, 0))
        daily_burned.append(burned_dict.get(date, 0))
    
    conn.close()
    
    return jsonify({
        'calories_gained': total_calories,
        'avg_daily_calories': round(avg_daily_calories, 2),
        'calories_burned': total_burned,
        'chart_data': {
            'dates': dates,
            'calories': daily_calories,
            'burned': daily_burned
        }
    })

@app.route('/activity-history')
def activity_history():
    if 'phone' not in session:
        return redirect('/login')
        
    phone = session['phone']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the current week's Monday and Sunday
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    # Get all exercises for the current week grouped by day of the week
    cursor.execute(""" 
        WITH RankedExercises AS (
            SELECT 
                exercise_name,
                duration,
                calories_burned,
                date,
                strftime('%w', date) as day_number,
                CASE strftime('%w', date)
                    WHEN '0' THEN 'Sunday'
                    WHEN '1' THEN 'Monday'
                    WHEN '2' THEN 'Tuesday'
                    WHEN '3' THEN 'Wednesday'
                    WHEN '4' THEN 'Thursday'
                    WHEN '5' THEN 'Friday'
                    WHEN '6' THEN 'Saturday'
                END as day_name
            FROM exercises 
            WHERE phone = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        )
        SELECT 
            day_number,
            day_name,
            '[' || GROUP_CONCAT(json_object(
                'name', exercise_name,
                'duration', duration,
                'calories', calories_burned,
                'date', date
            )) || ']' as exercises
        FROM RankedExercises
        GROUP BY day_number
        ORDER BY day_number
    """, (phone, monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')))
    
    daily_exercises = cursor.fetchall()
    
    # Initialize the week with empty data
    week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    exercise_schedule = [{'day': day, 'exercises': []} for day in week_days]
    
    # Populate the schedule with data from the query
    for day in daily_exercises:
        try:
            import json
            exercises_list = json.loads(day[2])
            day_index = int(day[0]) - 1  # Adjust day_number to match the week_days index
            exercise_schedule[day_index] = {
                'day': day[1],
                'exercises': exercises_list
            }
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            continue
    
    # Get total statistics for the current week
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT date) as total_days,
            COUNT(*) as total_exercises,
            SUM(calories_burned) as total_calories
        FROM exercises 
        WHERE phone = ? AND date BETWEEN ? AND ?
    """, (phone, monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')))
    stats = cursor.fetchone()
    
    conn.close()
    
    return render_template('activity_history.html', 
                         schedule=exercise_schedule,
                         stats={
                             'total_days': stats[0],
                             'total_exercises': stats[1],
                             'total_calories': stats[2] or 0
                         })

@app.route('/clear-recent-meals', methods=['POST'])
def clear_recent_meals():
    if 'phone' not in session:
        return redirect('/login')

    phone = session['phone']
    today = datetime.today().strftime('%Y-%m-%d')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meals WHERE phone = ? AND date = ?", (phone, today))
    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/clear_meals', methods=['POST'])
def clear_meals():
    if 'phone' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    try:
        phone = session['phone']
        today = datetime.today().strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete today's meals for the user
        cursor.execute("DELETE FROM meals WHERE phone = ? AND date = ?", (phone, today))
        
        # Reset current calories for today
        cursor.execute("""
            UPDATE calorie_goals 
            SET current_calories = 0 
            WHERE phone = ? AND date = ?
        """, (phone, today))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Meals cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
