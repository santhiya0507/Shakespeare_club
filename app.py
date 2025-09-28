import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from gemini import analyze_sentiment, summarize_article, analyze_communication_practice

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'your-secret-key-here')

# Database initialization
def init_db():
    conn = sqlite3.connect('shakespeare_club.db')
    c = conn.cursor()
    
    # Students table
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        register_number TEXT UNIQUE NOT NULL,
        mobile_number TEXT NOT NULL,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Admins table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Practices table
    c.execute('''CREATE TABLE IF NOT EXISTS practices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        practice_type TEXT NOT NULL,
        content_file TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES admins (id)
    )''')
    
    # Student performances table
    c.execute('''CREATE TABLE IF NOT EXISTS student_performances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        practice_id INTEGER NOT NULL,
        score REAL NOT NULL,
        feedback TEXT,
        ai_analysis TEXT,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (practice_id) REFERENCES practices (id)
    )''')
    
    # Insert default admin if not exists
    c.execute("SELECT * FROM admins WHERE username = 'admin'")
    if not c.fetchone():
        admin_password_hash = generate_password_hash('admin123')
        c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", 
                 ('admin', admin_password_hash))
        admin_id = c.lastrowid
        
        # Insert default practices
        default_practices = [
            ("Active Listening Exercise", "Listen to a conversation and identify key points, emotions, and underlying messages. Focus on non-verbal cues and tone of voice.", "listening", admin_id),
            ("Scene Observation Challenge", "Observe a given scenario or image and describe what you see in detail. Include character expressions, setting details, and potential story elements.", "observation", admin_id),
            ("Shakespeare Monologue Practice", "Choose a famous Shakespeare monologue and practice delivering it with proper expression, intonation, and dramatic flair. Record your interpretation.", "speaking", admin_id),
            ("Creative Writing Workshop", "Write a short story or essay incorporating Shakespearean themes of love, betrayal, honor, or fate. Focus on clear communication and expressive language.", "writing", admin_id),
            ("Dialogue Analysis", "Listen to a dialogue between characters and analyze their communication styles, hidden meanings, and emotional subtext.", "listening", admin_id),
            ("Character Study", "Observe character interactions in a scene and describe their motivations, relationships, and communication patterns.", "observation", admin_id),
            ("Impromptu Speech", "Deliver a 2-minute impromptu speech on a given topic related to communication, literature, or current events.", "speaking", admin_id),
            ("Persuasive Essay", "Write a persuasive essay arguing for or against a contemporary issue using clear arguments and effective communication techniques.", "writing", admin_id)
        ]
        
        for title, description, practice_type, created_by in default_practices:
            c.execute("INSERT INTO practices (title, description, practice_type, created_by) VALUES (?, ?, ?, ?)",
                     (title, description, practice_type, created_by))
    
    conn.commit()
    conn.close()

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('shakespeare_club.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        register_number = request.form['register_number']
        mobile_number = request.form['mobile_number']
        email = request.form['email']
        password = request.form['password']
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('''INSERT INTO students 
                           (name, department, register_number, mobile_number, email, password_hash)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        (name, department, register_number, mobile_number, email, password_hash))
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('student_login'))
        except sqlite3.IntegrityError:
            flash('Register number already exists!')
        finally:
            conn.close()
    
    return render_template('student_register.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        register_number = request.form['register_number']
        password = request.form['password']
        
        conn = get_db_connection()
        student = conn.execute('SELECT * FROM students WHERE register_number = ?', 
                              (register_number,)).fetchone()
        conn.close()
        
        if student and check_password_hash(student['password_hash'], password):
            session['student_id'] = student['id']
            session['student_name'] = student['name']
            session['user_type'] = 'student'
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid register number or password!')
    
    return render_template('student_login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admins WHERE username = ?', 
                            (username,)).fetchone()
        conn.close()
        
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            session['user_type'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!')
    
    return render_template('admin_login.html')

@app.route('/student/dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    
    conn = get_db_connection()
    
    # Get student's recent performances
    performances = conn.execute('''
        SELECT p.title, p.practice_type, sp.score, sp.completed_at, sp.ai_analysis
        FROM student_performances sp
        JOIN practices p ON sp.practice_id = p.id
        WHERE sp.student_id = ?
        ORDER BY sp.completed_at DESC
        LIMIT 5
    ''', (session['student_id'],)).fetchall()
    
    # Get available practices
    practices = conn.execute('''
        SELECT id, title, description, practice_type
        FROM practices
        ORDER BY created_at DESC
    ''').fetchall()
    
    # Get student ranking
    ranking = conn.execute('''
        SELECT 
            s.name,
            s.register_number,
            AVG(sp.score) as avg_score,
            COUNT(sp.id) as total_practices
        FROM students s
        LEFT JOIN student_performances sp ON s.id = sp.student_id
        GROUP BY s.id
        ORDER BY avg_score DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('student_dashboard.html', 
                         performances=performances, 
                         practices=practices, 
                         ranking=ranking)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    
    # Get statistics
    stats = {
        'total_students': conn.execute('SELECT COUNT(*) FROM students').fetchone()[0],
        'total_practices': conn.execute('SELECT COUNT(*) FROM practices').fetchone()[0],
        'total_performances': conn.execute('SELECT COUNT(*) FROM student_performances').fetchone()[0]
    }
    
    # Get recent performances
    recent_performances = conn.execute('''
        SELECT 
            s.name,
            s.register_number,
            p.title,
            p.practice_type,
            sp.score,
            sp.completed_at
        FROM student_performances sp
        JOIN students s ON sp.student_id = s.id
        JOIN practices p ON sp.practice_id = p.id
        ORDER BY sp.completed_at DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         stats=stats, 
                         recent_performances=recent_performances)

@app.route('/practice/<int:practice_id>')
def take_practice(practice_id):
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    
    conn = get_db_connection()
    practice = conn.execute('SELECT * FROM practices WHERE id = ?', 
                           (practice_id,)).fetchone()
    conn.close()
    
    if not practice:
        flash('Practice not found!')
        return redirect(url_for('student_dashboard'))
    
    return render_template('practice.html', practice=practice)

@app.route('/submit_practice', methods=['POST'])
def submit_practice():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    
    practice_id = request.form['practice_id']
    submission_text = request.form['submission']
    
    try:
        # Get practice details for better analysis
        conn = get_db_connection()
        practice = conn.execute('SELECT * FROM practices WHERE id = ?', (practice_id,)).fetchone()
        
        # Use Gemini AI for comprehensive analysis
        sentiment_result = analyze_sentiment(submission_text)
        detailed_feedback = analyze_communication_practice(submission_text, practice['practice_type'])
        
        # Calculate score based on AI analysis with practice type considerations
        base_score = sentiment_result.rating * 20  # Convert to percentage
        
        # Adjust score based on practice type and text length
        if practice['practice_type'] == 'writing' and len(submission_text.split()) > 50:
            bonus = 5  # Bonus for substantial writing
        elif practice['practice_type'] == 'speaking' and len(submission_text.split()) > 30:
            bonus = 5  # Bonus for detailed speaking practice
        else:
            bonus = 0
            
        final_score = min(100, base_score + bonus)  # Cap at 100%
        
        ai_analysis = f"Score: {sentiment_result.rating}/5 (Confidence: {sentiment_result.confidence:.2f})\n\nDetailed Analysis:\n{detailed_feedback}"
        
        conn.execute('''INSERT INTO student_performances 
                       (student_id, practice_id, score, ai_analysis)
                       VALUES (?, ?, ?, ?)''',
                    (session['student_id'], practice_id, final_score, ai_analysis))
        conn.commit()
        conn.close()
        
        flash(f'Practice submitted successfully! Score: {final_score}% - Check your dashboard for detailed AI feedback.')
    except Exception as e:
        flash(f'Error analyzing submission: {str(e)}')
        # Still save the submission without AI analysis in case of API issues
        try:
            conn = get_db_connection()
            conn.execute('''INSERT INTO student_performances 
                           (student_id, practice_id, score, ai_analysis)
                           VALUES (?, ?, ?, ?)''',
                        (session['student_id'], practice_id, 75.0, f"Submission received but AI analysis failed: {str(e)}"))
            conn.commit()
            conn.close()
            flash('Practice submitted with basic scoring. AI analysis temporarily unavailable.')
        except:
            pass
    
    return redirect(url_for('student_dashboard'))

@app.route('/admin/practices')
def admin_practices():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    practices = conn.execute('SELECT * FROM practices ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('admin_practices.html', practices=practices)

@app.route('/admin/add_practice', methods=['GET', 'POST'])
def add_practice():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        practice_type = request.form['practice_type']
        
        conn = get_db_connection()
        conn.execute('''INSERT INTO practices (title, description, practice_type, created_by)
                       VALUES (?, ?, ?, ?)''',
                    (title, description, practice_type, session['admin_id']))
        conn.commit()
        conn.close()
        
        flash('Practice added successfully!')
        return redirect(url_for('admin_practices'))
    
    return render_template('add_practice.html')

@app.route('/admin/students')
def admin_students():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    students = conn.execute('''
        SELECT 
            s.*,
            AVG(sp.score) as avg_score,
            COUNT(sp.id) as total_practices
        FROM students s
        LEFT JOIN student_performances sp ON s.id = sp.student_id
        GROUP BY s.id
        ORDER BY avg_score DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_students.html', students=students)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)