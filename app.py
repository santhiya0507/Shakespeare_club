import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json
from gemini import analyze_sentiment, analyze_communication_practice
import random

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'shakespeare-club-secret-key')

# Database initialization for gamified app
def init_db():
    conn = sqlite3.connect('shakespeare_club_gamified.db')
    c = conn.cursor()
    
    # Users table (simplified registration)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        register_number TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        total_points INTEGER DEFAULT 0,
        current_streak INTEGER DEFAULT 0,
        best_streak INTEGER DEFAULT 0,
        badges TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Admins table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Content tables for each module
    c.execute('''CREATE TABLE IF NOT EXISTS biographies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        person_name TEXT NOT NULL,
        content TEXT NOT NULL,
        profession TEXT NOT NULL,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admins (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS daily_quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote TEXT NOT NULL,
        author TEXT,
        posted_by INTEGER NOT NULL,
        department TEXT NOT NULL,
        post_date DATE NOT NULL,
        is_featured BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (posted_by) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS listening_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        audio_file TEXT NOT NULL,
        transcript TEXT NOT NULL,
        robot_character TEXT DEFAULT 'boy',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admins (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS observation_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        video_url TEXT NOT NULL,
        questions TEXT NOT NULL,
        correct_answers TEXT NOT NULL,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admins (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS writing_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admins (id)
    )''')
    
    # User activities and completions
    c.execute('''CREATE TABLE IF NOT EXISTS user_completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        module_type TEXT NOT NULL,
        content_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        points_earned INTEGER NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_streaks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        streak_date DATE NOT NULL,
        modules_completed INTEGER DEFAULT 0,
        points_earned INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Insert default admin
    c.execute("SELECT * FROM admins WHERE username = 'admin'")
    if not c.fetchone():
        admin_password_hash = generate_password_hash('admin123')
        c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", 
                 ('admin', admin_password_hash))
        admin_id = c.lastrowid
        
        # Insert sample content
        sample_biographies = [
            ("MS Dhoni - The Captain Cool", "Mahendra Singh Dhoni", 
             "Mahendra Singh Dhoni, known as Captain Cool, is one of the greatest cricket captains in history. Born on July 7, 1981, in Ranchi, Jharkhand, Dhoni rose from a small town to lead India to victory in the 2007 T20 World Cup, 2011 Cricket World Cup, and 2013 Champions Trophy. His calm demeanor under pressure and lightning-fast wicket-keeping skills made him a legend. Dhoni's leadership style was unique - he led by example, never panicked, and always believed in his team. Even in the most challenging situations, he maintained his composure and made strategic decisions that turned matches around.", 
             "Cricketer", admin_id),
            ("Dr. APJ Abdul Kalam - The Missile Man", "Dr. APJ Abdul Kalam",
             "Dr. Avul Pakir Jainulabdeen Abdul Kalam, known as the Missile Man of India, was born on October 15, 1931, in Rameswaram, Tamil Nadu. From humble beginnings selling newspapers to becoming India's 11th President, Dr. Kalam's journey is truly inspiring. He played a pivotal role in India's space and missile programs, leading projects like Agni and Prithvi missiles. His vision for India as a developed nation by 2020 motivated millions. Dr. Kalam was not just a scientist but also a teacher who loved interacting with students. His simplicity, dedication to education, and unwavering belief in the power of dreams made him the People's President.",
             "Scientist", admin_id)
        ]
        
        for title, name, content, profession, created_by in sample_biographies:
            c.execute("INSERT INTO biographies (title, person_name, content, profession, created_by) VALUES (?, ?, ?, ?, ?)",
                     (title, name, content, profession, created_by))
        
        # Sample listening content
        sample_listening = [
            ("Robot Greeting", "audio_greeting.mp3", 
             "Hello there! Welcome to the Shakespeare Club Communication App. I am your friendly learning companion. Today we will practice listening skills together. Are you ready to begin this exciting journey of improving your English communication? Let's start with something fun and educational!",
             "boy", admin_id),
            ("Daily Motivation", "audio_motivation.mp3",
             "Good morning, dear students! Every day is a new opportunity to learn something amazing. Remember, communication is not just about speaking - it's about connecting with others, sharing ideas, and building relationships. Practice makes perfect, so keep working on your skills. You are capable of achieving great things!",
             "girl", admin_id)
        ]
        
        for title, audio_file, transcript, robot_character, created_by in sample_listening:
            c.execute("INSERT INTO listening_content (title, audio_file, transcript, robot_character, created_by) VALUES (?, ?, ?, ?, ?)",
                     (title, audio_file, transcript, robot_character, created_by))
        
        # Sample observation content
        sample_observation = [
            ("Success Mindset", "https://www.youtube.com/watch?v=motivational1",
             "What are the key points mentioned about achieving success? List three important qualities discussed in the video.",
             "Hard work, Perseverance, Positive attitude", admin_id),
            ("Communication Skills", "https://www.youtube.com/watch?v=communication1",
             "According to the video, what makes effective communication? Name two important elements.",
             "Active listening, Clear expression", admin_id)
        ]
        
        for title, video_url, questions, answers, created_by in sample_observation:
            c.execute("INSERT INTO observation_content (title, video_url, questions, correct_answers, created_by) VALUES (?, ?, ?, ?, ?)",
                     (title, video_url, questions, answers, created_by))
        
        # Sample writing topics
        sample_topics = [
            ("My Dreams and Aspirations", "Write about your future goals and how you plan to achieve them.", admin_id),
            ("The Importance of Communication", "Explain why good communication skills are essential in today's world.", admin_id),
            ("A Person Who Inspires Me", "Describe someone who motivates you and explain why they are your inspiration.", admin_id)
        ]
        
        for topic, description, created_by in sample_topics:
            c.execute("INSERT INTO writing_topics (topic, description, created_by) VALUES (?, ?, ?)",
                     (topic, description, created_by))
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('shakespeare_club_gamified.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_badge_progress(user_id):
    """Calculate badges based on user achievements"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    completions = conn.execute('SELECT * FROM user_completions WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    
    badges = []
    if user['total_points'] >= 100:
        badges.append("Century Scorer")
    if user['best_streak'] >= 7:
        badges.append("Week Warrior")
    if user['best_streak'] >= 30:
        badges.append("Monthly Master")
    if len(completions) >= 10:
        badges.append("Practice Champion")
    if len(completions) >= 50:
        badges.append("Communication Expert")
    
    # Update badges in database
    conn = get_db_connection()
    conn.execute('UPDATE users SET badges = ? WHERE id = ?', (json.dumps(badges), user_id))
    conn.commit()
    conn.close()
    
    return badges

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        register_number = request.form['register_number']
        department = request.form['department']
        
        conn = get_db_connection()
        try:
            conn.execute('''INSERT INTO users (username, register_number, department)
                           VALUES (?, ?, ?)''',
                        (username, register_number, department))
            conn.commit()
            
            # Get the new user
            user = conn.execute('SELECT * FROM users WHERE register_number = ?', (register_number,)).fetchone()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['department'] = user['department']
            
            flash('Welcome to Shakespeare Club! Your communication journey begins now! 🎭')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('Username or register number already exists!')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        register_number = request.form['register_number']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE register_number = ?', (register_number,)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['department'] = user['department']
            flash(f'Welcome back, {user["username"]}! Ready for more communication practice? 🌟')
            return redirect(url_for('dashboard'))
        else:
            flash('Register number not found!')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get user stats
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Get recent completions
    recent_activities = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? 
        ORDER BY completed_at DESC 
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    # Get today's featured quote
    today = date.today()
    featured_quote = conn.execute('''
        SELECT dq.*, u.username, u.department 
        FROM daily_quotes dq 
        JOIN users u ON dq.posted_by = u.id 
        WHERE dq.post_date = ? AND dq.is_featured = TRUE 
        ORDER BY dq.created_at ASC 
        LIMIT 1
    ''', (today,)).fetchone()
    
    # Calculate badges
    badges = calculate_badge_progress(session['user_id'])
    
    conn.close()
    
    return render_template('dashboard.html', 
                         user=user, 
                         activities=recent_activities, 
                         featured_quote=featured_quote,
                         badges=badges)

@app.route('/speaking')
def speaking_module():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get available biographies
    biographies = conn.execute('SELECT * FROM biographies ORDER BY created_at DESC').fetchall()
    
    # Get completed biographies
    completed = conn.execute('''
        SELECT content_id FROM user_completions 
        WHERE user_id = ? AND module_type = "speaking"
    ''', (session['user_id'],)).fetchall()
    
    completed_ids = [row['content_id'] for row in completed]
    
    conn.close()
    
    return render_template('speaking.html', biographies=biographies, completed_ids=completed_ids)

@app.route('/speaking/<int:bio_id>')
def speaking_practice(bio_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Check if already completed
    completed = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? AND module_type = "speaking" AND content_id = ?
    ''', (session['user_id'], bio_id)).fetchone()
    
    if completed:
        flash('You have already completed this speaking practice! ✅')
        return redirect(url_for('speaking_module'))
    
    biography = conn.execute('SELECT * FROM biographies WHERE id = ?', (bio_id,)).fetchone()
    conn.close()
    
    if not biography:
        flash('Biography not found!')
        return redirect(url_for('speaking_module'))
    
    return render_template('speaking_practice.html', biography=biography)

@app.route('/submit_speaking', methods=['POST'])
def submit_speaking():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    bio_id = request.form['bio_id']
    recorded_text = request.form['recorded_text']
    
    conn = get_db_connection()
    
    # Check if already completed this practice
    existing = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? AND module_type = "speaking" AND content_id = ?
    ''', (session['user_id'], bio_id)).fetchone()
    
    if existing:
        conn.close()
        flash('🚫 You have already completed this practice! Try a different one.')
        return redirect(url_for('speaking_module'))
    
    biography = conn.execute('SELECT * FROM biographies WHERE id = ?', (bio_id,)).fetchone()
    
    try:
        # Use Gemini AI for real analysis
        sentiment_result = analyze_sentiment(recorded_text)
        detailed_feedback = analyze_communication_practice(recorded_text, 'speaking')
        
        # Calculate similarity percentage with AI enhancement
        original_words = set(biography['content'].lower().split())
        user_words = set(recorded_text.lower().split())
        similarity = len(original_words.intersection(user_words)) / max(len(original_words), 1) * 100
        
        # Award 10 points for completion, bonus for high performance
        points_earned = 10
        if similarity >= 80 and sentiment_result.rating >= 4:
            points_earned = 15  # Bonus for excellent performance
        elif similarity >= 60 or sentiment_result.rating >= 3:
            points_earned = 12  # Good effort bonus
        
        final_score = min(100, similarity + sentiment_result.rating * 10)
        
    except Exception as e:
        # Fallback if AI fails
        original_words = biography['content'].lower().split()
        user_words = recorded_text.lower().split()
        matching_words = sum(1 for word in user_words if word in original_words)
        similarity = (matching_words / len(original_words)) * 100 if original_words else 0
        points_earned = 10 if similarity >= 70 else 8
        final_score = similarity
        detailed_feedback = f"Analysis completed with basic scoring. AI unavailable: {str(e)}"
    
    # Save completion
    conn.execute('''INSERT INTO user_completions 
                   (user_id, module_type, content_id, score, points_earned)
                   VALUES (?, ?, ?, ?, ?)''',
                (session['user_id'], 'speaking', bio_id, final_score, points_earned))
    
    # Update user points
    conn.execute('UPDATE users SET total_points = total_points + ? WHERE id = ?',
                (points_earned, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Update user streak and points
    today = date.today()
    streak_record = conn.execute('''
        SELECT * FROM user_streaks 
        WHERE user_id = ? AND streak_date = ?
    ''', (session['user_id'], today)).fetchone()
    
    if not streak_record:
        # First task today
        conn.execute('''INSERT INTO user_streaks 
                       (user_id, streak_date, modules_completed, points_earned)
                       VALUES (?, ?, 1, ?)''',
                    (session['user_id'], today, points_earned))
        
        # Update current streak
        yesterday = date.today().replace(day=date.today().day-1) if date.today().day > 1 else None
        if yesterday:
            yesterday_record = conn.execute('''
                SELECT * FROM user_streaks 
                WHERE user_id = ? AND streak_date = ?
            ''', (session['user_id'], yesterday)).fetchone()
            
            if yesterday_record:
                conn.execute('UPDATE users SET current_streak = current_streak + 1 WHERE id = ?',
                           (session['user_id'],))
            else:
                conn.execute('UPDATE users SET current_streak = 1 WHERE id = ?',
                           (session['user_id'],))
        else:
            conn.execute('UPDATE users SET current_streak = 1 WHERE id = ?',
                       (session['user_id'],))
    
    # Update best streak
    current_user = conn.execute('SELECT current_streak FROM users WHERE id = ?', 
                               (session['user_id'],)).fetchone()
    conn.execute('''UPDATE users SET best_streak = MAX(best_streak, current_streak) 
                   WHERE id = ?''', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    success_data = {
        'points': points_earned,
        'similarity': similarity,
        'celebration': similarity >= 70,
        'current_streak': current_user['current_streak'] if current_user else 1
    }
    
    return jsonify(success_data)

@app.route('/writing')
def writing_module():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get today's quotes by department
    today = date.today()
    department_quotes = conn.execute('''
        SELECT dq.*, u.username 
        FROM daily_quotes dq 
        JOIN users u ON dq.posted_by = u.id 
        WHERE dq.post_date = ? 
        ORDER BY dq.department, dq.created_at ASC
    ''', (today,)).fetchall()
    
    # Check if user already posted today
    user_posted_today = conn.execute('''
        SELECT * FROM daily_quotes 
        WHERE posted_by = ? AND post_date = ?
    ''', (session['user_id'], today)).fetchone()
    
    # Get available writing topics
    topics = conn.execute('SELECT * FROM writing_topics ORDER BY created_at DESC').fetchall()
    
    conn.close()
    
    return render_template('writing.html', 
                         department_quotes=department_quotes,
                         user_posted_today=user_posted_today,
                         topics=topics)

@app.route('/submit_quote', methods=['POST'])
def submit_quote():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    quote = request.form['quote']
    author = request.form['author']
    
    conn = get_db_connection()
    today = date.today()
    
    # Check if user already posted today
    existing = conn.execute('''
        SELECT * FROM daily_quotes 
        WHERE posted_by = ? AND post_date = ?
    ''', (session['user_id'], today)).fetchone()
    
    if existing:
        flash('You already posted a quote today!')
        return redirect(url_for('writing_module'))
    
    # Check if this is the first quote from this department today
    dept_quotes_today = conn.execute('''
        SELECT COUNT(*) as count FROM daily_quotes dq
        JOIN users u ON dq.posted_by = u.id
        WHERE u.department = ? AND dq.post_date = ?
    ''', (session['department'], today)).fetchone()
    
    is_first = dept_quotes_today['count'] == 0
    points_earned = 15 if is_first else 10
    
    # Insert quote
    conn.execute('''INSERT INTO daily_quotes 
                   (quote, author, posted_by, department, post_date, is_featured)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (quote, author, session['user_id'], session['department'], today, is_first))
    
    # Save completion
    conn.execute('''INSERT INTO user_completions 
                   (user_id, module_type, content_id, score, points_earned)
                   VALUES (?, ?, ?, ?, ?)''',
                (session['user_id'], 'writing', 0, 100, points_earned))
    
    # Update user points
    conn.execute('UPDATE users SET total_points = total_points + ? WHERE id = ?',
                (points_earned, session['user_id']))
    
    conn.commit()
    conn.close()
    
    if is_first:
        flash('🎉 Congratulations! You are the first from your department to post today! You earned 15 points!')
    else:
        flash(f'Great quote! You earned {points_earned} points! 📝')
    
    return redirect(url_for('writing_module'))

@app.route('/submit_writing', methods=['POST'])
def submit_writing():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    quote_id = request.form['quote_id']
    user_response = request.form['user_response']
    
    conn = get_db_connection()
    
    # Check if already completed this practice
    existing = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? AND module_type = "writing" AND content_id = ?
    ''', (session['user_id'], quote_id)).fetchone()
    
    if existing:
        conn.close()
        flash('🚫 You have already completed this writing practice! Try a different quote.')
        return redirect(url_for('writing_module'))
    
    quote = conn.execute('SELECT * FROM daily_quotes WHERE id = ?', (quote_id,)).fetchone()
    
    try:
        # Use Gemini AI for real writing analysis
        sentiment_result = analyze_sentiment(user_response)
        detailed_feedback = analyze_communication_practice(user_response, 'writing')
        
        # Calculate comprehensive writing score
        word_count = len(user_response.split())
        depth_score = min(100, word_count * 1.5)  # Reward substantial responses
        quality_score = sentiment_result.rating * 20  # Convert to percentage
        final_score = (depth_score + quality_score) / 2
        
        # Award 10 points for completion, bonus for exceptional writing
        points_earned = 10
        if word_count >= 100 and sentiment_result.rating >= 4:
            points_earned = 15  # Excellent writing bonus
        elif word_count >= 75 or sentiment_result.rating >= 3:
            points_earned = 12  # Good writing bonus
        
    except Exception as e:
        # Fallback scoring
        word_count = len(user_response.split())
        final_score = min(100, word_count * 2)
        points_earned = 10 if word_count >= 50 else 8
        detailed_feedback = f"Writing evaluated with basic scoring. AI unavailable: {str(e)}"
    
    # Save completion
    conn.execute('''INSERT INTO user_completions 
                   (user_id, module_type, content_id, score, points_earned)
                   VALUES (?, ?, ?, ?, ?)''',
                (session['user_id'], 'writing', quote_id, final_score, points_earned))
    
    # Update user points
    conn.execute('UPDATE users SET total_points = total_points + ? WHERE id = ?',
                (points_earned, session['user_id']))
    
    conn.commit()
    conn.close()
    
    flash(f'🎉 Writing practice completed! Points earned: {points_earned} | Score: {final_score:.1f}%')
    return redirect(url_for('writing_module'))

@app.route('/listening')
def listening_module():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get available listening content
    listening_items = conn.execute('SELECT * FROM listening_content ORDER BY created_at DESC').fetchall()
    
    # Get completed items
    completed = conn.execute('''
        SELECT content_id FROM user_completions 
        WHERE user_id = ? AND module_type = "listening"
    ''', (session['user_id'],)).fetchall()
    
    completed_ids = [row['content_id'] for row in completed]
    
    conn.close()
    
    return render_template('listening.html', listening_items=listening_items, completed_ids=completed_ids)

@app.route('/listening/<int:content_id>')
def listening_practice(content_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Check if already completed
    completed = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? AND module_type = "listening" AND content_id = ?
    ''', (session['user_id'], content_id)).fetchone()
    
    if completed:
        flash('You have already completed this listening practice! ✅')
        return redirect(url_for('listening_module'))
    
    content = conn.execute('SELECT * FROM listening_content WHERE id = ?', (content_id,)).fetchone()
    conn.close()
    
    if not content:
        flash('Content not found!')
        return redirect(url_for('listening_module'))
    
    return render_template('listening_practice.html', content=content)

@app.route('/submit_listening', methods=['POST'])
def submit_listening():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    content_id = request.form['content_id']
    user_input = request.form['user_input']
    
    conn = get_db_connection()
    
    # Check if already completed this practice
    existing = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? AND module_type = "listening" AND content_id = ?
    ''', (session['user_id'], content_id)).fetchone()
    
    if existing:
        conn.close()
        flash('🚫 You have already completed this listening practice! Try a different one.')
        return redirect(url_for('listening'))
    
    content = conn.execute('SELECT * FROM listening_content WHERE id = ?', (content_id,)).fetchone()
    
    try:
        # Use Gemini AI for listening comprehension analysis
        sentiment_result = analyze_sentiment(user_input)
        detailed_feedback = analyze_communication_practice(user_input, 'listening')
        
        # Calculate accuracy with AI enhancement
        original_text = content['transcript'].lower().strip()
        user_text = user_input.lower().strip()
        
        # Word-level accuracy
        original_words = set(original_text.split())
        user_words = set(user_text.split())
        word_accuracy = len(original_words.intersection(user_words)) / max(len(original_words), 1) * 100
        
        # Combined scoring
        accuracy = min(100, (word_accuracy + sentiment_result.rating * 15) / 2)
        points_earned = 10 if accuracy >= 80 else 8
        
    except Exception as e:
        # Fallback accuracy calculation
        original_text = content['transcript'].lower().strip()
        user_text = user_input.lower().strip()
        accuracy = (100 if original_text == user_text else 
                   80 if len(user_text) > 0 and original_text in user_text else
                   60 if len(user_text) > 0 else 0)
        points_earned = 10 if accuracy >= 80 else 8
    
    # Save completion
    conn.execute('''INSERT INTO user_completions 
                   (user_id, module_type, content_id, score, points_earned)
                   VALUES (?, ?, ?, ?, ?)''',
                (session['user_id'], 'listening', content_id, accuracy, points_earned))
    
    # Update user points
    conn.execute('UPDATE users SET total_points = total_points + ? WHERE id = ?',
                (points_earned, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Update user streak and points
    today = date.today()
    streak_record = conn.execute('''
        SELECT * FROM user_streaks 
        WHERE user_id = ? AND streak_date = ?
    ''', (session['user_id'], today)).fetchone()
    
    if not streak_record:
        conn.execute('''INSERT INTO user_streaks 
                       (user_id, streak_date, modules_completed, points_earned)
                       VALUES (?, ?, 1, ?)''',
                    (session['user_id'], today, points_earned))
        conn.execute('UPDATE users SET current_streak = current_streak + 1 WHERE id = ?',
                   (session['user_id'],))
    
    # Update best streak
    conn.execute('''UPDATE users SET best_streak = MAX(best_streak, current_streak) 
                   WHERE id = ?''', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    success_data = {
        'points': points_earned,
        'accuracy': accuracy,
        'celebration': accuracy >= 80
    }
    
    return jsonify(success_data)

@app.route('/observation')
def observation_module():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get available observation content
    observation_items = conn.execute('SELECT * FROM observation_content ORDER BY created_at DESC').fetchall()
    
    # Get completed items
    completed = conn.execute('''
        SELECT content_id FROM user_completions 
        WHERE user_id = ? AND module_type = "observation"
    ''', (session['user_id'],)).fetchall()
    
    completed_ids = [row['content_id'] for row in completed]
    
    conn.close()
    
    return render_template('observation.html', observation_items=observation_items, completed_ids=completed_ids)

@app.route('/observation/<int:content_id>')
def observation_practice(content_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Check if already completed
    completed = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? AND module_type = "observation" AND content_id = ?
    ''', (session['user_id'], content_id)).fetchone()
    
    if completed:
        flash('You have already completed this observation practice! ✅')
        return redirect(url_for('observation_module'))
    
    content = conn.execute('SELECT * FROM observation_content WHERE id = ?', (content_id,)).fetchone()
    conn.close()
    
    if not content:
        flash('Content not found!')
        return redirect(url_for('observation_module'))
    
    return render_template('observation_practice.html', content=content)

@app.route('/submit_observation', methods=['POST'])
def submit_observation():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    content_id = request.form['content_id']
    user_answer = request.form['user_answer']
    
    conn = get_db_connection()
    
    # Check if already completed this practice
    existing = conn.execute('''
        SELECT * FROM user_completions 
        WHERE user_id = ? AND module_type = "observation" AND content_id = ?
    ''', (session['user_id'], content_id)).fetchone()
    
    if existing:
        conn.close()
        flash('🚫 You have already completed this observation practice! Try a different video.')
        return redirect(url_for('observation'))
    
    content = conn.execute('SELECT * FROM observation_content WHERE id = ?', (content_id,)).fetchone()
    
    try:
        # Use Gemini AI for observation analysis
        sentiment_result = analyze_sentiment(user_answer)
        detailed_feedback = analyze_communication_practice(user_answer, 'observation')
        
        # Check answer accuracy with AI enhancement
        correct_answers = content['correct_answers'].lower()
        user_answer_lower = user_answer.lower()
        
        # Basic accuracy + AI quality assessment
        base_accuracy = 100 if correct_answers in user_answer_lower else 70
        quality_boost = sentiment_result.rating * 5  # Up to 25 point boost
        accuracy = min(100, base_accuracy + quality_boost)
        
        # Award 10 points for completion, bonus for excellent answers
        points_earned = 10 if accuracy >= 90 else 8
        
    except Exception as e:
        # Fallback scoring
        correct_answers = content['correct_answers'].lower()
        user_answer_lower = user_answer.lower()
        accuracy = 100 if correct_answers in user_answer_lower else 70
        points_earned = 10 if accuracy == 100 else 8
    
    # Save completion
    conn.execute('''INSERT INTO user_completions 
                   (user_id, module_type, content_id, score, points_earned)
                   VALUES (?, ?, ?, ?, ?)''',
                (session['user_id'], 'observation', content_id, accuracy, points_earned))
    
    # Update user points
    conn.execute('UPDATE users SET total_points = total_points + ? WHERE id = ?',
                (points_earned, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Update user streak and points  
    today = date.today()
    streak_record = conn.execute('''
        SELECT * FROM user_streaks 
        WHERE user_id = ? AND streak_date = ?
    ''', (session['user_id'], today)).fetchone()
    
    if not streak_record:
        conn.execute('''INSERT INTO user_streaks 
                       (user_id, streak_date, modules_completed, points_earned)
                       VALUES (?, ?, 1, ?)''',
                    (session['user_id'], today, points_earned))
        conn.execute('UPDATE users SET current_streak = current_streak + 1 WHERE id = ?',
                   (session['user_id'],))
    
    # Update best streak
    conn.execute('''UPDATE users SET best_streak = MAX(best_streak, current_streak) 
                   WHERE id = ?''', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    success_data = {
        'points': points_earned,
        'accuracy': accuracy,
        'celebration': accuracy == 100
    }
    
    return jsonify(success_data)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    
    stats = {
        'total_users': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'total_completions': conn.execute('SELECT COUNT(*) FROM user_completions').fetchone()[0],
        'today_activities': conn.execute('SELECT COUNT(*) FROM user_completions WHERE DATE(completed_at) = DATE("now")').fetchone()[0]
    }
    
    # Recent activities
    recent_activities = conn.execute('''
        SELECT uc.*, u.username, u.department 
        FROM user_completions uc
        JOIN users u ON uc.user_id = u.id
        ORDER BY uc.completed_at DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', stats=stats, activities=recent_activities)

@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    
    # Get top users by points
    top_users = conn.execute('''
        SELECT username, department, total_points, current_streak, best_streak, badges
        FROM users 
        ORDER BY total_points DESC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('leaderboard.html', top_users=top_users)

@app.route('/logout')
def logout():
    session.clear()
    flash('Thanks for practicing! Come back soon! 👋')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)