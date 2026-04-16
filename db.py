import mysql.connector
from mysql.connector import Error
from datetime import datetime, date, timedelta
import os, hashlib, hmac, base64

# ─── SECURITY: PBKDF2 PASSWORD HASHING ────────────────────────────────────────
def hash_password(password: str) -> str:
    """PBKDF2-SHA256 + random salt. Format: pbkdf2$salt_b64$hash_b64"""
    salt = os.urandom(32)
    key  = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 310000)
    return 'pbkdf2$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(key).decode()

def verify_password(password: str, stored: str) -> bool:
    """Verify password. Supports pbkdf2 (new) and sha256 (legacy)."""
    try:
        if stored.startswith('pbkdf2$'):
            _, salt_b64, key_b64 = stored.split('$')
            salt    = base64.b64decode(salt_b64)
            key     = base64.b64decode(key_b64)
            new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 310000)
            return hmac.compare_digest(key, new_key)
        else:
            # Legacy SHA256 — supported during migration period
            legacy = hashlib.sha256(password.encode()).hexdigest()
            return hmac.compare_digest(stored, legacy)
    except Exception:
        return False

# ─── DATABASE CONFIG ───────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': '',
    'database': 'daily_activity_db',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"[DB ERROR] Gagal konek: {e}")
        return None

def init_db():
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'], port=DB_CONFIG['port'],
            user=DB_CONFIG['user'], password=DB_CONFIG['password'],
            charset=DB_CONFIG['charset']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {DB_CONFIG['database']}")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                username    VARCHAR(50)  NOT NULL UNIQUE,
                email       VARCHAR(100) NOT NULL UNIQUE,
                password    VARCHAR(255) NOT NULL,
                full_name   VARCHAR(100),
                avatar_url  VARCHAR(255),
                theme_pref  VARCHAR(10) DEFAULT 'dark',
                onboarded   BOOLEAN DEFAULT FALSE,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
                title VARCHAR(200) NOT NULL, description TEXT,
                year INT NOT NULL, category VARCHAR(50) DEFAULT 'general',
                color VARCHAR(7) DEFAULT '#6366f1', icon VARCHAR(50) DEFAULT 'target',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id INT AUTO_INCREMENT PRIMARY KEY, goal_id INT NOT NULL, user_id INT NOT NULL,
                title VARCHAR(200) NOT NULL, description TEXT,
                month INT NOT NULL, year INT NOT NULL,
                target_value DECIMAL(10,2) DEFAULT 100, unit VARCHAR(30) DEFAULT 'percent',
                is_completed BOOLEAN DEFAULT FALSE, completed_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_targets (
                id INT AUTO_INCREMENT PRIMARY KEY, milestone_id INT NOT NULL, user_id INT NOT NULL,
                week_number INT NOT NULL, year INT NOT NULL,
                target_hours DECIMAL(5,2) DEFAULT 0, target_tasks INT DEFAULT 0, notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, milestone_id INT,
                title VARCHAR(255) NOT NULL, description TEXT,
                category VARCHAR(50) DEFAULT 'general',
                priority ENUM('low','medium','high','urgent') DEFAULT 'medium',
                status ENUM('todo','in_progress','done','cancelled') DEFAULT 'todo',
                duration_min INT DEFAULT 0, task_date DATE NOT NULL,
                start_time TIME, end_time TIME, tags VARCHAR(255),
                completed_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                goal_id INT NULL DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE SET NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_streaks (
                id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL UNIQUE,
                current_streak INT DEFAULT 0, longest_streak INT DEFAULT 0,
                last_active_date DATE, total_days INT DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # ── NEW: user_moods ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_moods (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                user_id    INT NOT NULL,
                mood       VARCHAR(10) NOT NULL,
                mood_label VARCHAR(50),
                mood_date  DATE NOT NULL,
                note       VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_user_date (user_id, mood_date),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # ── quick_notes ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quick_notes (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                user_id    INT NOT NULL,
                content    TEXT,
                color      VARCHAR(7) DEFAULT '#6366f1',
                note_date  DATE NOT NULL DEFAULT (CURDATE()),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # ── login_logs ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                user_id    INT,
                action     VARCHAR(50),
                ip_address VARCHAR(45),
                detail     VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("[DB] ✅ Database & tabel berhasil dibuat!")

        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            seed_demo_data(cursor)
            conn.commit()
            print("[DB] ✅ Demo data berhasil dimasukkan!")

        cursor.close(); conn.close()
        return True
    except Error as e:
        print(f"[DB ERROR] init_db gagal: {e}")
        return False


def seed_demo_data(cursor):
    pw = hash_password("admin123")
    cursor.execute("""
        INSERT INTO users (username, email, password, full_name, onboarded, is_admin)
        VALUES ('admin', 'admin@example.com', %s, 'Admin User', TRUE, TRUE)
    """, (pw,))
    user_id = cursor.lastrowid
    year = datetime.now().year

    goal_ids = []
    for g in [
        ('Fullstack Mastery', 'Menguasai pengembangan fullstack', 'tech',    '#6366f1', 'code'),
        ('Fitness & Health',  'Hidup sehat dan bugar',            'health',  '#10b981', 'heart'),
        ('Personal Finance',  'Literasi dan manajemen keuangan',  'finance', '#f59e0b', 'trending-up'),
    ]:
        cursor.execute("""
            INSERT INTO goals (user_id, title, description, year, category, color, icon)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, g[0], g[1], year, g[2], g[3], g[4]))
        goal_ids.append(cursor.lastrowid)

    now = datetime.now()
    for ms in [
        (goal_ids[0], user_id, 'Backend Python Flask', 'API & Database',        now.month, year),
        (goal_ids[0], user_id, 'Frontend React',       'UI & State Management', now.month, year),
        (goal_ids[1], user_id, 'Cardio 20x',           'Lari & Bersepeda',      now.month, year),
        (goal_ids[2], user_id, 'Investasi Reksa Dana', 'Mulai investasi rutin', now.month, year),
    ]:
        cursor.execute("INSERT INTO milestones (goal_id,user_id,title,description,month,year) VALUES (%s,%s,%s,%s,%s,%s)", ms)

    cursor.execute("SELECT MIN(id) FROM milestones WHERE user_id=%s", (user_id,))
    ms_id = cursor.fetchone()[0]

    today = date.today()
    tasks = []
    for i in range(7):
        d = today - timedelta(days=i)
        tasks += [
            (user_id, ms_id,   'Belajar Flask Route & Blueprint', 'Study session', 'tech',   'high',   'done' if i>0 else 'in_progress', 120, d),
            (user_id, ms_id,   'Coding REST API endpoint',        'Implementasi',  'tech',   'medium', 'done' if i>1 else 'todo',        90,  d),
            (user_id, ms_id+2, 'Lari pagi 5km',                   'Cardio session','health', 'medium', 'done' if i>0 else 'todo',        45,  d),
        ]
    cursor.executemany("""
        INSERT INTO daily_tasks (user_id,milestone_id,title,description,category,priority,status,duration_min,task_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, tasks)

    cursor.execute("""
        INSERT INTO activity_streaks (user_id,current_streak,longest_streak,last_active_date,total_days)
        VALUES (%s,7,14,%s,42)
    """, (user_id, today))

    # Seed beberapa mood
    moods = [('😊','Happy'),('🔥','Motivated'),('😌','Calm'),('💪','Energetic'),('😴','Tired')]
    for i, (emoji, label) in enumerate(moods):
        d = today - timedelta(days=i)
        cursor.execute("""
            INSERT IGNORE INTO user_moods (user_id,mood,mood_label,mood_date)
            VALUES (%s,%s,%s,%s)
        """, (user_id, emoji, label, d))


# ─── QUERY HELPERS ─────────────────────────────────────────────────────────────

def get_user(user_id):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id,username,email,full_name,avatar_url,theme_pref,onboarded,created_at FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    return user

def get_user_by_login(username_or_email, password, ip_address=None):
    """Login dengan lockout protection + activity log."""
    conn = get_connection()
    if not conn: return None, 'db_error'
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch user (tanpa cek password dulu)
        cursor.execute("""
            SELECT id,username,email,full_name,avatar_url,theme_pref,onboarded,
                   password, is_admin, failed_attempts, locked_until
            FROM users WHERE username=%s OR email=%s
        """, (username_or_email, username_or_email))
        user = cursor.fetchone()

        if not user:
            return None, 'invalid'

        # Cek lockout
        if user['locked_until']:
            from datetime import timezone
            lock_dt = user['locked_until']
            now_dt  = datetime.now()
            if lock_dt > now_dt:
                remaining = int((lock_dt - now_dt).total_seconds() // 60) + 1
                return None, f'locked:{remaining}'

        # Verify password
        if not verify_password(password, user['password']):
            # Increment failed_attempts
            new_attempts = (user['failed_attempts'] or 0) + 1
            locked_until = None
            if new_attempts >= 5:
                from datetime import timedelta
                locked_until = datetime.now() + timedelta(minutes=5)
                new_attempts = 0  # reset counter after lock
            cursor.execute("""
                UPDATE users SET failed_attempts=%s, locked_until=%s WHERE id=%s
            """, (new_attempts, locked_until, user['id']))
            # Log failed attempt
            _log_activity(cursor, user['id'], 'login_failed', ip_address, f'attempt {new_attempts}/5')
            conn.commit()
            return None, 'locked:0' if locked_until else 'invalid'

        # ✅ Login berhasil
        cursor.execute("""
            UPDATE users SET failed_attempts=0, locked_until=NULL, last_login=NOW() WHERE id=%s
        """, (user['id'],))
        # Auto-upgrade legacy SHA256 → PBKDF2
        if not user['password'].startswith('pbkdf2$'):
            cursor.execute("UPDATE users SET password=%s WHERE id=%s",
                           (hash_password(password), user['id']))
        _log_activity(cursor, user['id'], 'login_success', ip_address)
        conn.commit()

        # Return clean user dict
        return {k: user[k] for k in
                ['id','username','email','full_name','avatar_url','theme_pref','onboarded','is_admin']}, 'ok'
    except Exception as e:
        print(f'[login] error: {e}')
        return None, 'db_error'
    finally:
        cursor.close(); conn.close()

def _log_activity(cursor, user_id, action, ip=None, detail=None):
    """Internal: log activity ke tabel login_logs."""
    try:
        cursor.execute("""
            INSERT IGNORE INTO login_logs (user_id, action, ip_address, detail, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (user_id, action, ip or 'unknown', detail or ''))
    except Exception:
        pass  # Jangan sampai gagal login gara-gara log error

def register_user(username, email, password, full_name):
    pw = hash_password(password)   # PBKDF2, bukan SHA256
    conn = get_connection()
    if not conn: return None, "DB Error"
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username,email,password,full_name,is_admin) VALUES (%s,%s,%s,%s,FALSE)",
            (username, email, pw, full_name))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO activity_streaks (user_id) VALUES (%s)", (user_id,))
        conn.commit(); cursor.close(); conn.close()
        return user_id, None
    except Error as e:
        conn.close()
        if e.errno == 1062: return None, "Username atau email sudah digunakan"
        return None, str(e)

def update_avatar(user_id, avatar_url):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar_url=%s WHERE id=%s", (avatar_url, user_id))
    conn.commit(); cursor.close(); conn.close()
    return True

def mark_onboarded(user_id):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET onboarded=TRUE WHERE id=%s", (user_id,))
    conn.commit(); cursor.close(); conn.close()

def save_mood(user_id, mood, mood_label, note=''):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_moods (user_id,mood,mood_label,mood_date,note)
        VALUES (%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE mood=%s, mood_label=%s, note=%s
    """, (user_id, mood, mood_label, date.today(), note, mood, mood_label, note))
    conn.commit(); cursor.close(); conn.close()
    return True

def get_today_mood(user_id):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_moods WHERE user_id=%s AND mood_date=%s", (user_id, date.today()))
    mood = cursor.fetchone()
    cursor.close(); conn.close()
    return mood

def get_daily_tasks(user_id, task_date=None):
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    if task_date is None: task_date = date.today()
    cursor.execute("""
        SELECT t.*, m.title as milestone_title, m.goal_id
        FROM daily_tasks t
        LEFT JOIN milestones m ON t.milestone_id=m.id
        WHERE t.user_id=%s AND t.task_date=%s
        ORDER BY FIELD(t.priority,'urgent','high','medium','low'), t.created_at ASC
    """, (user_id, task_date))
    tasks = cursor.fetchall()
    cursor.close(); conn.close()
    return tasks

def create_task(user_id, data):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor()
    start_time = data.get('start_time') or None
    end_time   = data.get('end_time')   or None
    cursor.execute("""
        INSERT INTO daily_tasks (user_id,milestone_id,title,description,category,priority,status,duration_min,task_date,tags,start_time,end_time)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (user_id, data.get('milestone_id') or None, data['title'],
          data.get('description',''), data.get('category','general'),
          data.get('priority','medium'), data.get('status','todo'),
          data.get('duration_min',0), data.get('task_date', date.today()),
          data.get('tags',''), start_time, end_time))
    task_id = cursor.lastrowid
    conn.commit(); cursor.close(); conn.close()
    return task_id

def update_task_status(task_id, user_id, status):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    completed_at = datetime.now() if status == 'done' else None
    cursor.execute("UPDATE daily_tasks SET status=%s,completed_at=%s,updated_at=NOW() WHERE id=%s AND user_id=%s",
                   (status, completed_at, task_id, user_id))
    conn.commit(); affected = cursor.rowcount
    cursor.close(); conn.close()
    if status == 'done': update_streak(user_id)
    return affected > 0

def delete_task(task_id, user_id):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_tasks WHERE id=%s AND user_id=%s", (task_id, user_id))
    conn.commit(); ok = cursor.rowcount > 0
    cursor.close(); conn.close()
    return ok

def get_goals_with_progress(user_id, year=None):
    if year is None: year = datetime.now().year
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.*, COUNT(DISTINCT m.id) AS total_milestones, SUM(m.is_completed) AS done_milestones,
               IFNULL(ROUND(SUM(m.is_completed)/NULLIF(COUNT(DISTINCT m.id),0)*100),0) AS progress_pct
        FROM goals g LEFT JOIN milestones m ON m.goal_id=g.id
        WHERE g.user_id=%s AND g.year=%s AND g.is_active=1
        GROUP BY g.id ORDER BY g.created_at ASC
    """, (user_id, year))
    goals = cursor.fetchall()
    cursor.close(); conn.close()
    return goals

def get_milestones(user_id, goal_id=None, month=None, year=None):
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    now = datetime.now()
    month = month or now.month; year = year or now.year
    query = """
        SELECT m.*, COUNT(t.id) AS total_tasks, SUM(t.status='done') AS done_tasks,
               IFNULL(SUM(t.duration_min),0) AS total_minutes,
               IFNULL(ROUND(SUM(t.status='done')/NULLIF(COUNT(t.id),0)*100),0) AS progress_pct
        FROM milestones m
        LEFT JOIN daily_tasks t ON t.milestone_id=m.id AND t.task_date BETWEEN
              CONCAT(m.year,'-',LPAD(m.month,2,'0'),'-01')
              AND LAST_DAY(CONCAT(m.year,'-',LPAD(m.month,2,'0'),'-01'))
        WHERE m.user_id=%s
    """
    params = [user_id]
    if goal_id: query += " AND m.goal_id=%s"; params.append(goal_id)
    query += " GROUP BY m.id ORDER BY m.year,m.month,m.id"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def get_streak(user_id):
    conn = get_connection()
    if not conn: return {}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM activity_streaks WHERE user_id=%s", (user_id,))
    streak = cursor.fetchone() or {}
    cursor.close(); conn.close()
    return streak

def update_streak(user_id):
    today = date.today()
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM activity_streaks WHERE user_id=%s", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO activity_streaks (user_id,current_streak,last_active_date,total_days) VALUES (%s,1,%s,1)", (user_id, today))
    else:
        last = row['last_active_date']
        if last == today: pass
        elif last == today - timedelta(days=1):
            ns = row['current_streak']+1
            cursor.execute("UPDATE activity_streaks SET current_streak=%s,longest_streak=%s,last_active_date=%s,total_days=total_days+1 WHERE user_id=%s",
                           (ns, max(row['longest_streak'],ns), today, user_id))
        else:
            cursor.execute("UPDATE activity_streaks SET current_streak=1,last_active_date=%s,total_days=total_days+1 WHERE user_id=%s", (today, user_id))
    conn.commit(); cursor.close(); conn.close()

def get_weekly_summary(user_id, week_offset=0):
    today = date.today()
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
    end   = start + timedelta(days=6)
    conn  = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT task_date, COUNT(*) AS total_tasks, SUM(status='done') AS done_tasks,
               IFNULL(SUM(duration_min),0) AS total_minutes
        FROM daily_tasks WHERE user_id=%s AND task_date BETWEEN %s AND %s
        GROUP BY task_date ORDER BY task_date
    """, (user_id, start, end))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    result = []
    for i in range(7):
        d = start + timedelta(days=i)
        found = next((r for r in rows if r['task_date']==d), None)
        result.append({'date':d.isoformat(),'day':d.strftime('%a'),
                       'total_tasks':found['total_tasks'] if found else 0,
                       'done_tasks':found['done_tasks'] if found else 0,
                       'total_minutes':int(found['total_minutes']) if found else 0})
    return result

def get_contribution_grid(user_id, weeks=16):
    end   = date.today()
    start = end - timedelta(weeks=weeks)
    conn  = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT task_date, COUNT(*) AS total, SUM(status='done') AS done
        FROM daily_tasks WHERE user_id=%s AND task_date BETWEEN %s AND %s
        GROUP BY task_date
    """, (user_id, start, end))
    rows = {r['task_date']:r for r in cursor.fetchall()}
    cursor.close(); conn.close()
    grid = []
    for i in range((end-start).days+1):
        d = start + timedelta(days=i)
        r = rows.get(d, {'total':0,'done':0})
        level = 0
        if r['done']>=1: level=1
        if r['done']>=3: level=2
        if r['done']>=5: level=3
        if r['done']>=8: level=4
        grid.append({'date':d.isoformat(),'count':int(r['done']),'level':level})
    return grid

def search_all(user_id, query):
    """Command palette search"""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    q = f"%{query}%"
    results = []
    # Tasks
    cursor.execute("""
        SELECT id, title, status, priority, task_date, 'task' AS type FROM daily_tasks
        WHERE user_id=%s AND title LIKE %s ORDER BY task_date DESC LIMIT 5
    """, (user_id, q))
    for r in cursor.fetchall():
        r['task_date'] = r['task_date'].isoformat() if r['task_date'] else ''
        results.append(r)
    # Goals
    cursor.execute("""
        SELECT id, title, color, icon, 'goal' AS type FROM goals
        WHERE user_id=%s AND title LIKE %s LIMIT 3
    """, (user_id, q))
    results += cursor.fetchall()
    cursor.close(); conn.close()
    return results

# ─── QUICK NOTES & PUSH (added in v2) ─────────────────────────────────────────
def add_tables_v2():
    """Add new tables without breaking existing data"""
    conn = get_connection()
    if not conn: return
    c = conn.cursor()
    c.execute(f"USE {DB_CONFIG['database']}")

    c.execute("""
        CREATE TABLE IF NOT EXISTS quick_notes (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT NOT NULL,
            content    TEXT,
            color      VARCHAR(7) DEFAULT '#6366f1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT NOT NULL,
            endpoint   TEXT NOT NULL,
            p256dh     VARCHAR(255),
            auth_key   VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_user_endpoint (user_id, endpoint(200)),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Add tags column to daily_tasks if not exists
    try:
        c.execute("ALTER TABLE daily_tasks ADD COLUMN IF NOT EXISTS tags VARCHAR(255) DEFAULT ''")
    except: pass

    conn.commit(); c.close(); conn.close()
    print("[DB] ✅ Tables v2 ready")

# ─── ISQ TABLES v3 ─────────────────────────────────────────────────────────────
def add_tables_v3():
    conn = get_connection()
    if not conn: return
    c = conn.cursor()
    c.execute(f"USE {DB_CONFIG['database']}")

    c.execute("""
        CREATE TABLE IF NOT EXISTS isq_morning (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            user_id       INT NOT NULL,
            entry_date    DATE NOT NULL,
            energy_level  TINYINT DEFAULT 3,
            mood          VARCHAR(10),
            mood_label    VARCHAR(50),
            gratitude_1   VARCHAR(255),
            gratitude_2   VARCHAR(255),
            gratitude_3   VARCHAR(255),
            word_of_day   VARCHAR(50),
            intention_1   VARCHAR(255),
            intention_2   VARCHAR(255),
            intention_3   VARCHAR(255),
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_user_date (user_id, entry_date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS isq_evening (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT NOT NULL,
            entry_date      DATE NOT NULL,
            energy_level    TINYINT DEFAULT 3,
            mood            VARCHAR(10),
            mood_label      VARCHAR(50),
            intention_done  TINYINT DEFAULT 0,
            micro_journal   TEXT,
            highlight       VARCHAR(255),
            gratitude_close VARCHAR(255),
            isq_score       TINYINT DEFAULT 0,
            isq_mode        VARCHAR(20) DEFAULT 'steady',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_user_date (user_id, entry_date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS time_capsules (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            user_id      INT NOT NULL,
            message      TEXT NOT NULL,
            open_date    DATE NOT NULL,
            is_opened    BOOLEAN DEFAULT FALSE,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_letters (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            week_number INT NOT NULL,
            year        INT NOT NULL,
            letter      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_user_week (user_id, week_number, year),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit(); c.close(); conn.close()
    print("[DB] ✅ ISQ tables v3 ready")


def save_isq_morning(user_id, data):
    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    c.execute("""
        INSERT INTO isq_morning
          (user_id,entry_date,energy_level,mood,mood_label,
           gratitude_1,gratitude_2,gratitude_3,
           word_of_day,intention_1,intention_2,intention_3)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
          energy_level=%s,mood=%s,mood_label=%s,
          gratitude_1=%s,gratitude_2=%s,gratitude_3=%s,
          word_of_day=%s,intention_1=%s,intention_2=%s,intention_3=%s
    """, (
        user_id, data.get('date', date.today()),
        data.get('energy',3), data.get('mood','😊'), data.get('mood_label',''),
        data.get('gratitude_1',''), data.get('gratitude_2',''), data.get('gratitude_3',''),
        data.get('word_of_day',''), data.get('intention_1',''), data.get('intention_2',''), data.get('intention_3',''),
        # ON DUPLICATE
        data.get('energy',3), data.get('mood','😊'), data.get('mood_label',''),
        data.get('gratitude_1',''), data.get('gratitude_2',''), data.get('gratitude_3',''),
        data.get('word_of_day',''), data.get('intention_1',''), data.get('intention_2',''), data.get('intention_3',''),
    ))
    conn.commit(); c.close(); conn.close()
    return True


def save_isq_evening(user_id, data):
    # Calculate ISQ score
    score = 0
    score += min(data.get('energy',3), 5) * 10   # max 50
    if data.get('mood'): score += 15
    score += min(data.get('intention_done',0), 3) * 5  # max 15
    if data.get('micro_journal',''): score += 10
    if data.get('gratitude_close',''): score += 10
    score = min(score, 100)
    mode = 'flowing' if score>=75 else 'steady' if score>=50 else 'struggling' if score>=25 else 'resting'

    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    c.execute("""
        INSERT INTO isq_evening
          (user_id,entry_date,energy_level,mood,mood_label,
           intention_done,micro_journal,highlight,gratitude_close,isq_score,isq_mode)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
          energy_level=%s,mood=%s,mood_label=%s,
          intention_done=%s,micro_journal=%s,highlight=%s,
          gratitude_close=%s,isq_score=%s,isq_mode=%s
    """, (
        user_id, data.get('date', date.today()),
        data.get('energy',3), data.get('mood','😊'), data.get('mood_label',''),
        data.get('intention_done',0), data.get('micro_journal',''),
        data.get('highlight',''), data.get('gratitude_close',''), score, mode,
        data.get('energy',3), data.get('mood','😊'), data.get('mood_label',''),
        data.get('intention_done',0), data.get('micro_journal',''),
        data.get('highlight',''), data.get('gratitude_close',''), score, mode,
    ))
    conn.commit(); c.close(); conn.close()
    return score


def get_isq_today(user_id):
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    today = date.today()
    c.execute("SELECT * FROM isq_morning WHERE user_id=%s AND entry_date=%s", (user_id, today))
    morning = c.fetchone()
    c.execute("SELECT * FROM isq_evening WHERE user_id=%s AND entry_date=%s", (user_id, today))
    evening = c.fetchone()
    if morning and morning.get('entry_date'): morning['entry_date'] = morning['entry_date'].isoformat()
    if evening and evening.get('entry_date'): evening['entry_date'] = evening['entry_date'].isoformat()
    if morning and morning.get('created_at'): morning['created_at'] = str(morning['created_at'])
    if evening and evening.get('created_at'): evening['created_at'] = str(evening['created_at'])
    c.close(); conn.close()
    return {'morning': morning, 'evening': evening}


def get_isq_history(user_id, days=30):
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT m.entry_date, m.energy_level as m_energy, m.mood as m_mood,
               m.word_of_day, m.intention_1, m.intention_2, m.intention_3,
               e.energy_level as e_energy, e.mood as e_mood,
               e.micro_journal, e.highlight, e.isq_score, e.isq_mode,
               e.intention_done
        FROM isq_morning m
        LEFT JOIN isq_evening e ON e.user_id=m.user_id AND e.entry_date=m.entry_date
        WHERE m.user_id=%s
        ORDER BY m.entry_date DESC
        LIMIT %s
    """, (user_id, days))
    rows = c.fetchall()
    for r in rows:
        if r.get('entry_date'): r['entry_date'] = r['entry_date'].isoformat()
    c.close(); conn.close()
    return rows


def get_isq_context(user_id):
    """Rich context for AI voice generation"""
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    today = date.today()

    c.execute("SELECT * FROM isq_morning WHERE user_id=%s AND entry_date=%s", (user_id, today))
    morning = c.fetchone()
    c.execute("SELECT * FROM isq_evening WHERE user_id=%s AND entry_date=%s", (user_id, today))
    evening = c.fetchone()
    c.execute("SELECT * FROM activity_streaks WHERE user_id=%s", (user_id,))
    streak = c.fetchone() or {}
    c.execute("""
        SELECT COUNT(*) as total, SUM(status='done') as done
        FROM daily_tasks WHERE user_id=%s AND task_date=%s
    """, (user_id, today))
    tasks = c.fetchone() or {'total':0,'done':0}
    # Last 3 days mood
    c.execute("""
        SELECT mood_label, mood_date FROM user_moods
        WHERE user_id=%s ORDER BY mood_date DESC LIMIT 3
    """, (user_id,))
    moods = c.fetchall()

    c.close(); conn.close()
    return {
        'morning': morning,
        'evening': evening,
        'streak': streak.get('current_streak',0),
        'tasks_done': int(tasks.get('done') or 0),
        'tasks_total': int(tasks.get('total') or 0),
        'recent_moods': [m['mood_label'] for m in moods if m.get('mood_label')]
    }


def save_time_capsule(user_id, message, open_date):
    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    c.execute("INSERT INTO time_capsules (user_id,message,open_date) VALUES (%s,%s,%s)",
              (user_id, message, open_date))
    conn.commit(); c.close(); conn.close()
    return True


def get_due_capsules(user_id):
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT * FROM time_capsules
        WHERE user_id=%s AND open_date<=%s AND is_opened=FALSE
        ORDER BY open_date ASC
    """, (user_id, date.today()))
    rows = c.fetchall()
    for r in rows:
        if r.get('open_date'): r['open_date'] = r['open_date'].isoformat()
        if r.get('created_at'): r['created_at'] = str(r['created_at'])
    c.close(); conn.close()
    return rows


def open_capsule(capsule_id, user_id):
    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    c.execute("UPDATE time_capsules SET is_opened=TRUE WHERE id=%s AND user_id=%s",
              (capsule_id, user_id))
    conn.commit(); c.close(); conn.close()
    return True

# ─── SPRINT 2+3 TABLES ─────────────────────────────────────────────────────────
def add_tables_v4():
    conn = get_connection()
    if not conn: return
    c = conn.cursor()
    c.execute(f"USE {DB_CONFIG['database']}")

    # Compass Quiz archetype result per user
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_archetype (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    INT NOT NULL UNIQUE,
            archetype  VARCHAR(50) DEFAULT 'explorer',
            quiz_data  JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Adaptive task difficulty log
    c.execute("""
        CREATE TABLE IF NOT EXISTS adaptive_log (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            log_date    DATE NOT NULL,
            fail_streak INT DEFAULT 0,
            action_taken VARCHAR(100),
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Ghost data — weekly snapshots for comparison
    c.execute("""
        CREATE TABLE IF NOT EXISTS ghost_snapshots (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            week_start  DATE NOT NULL,
            day_data    JSON,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_user_week (user_id, week_start),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ══════════════════════════════════════════
    # REMINDER SYSTEM — Sprint v5
    # ══════════════════════════════════════════

    # ── reminders ──
    # Satu baris = satu pengingat milik user
    # repeat_type: daily | weekdays | weekend | weekly | custom
    # repeat_days: JSON array hari (0=Sen..6=Min), null = setiap hari
    # snooze_minutes: interval ulang notif kalau belum dicentang
    # quantity_target: untuk reminder kuantitatif (mis. 5 = 5km, 8 = 8 gelas)
    # quantity_unit: satuan (km, gelas, halaman, menit, dll)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            user_id          INT          NOT NULL,
            title            VARCHAR(200) NOT NULL,
            emoji            VARCHAR(10)  DEFAULT '🔔',
            remind_time      TIME         NOT NULL,
            repeat_type      ENUM('daily','weekdays','weekend','weekly','custom')
                             DEFAULT 'daily',
            repeat_days      JSON,
            snooze_minutes   INT          DEFAULT 30,
            is_active        BOOLEAN      DEFAULT TRUE,
            has_quantity     BOOLEAN      DEFAULT FALSE,
            quantity_target  DECIMAL(8,2) DEFAULT NULL,
            quantity_unit    VARCHAR(30)  DEFAULT NULL,
            category         VARCHAR(50)  DEFAULT 'general',
            color            VARCHAR(7)   DEFAULT '#6366f1',
            sort_order       INT          DEFAULT 0,
            created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,
            goal_id          INT          NULL DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL,
            INDEX idx_rem_user_active (user_id, is_active),
            INDEX idx_rem_user_time   (user_id, remind_time),
            INDEX idx_rem_goal        (goal_id)
        )
    """)

    # ── reminder_logs ──
    # Satu baris = satu instance harian dari satu reminder
    # completed_at NULL  = belum selesai hari ini
    # quantity_done: nilai aktual yang diinput user (mis. 4.5 km dari target 5)
    # snoozed_until: kalau user klik snooze, kapan notif berikutnya
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminder_logs (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            reminder_id     INT          NOT NULL,
            user_id         INT          NOT NULL,
            log_date        DATE         NOT NULL,
            completed_at    TIMESTAMP    NULL DEFAULT NULL,
            quantity_done   DECIMAL(8,2) DEFAULT NULL,
            snoozed_until   TIMESTAMP    NULL DEFAULT NULL,
            skipped         BOOLEAN      DEFAULT FALSE,
            note            VARCHAR(255) DEFAULT NULL,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_log_per_day (reminder_id, log_date),
            FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)     REFERENCES users(id)     ON DELETE CASCADE,
            INDEX idx_log_user_date   (user_id, log_date),
            INDEX idx_log_reminder    (reminder_id, log_date)
        )
    """)

    # ── reminder_streaks ──
    # Streak per reminder — terpisah dari activity_streaks global
    # tier: pemula | konsisten | momentum | disiplin | century |
    #        master | setahun | legend | immortal
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminder_streaks (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            reminder_id     INT          NOT NULL UNIQUE,
            user_id         INT          NOT NULL,
            current_streak  INT          DEFAULT 0,
            longest_streak  INT          DEFAULT 0,
            total_done      INT          DEFAULT 0,
            last_done_date  DATE         NULL,
            tier            VARCHAR(20)  DEFAULT 'pemula',
            tier_color      VARCHAR(7)   DEFAULT '#888780',
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)     REFERENCES users(id)     ON DELETE CASCADE,
            INDEX idx_rstreak_user (user_id)
        )
    """)

    # ── reminder_groups ──
    # Grup/challenge bersama (fase multi-user)
    # invite_code: 8-char kode unik untuk join grup
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminder_groups (
            id              INT          AUTO_INCREMENT PRIMARY KEY,
            name            VARCHAR(100) NOT NULL,
            description     TEXT,
            emoji           VARCHAR(10)  DEFAULT '👥',
            created_by      INT          NOT NULL,
            invite_code     VARCHAR(8)   NOT NULL UNIQUE,
            is_active       BOOLEAN      DEFAULT TRUE,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_group_invite (invite_code)
        )
    """)

    # ── reminder_group_members ──
    # Member dari setiap grup + role mereka
    # role: owner | admin | member
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminder_group_members (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            group_id        INT          NOT NULL,
            user_id         INT          NOT NULL,
            role            ENUM('owner','admin','member') DEFAULT 'member',
            joined_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_group_user (group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES reminder_groups(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)  REFERENCES users(id)           ON DELETE CASCADE,
            INDEX idx_gmem_user (user_id)
        )
    """)

    # ── reminder_group_challenges ──
    # Reminder yang dijadikan challenge di dalam grup
    # Setiap member harus selesaikan reminder ini setiap hari
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminder_group_challenges (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            group_id        INT          NOT NULL,
            title           VARCHAR(200) NOT NULL,
            emoji           VARCHAR(10)  DEFAULT '🎯',
            description     TEXT,
            remind_time     TIME         NOT NULL,
            start_date      DATE         NOT NULL,
            end_date        DATE         NULL,
            is_active       BOOLEAN      DEFAULT TRUE,
            created_by      INT          NOT NULL,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id)   REFERENCES reminder_groups(id)  ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id)            ON DELETE CASCADE,
            INDEX idx_challenge_group (group_id, is_active)
        )
    """)

    # ── reminder_challenge_logs ──
    # Log harian per member per challenge
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminder_challenge_logs (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            challenge_id    INT          NOT NULL,
            user_id         INT          NOT NULL,
            log_date        DATE         NOT NULL,
            completed_at    TIMESTAMP    NULL DEFAULT NULL,
            UNIQUE KEY uniq_chlog (challenge_id, user_id, log_date),
            FOREIGN KEY (challenge_id) REFERENCES reminder_group_challenges(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)      REFERENCES users(id)                     ON DELETE CASCADE,
            INDEX idx_chlog_date  (challenge_id, log_date),
            INDEX idx_chlog_user  (user_id, log_date)
        )
    """)

    # ── reminder_templates ──
    # Template library — bisa built-in (user_id NULL) atau buatan user
    # category: ibadah | kesehatan | produktivitas | custom
    # template_data: JSON array of reminder objects
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminder_templates (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NULL,
            name            VARCHAR(100) NOT NULL,
            description     VARCHAR(255),
            category        VARCHAR(50)  DEFAULT 'custom',
            emoji           VARCHAR(10)  DEFAULT '📦',
            template_data   JSON         NOT NULL,
            is_builtin      BOOLEAN      DEFAULT FALSE,
            use_count       INT          DEFAULT 0,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            INDEX idx_tpl_category (category, is_builtin)
        )
    """)

    # ── Seed built-in templates (skip jika sudah ada) ──
    c.execute("SELECT COUNT(*) as n FROM reminder_templates WHERE is_builtin=1")
    row = c.fetchone()
    if (row['n'] if isinstance(row, dict) else row[0]) == 0:
        import json
        builtin_templates = [
            {
                'name': 'Paket Ibadah',
                'description': 'Sholat 5 waktu, Al-Quran, dan dzikir harian',
                'category': 'ibadah',
                'emoji': '🕌',
                'template_data': json.dumps([
                    {'title':'Sholat Subuh',  'emoji':'🌅','remind_time':'04:30','snooze_minutes':10,'category':'ibadah','color':'#6366f1'},
                    {'title':'Sholat Dzuhur', 'emoji':'☀️','remind_time':'12:00','snooze_minutes':15,'category':'ibadah','color':'#6366f1'},
                    {'title':'Sholat Ashar',  'emoji':'🌤','remind_time':'15:30','snooze_minutes':15,'category':'ibadah','color':'#6366f1'},
                    {'title':'Sholat Maghrib','emoji':'🌆','remind_time':'18:00','snooze_minutes':10,'category':'ibadah','color':'#6366f1'},
                    {'title':'Sholat Isya',   'emoji':'🌙','remind_time':'19:30','snooze_minutes':15,'category':'ibadah','color':'#6366f1'},
                    {'title':'Baca Al-Quran', 'emoji':'📖','remind_time':'05:00','snooze_minutes':30,'has_quantity':True,'quantity_target':1,'quantity_unit':'juz','category':'ibadah','color':'#10b981'},
                    {'title':'Dzikir Pagi',   'emoji':'🌿','remind_time':'06:00','snooze_minutes':20,'category':'ibadah','color':'#10b981'},
                    {'title':'Dzikir Malam',  'emoji':'✨','remind_time':'21:00','snooze_minutes':20,'category':'ibadah','color':'#8b5cf6'},
                ])
            },
            {
                'name': 'Paket Kesehatan',
                'description': 'Olahraga, hidrasi, tidur, dan vitamin',
                'category': 'kesehatan',
                'emoji': '💪',
                'template_data': json.dumps([
                    {'title':'Minum Air Pagi',  'emoji':'💧','remind_time':'07:00','snooze_minutes':30,'has_quantity':True,'quantity_target':2,'quantity_unit':'gelas','category':'kesehatan','color':'#0ea5e9'},
                    {'title':'Minum Air Siang', 'emoji':'💧','remind_time':'12:00','snooze_minutes':30,'has_quantity':True,'quantity_target':2,'quantity_unit':'gelas','category':'kesehatan','color':'#0ea5e9'},
                    {'title':'Minum Air Sore',  'emoji':'💧','remind_time':'16:00','snooze_minutes':30,'has_quantity':True,'quantity_target':2,'quantity_unit':'gelas','category':'kesehatan','color':'#0ea5e9'},
                    {'title':'Olahraga',        'emoji':'🏃','remind_time':'06:00','snooze_minutes':30,'has_quantity':True,'quantity_target':30,'quantity_unit':'menit','category':'kesehatan','color':'#f59e0b'},
                    {'title':'Minum Vitamin',   'emoji':'💊','remind_time':'08:00','snooze_minutes':60,'category':'kesehatan','color':'#ec4899'},
                    {'title':'Tidur Tepat Waktu','emoji':'😴','remind_time':'22:00','snooze_minutes':30,'category':'kesehatan','color':'#8b5cf6'},
                ])
            },
            {
                'name': 'Paket Produktivitas',
                'description': 'Review pagi, fokus kerja, dan refleksi malam',
                'category': 'produktivitas',
                'emoji': '⚡',
                'template_data': json.dumps([
                    {'title':'Review Tasks Pagi',  'emoji':'📋','remind_time':'07:30','snooze_minutes':15,'category':'produktivitas','color':'#6366f1'},
                    {'title':'Deep Work Pagi',     'emoji':'🎯','remind_time':'08:00','snooze_minutes':30,'has_quantity':True,'quantity_target':90,'quantity_unit':'menit','category':'produktivitas','color':'#f59e0b'},
                    {'title':'Cek Progress Siang', 'emoji':'📊','remind_time':'13:00','snooze_minutes':30,'category':'produktivitas','color':'#6366f1'},
                    {'title':'Baca Buku',          'emoji':'📚','remind_time':'20:00','snooze_minutes':30,'has_quantity':True,'quantity_target':20,'quantity_unit':'halaman','category':'produktivitas','color':'#10b981'},
                    {'title':'Jurnal Malam',       'emoji':'📝','remind_time':'21:30','snooze_minutes':30,'category':'produktivitas','color':'#8b5cf6'},
                    {'title':'Review Hari Ini',    'emoji':'🌙','remind_time':'22:00','snooze_minutes':20,'category':'produktivitas','color':'#8b5cf6'},
                ])
            },
        ]
        for tpl in builtin_templates:
            c.execute("""
                INSERT INTO reminder_templates
                    (user_id, name, description, category, emoji, template_data, is_builtin)
                VALUES (NULL, %s, %s, %s, %s, %s, TRUE)
            """, (tpl['name'], tpl['description'], tpl['category'],
                  tpl['emoji'], tpl['template_data']))
        print("[DB] ✅ Built-in reminder templates seeded")

    # ══════════════════════════════════════════════════════
    # SPRINT v5 — PHASE 1: daily_focus cache
    # ══════════════════════════════════════════════════════

    # ── daily_focus ──
    # Cache 3 prioritas harian yang di-generate tiap pagi
    # source: 'milestone_deadline' | 'streak_risk' | 'task_overdue' | 'reminder_due'
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_focus (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT         NOT NULL,
            focus_date  DATE        NOT NULL,
            rank        TINYINT     NOT NULL DEFAULT 1,
            source      VARCHAR(30) NOT NULL,
            title       VARCHAR(200) NOT NULL,
            description VARCHAR(255),
            ref_type    VARCHAR(30),
            ref_id      INT,
            is_done     BOOLEAN     DEFAULT FALSE,
            done_at     TIMESTAMP   NULL,
            created_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY  uniq_focus (user_id, focus_date, rank),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_focus_date (user_id, focus_date)
        )
    """)

    # ══════════════════════════════════════════════════════
    # SPRINT v5 — PHASE 2: Financial Habit Tracker
    # ══════════════════════════════════════════════════════

    # ── currencies ──
    # Daftar mata uang yang didukung (manual rate update)
    c.execute("""
        CREATE TABLE IF NOT EXISTS currencies (
            code        VARCHAR(10)  PRIMARY KEY,
            name        VARCHAR(50)  NOT NULL,
            symbol      VARCHAR(5)   NOT NULL,
            rate_to_idr DECIMAL(20,6) DEFAULT 1.0,
            updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
        )
    """)

    # Seed mata uang dasar
    c.execute("SELECT COUNT(*) as n FROM currencies")
    row = c.fetchone()
    if (row['n'] if isinstance(row, dict) else row[0]) == 0:
        c.executemany(
            "INSERT IGNORE INTO currencies (code, name, symbol, rate_to_idr) VALUES (%s,%s,%s,%s)",
            [
                ('IDR', 'Rupiah Indonesia',  'Rp',  1.0),
                ('USD', 'US Dollar',         '$',   16000.0),
                ('EUR', 'Euro',              '€',   17500.0),
                ('SGD', 'Singapore Dollar',  'S$',  12000.0),
                ('MYR', 'Ringgit Malaysia',  'RM',  3500.0),
                ('SAR', 'Riyal Saudi Arabia','SR',  4200.0),
                ('GBP', 'British Pound',     '£',   20000.0),
                ('JPY', 'Japanese Yen',      '¥',   110.0),
                ('AUD', 'Australian Dollar', 'A$',  10500.0),
            ]
        )
        print("[DB] ✅ Currencies seeded")

    # ── savings_goals ──
    # Target tabungan — bisa terhubung ke goal roadmap
    # period: weekly | monthly | custom
    # target_amount dalam currency yang dipilih user
    c.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL,
            goal_id         INT          NULL,
            title           VARCHAR(200) NOT NULL,
            emoji           VARCHAR(10)  DEFAULT '💰',
            target_amount   DECIMAL(20,2) NOT NULL,
            currency        VARCHAR(10)  DEFAULT 'IDR',
            period          ENUM('weekly','monthly','custom') DEFAULT 'weekly',
            period_amount   DECIMAL(20,2) DEFAULT 0,
            start_date      DATE         NOT NULL,
            target_date     DATE         NULL,
            color           VARCHAR(7)   DEFAULT '#10b981',
            is_active       BOOLEAN      DEFAULT TRUE,
            is_completed    BOOLEAN      DEFAULT FALSE,
            completed_at    TIMESTAMP    NULL,
            notes           TEXT,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL,
            FOREIGN KEY (currency) REFERENCES currencies(code),
            INDEX idx_sav_user   (user_id, is_active),
            INDEX idx_sav_goal   (goal_id)
        )
    """)

    # ── saving_logs ──
    # Log setiap setoran/penarikan tabungan
    # type: deposit | withdrawal | adjustment
    c.execute("""
        CREATE TABLE IF NOT EXISTS saving_logs (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            savings_goal_id INT          NOT NULL,
            user_id         INT          NOT NULL,
            amount          DECIMAL(20,2) NOT NULL,
            type            ENUM('deposit','withdrawal','adjustment') DEFAULT 'deposit',
            currency        VARCHAR(10)  DEFAULT 'IDR',
            log_date        DATE         NOT NULL,
            note            VARCHAR(255),
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (savings_goal_id) REFERENCES savings_goals(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)         REFERENCES users(id)         ON DELETE CASCADE,
            FOREIGN KEY (currency)        REFERENCES currencies(code),
            INDEX idx_savlog_goal (savings_goal_id, log_date),
            INDEX idx_savlog_user (user_id, log_date)
        )
    """)

    # ── saving_streaks ──
    # Streak menabung per savings_goal — mingguan
    c.execute("""
        CREATE TABLE IF NOT EXISTS saving_streaks (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            savings_goal_id INT          NOT NULL UNIQUE,
            user_id         INT          NOT NULL,
            current_streak  INT          DEFAULT 0,
            longest_streak  INT          DEFAULT 0,
            total_periods   INT          DEFAULT 0,
            last_period     VARCHAR(10)  NULL,
            tier            VARCHAR(20)  DEFAULT 'pemula',
            tier_color      VARCHAR(7)   DEFAULT '#888780',
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (savings_goal_id) REFERENCES savings_goals(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)         REFERENCES users(id)         ON DELETE CASCADE,
            INDEX idx_savstreak_user (user_id)
        )
    """)

    # ── investments ──
    # Portofolio investasi (reksa dana, saham, emas, crypto, deposito, dll)
    # type: reksa_dana | saham | emas | crypto | deposito | obligasi | property | lainnya
    c.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL,
            goal_id         INT          NULL,
            title           VARCHAR(200) NOT NULL,
            type            VARCHAR(30)  DEFAULT 'lainnya',
            emoji           VARCHAR(10)  DEFAULT '📈',
            buy_price       DECIMAL(20,6) NOT NULL,
            units           DECIMAL(20,6) DEFAULT 1.0,
            currency        VARCHAR(10)  DEFAULT 'IDR',
            buy_date        DATE         NOT NULL,
            current_price   DECIMAL(20,6) NULL,
            price_updated_at TIMESTAMP   NULL,
            platform        VARCHAR(100),
            notes           TEXT,
            is_active       BOOLEAN      DEFAULT TRUE,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
            FOREIGN KEY (goal_id)  REFERENCES goals(id)  ON DELETE SET NULL,
            FOREIGN KEY (currency) REFERENCES currencies(code),
            INDEX idx_inv_user (user_id, is_active),
            INDEX idx_inv_goal (goal_id)
        )
    """)

    # ── investment_logs ──
    # Riwayat update harga + beli/jual tambahan
    # type: price_update | buy_more | partial_sell | sell_all
    c.execute("""
        CREATE TABLE IF NOT EXISTS investment_logs (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            investment_id   INT          NOT NULL,
            user_id         INT          NOT NULL,
            type            VARCHAR(20)  DEFAULT 'price_update',
            price           DECIMAL(20,6) NOT NULL,
            units           DECIMAL(20,6) DEFAULT 0,
            log_date        DATE         NOT NULL,
            note            VARCHAR(255),
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (investment_id) REFERENCES investments(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE,
            INDEX idx_invlog_inv  (investment_id, log_date),
            INDEX idx_invlog_user (user_id, log_date)
        )
    """)

    # ── fixed_expenses ──
    # Pengeluaran tetap bulanan (bukan full budgeting)
    # category: hunian | transportasi | pendidikan | kesehatan | langganan | lainnya
    c.execute("""
        CREATE TABLE IF NOT EXISTS fixed_expenses (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL,
            title           VARCHAR(200) NOT NULL,
            emoji           VARCHAR(10)  DEFAULT '💳',
            amount          DECIMAL(20,2) NOT NULL,
            currency        VARCHAR(10)  DEFAULT 'IDR',
            category        VARCHAR(30)  DEFAULT 'lainnya',
            billing_day     TINYINT      DEFAULT 1,
            is_active       BOOLEAN      DEFAULT TRUE,
            notes           VARCHAR(255),
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
            FOREIGN KEY (currency) REFERENCES currencies(code),
            INDEX idx_fexp_user (user_id, is_active)
        )
    """)

    # ══════════════════════════════════════════════════════
    # SPRINT v5 — PHASE 3: Insight & Review
    # ══════════════════════════════════════════════════════

    # ── weekly_reviews ──
    # Laporan mingguan otomatis (generated tiap Minggu malam)
    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reviews (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL,
            week_start      DATE         NOT NULL,
            week_end        DATE         NOT NULL,
            tasks_done      INT          DEFAULT 0,
            tasks_total     INT          DEFAULT 0,
            reminders_done  INT          DEFAULT 0,
            reminders_total INT          DEFAULT 0,
            avg_mood        DECIMAL(4,2) DEFAULT NULL,
            streaks_gained  INT          DEFAULT 0,
            streaks_lost    INT          DEFAULT 0,
            saving_amount   DECIMAL(20,2) DEFAULT 0,
            goal_progress   JSON,
            top_streak      JSON,
            summary_text    TEXT,
            is_read         BOOLEAN      DEFAULT FALSE,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_review (user_id, week_start),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_review_user (user_id, week_start)
        )
    """)

    # ══════════════════════════════════════════════════════
    # SPRINT v5 — PHASE 4: Gamifikasi
    # ══════════════════════════════════════════════════════

    # ── user_xp ──
    # Total XP dan level per user
    # Level: 1-10 (Pemula → Grand Master)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_xp (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL UNIQUE,
            total_xp        INT          DEFAULT 0,
            level           TINYINT      DEFAULT 1,
            level_title     VARCHAR(50)  DEFAULT 'Pemula',
            level_color     VARCHAR(7)   DEFAULT '#888780',
            xp_to_next      INT          DEFAULT 100,
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ── xp_logs ──
    # Log setiap dapat XP dari mana
    # source: task_done | reminder_done | streak_milestone | saving_deposit |
    #         isq_filled | goal_completed | login_streak | weekly_review
    c.execute("""
        CREATE TABLE IF NOT EXISTS xp_logs (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT         NOT NULL,
            xp_amount   INT         NOT NULL,
            source      VARCHAR(50) NOT NULL,
            description VARCHAR(200),
            ref_id      INT         NULL,
            earned_at   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_xp_user   (user_id, earned_at),
            INDEX idx_xp_source (user_id, source)
        )
    """)

    # ══════════════════════════════════════════════════════
    # SPRINT v6 — KANBAN + WORKSPACE + SHARE
    # ══════════════════════════════════════════════════════

    # ── boards ──
    # Kanban board — bisa private, team, atau public
    # visibility: private | team | public
    # type: personal | project | team
    c.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            user_id      INT          NOT NULL,
            goal_id      INT          NULL,
            title        VARCHAR(200) NOT NULL,
            description  TEXT,
            emoji        VARCHAR(10)  DEFAULT '📋',
            theme        VARCHAR(20)  DEFAULT 'default',
            visibility   ENUM('private','team','public') DEFAULT 'private',
            type         ENUM('personal','project','team') DEFAULT 'personal',
            invite_code  VARCHAR(8)   NULL UNIQUE,
            is_active    BOOLEAN      DEFAULT TRUE,
            sort_order   INT          DEFAULT 0,
            created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                         ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL,
            INDEX idx_board_user   (user_id, is_active),
            INDEX idx_board_invite (invite_code)
        )
    """)

    # ── board_columns ──
    # Kolom di dalam board (default: Todo, Doing, Done)
    # bisa dikustom nama dan warnanya
    c.execute("""
        CREATE TABLE IF NOT EXISTS board_columns (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            board_id   INT          NOT NULL,
            title      VARCHAR(100) NOT NULL,
            color      VARCHAR(7)   DEFAULT '#888780',
            sort_order INT          DEFAULT 0,
            wip_limit  INT          NULL,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
            INDEX idx_col_board (board_id, sort_order)
        )
    """)

    # ── board_members ──
    # Member tim untuk board type='team'
    # role: owner | editor | viewer
    c.execute("""
        CREATE TABLE IF NOT EXISTS board_members (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            board_id   INT          NOT NULL,
            user_id    INT          NOT NULL,
            role       ENUM('owner','editor','viewer') DEFAULT 'editor',
            joined_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_bm (board_id, user_id),
            FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
            INDEX idx_bm_user (user_id)
        )
    """)

    # ── board_cards ──
    # Card di dalam kolom kanban
    # Extends daily_tasks concept with kanban-specific fields
    c.execute("""
        CREATE TABLE IF NOT EXISTS board_cards (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            board_id     INT          NOT NULL,
            column_id    INT          NOT NULL,
            user_id      INT          NOT NULL,
            assigned_to  INT          NULL,
            goal_id      INT          NULL,
            title        VARCHAR(255) NOT NULL,
            description  TEXT,
            priority     ENUM('low','medium','high','urgent') DEFAULT 'medium',
            label_color  VARCHAR(7)   DEFAULT NULL,
            label_text   VARCHAR(50)  DEFAULT NULL,
            due_date     DATE         NULL,
            est_hours    DECIMAL(5,2) DEFAULT NULL,
            is_recurring BOOLEAN      DEFAULT FALSE,
            recur_type   VARCHAR(20)  DEFAULT NULL,
            sort_order   INT          DEFAULT 0,
            completed_at TIMESTAMP    NULL,
            archived_at  TIMESTAMP    NULL,
            created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                         ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id)   REFERENCES boards(id)  ON DELETE CASCADE,
            FOREIGN KEY (column_id)  REFERENCES board_columns(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)    REFERENCES users(id)   ON DELETE CASCADE,
            FOREIGN KEY (assigned_to) REFERENCES users(id)  ON DELETE SET NULL,
            FOREIGN KEY (goal_id)    REFERENCES goals(id)   ON DELETE SET NULL,
            INDEX idx_card_board  (board_id, archived_at),
            INDEX idx_card_column (column_id, sort_order),
            INDEX idx_card_due    (due_date)
        )
    """)

    # ── card_subtasks ──
    # Subtask checklist di dalam setiap card
    c.execute("""
        CREATE TABLE IF NOT EXISTS card_subtasks (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            card_id    INT          NOT NULL,
            title      VARCHAR(200) NOT NULL,
            is_done    BOOLEAN      DEFAULT FALSE,
            done_at    TIMESTAMP    NULL,
            sort_order INT          DEFAULT 0,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id) REFERENCES board_cards(id) ON DELETE CASCADE,
            INDEX idx_sub_card (card_id, sort_order)
        )
    """)

    # ── card_comments ──
    # Komentar/diskusi di dalam card (untuk board tim)
    c.execute("""
        CREATE TABLE IF NOT EXISTS card_comments (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            card_id    INT          NOT NULL,
            user_id    INT          NOT NULL,
            content    TEXT         NOT NULL,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (card_id)  REFERENCES board_cards(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)  REFERENCES users(id)       ON DELETE CASCADE,
            INDEX idx_comment_card (card_id)
        )
    """)

    # ── share_reports ──
    # Laporan yang sudah di-generate untuk di-share
    # type: weekly_summary | goal_progress | streak | finance | board_progress
    # platform: whatsapp | instagram | twitter | general
    c.execute("""
        CREATE TABLE IF NOT EXISTS share_reports (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT          NOT NULL,
            type        VARCHAR(30)  NOT NULL,
            title       VARCHAR(200),
            data        JSON,
            platform    VARCHAR(20)  DEFAULT 'general',
            share_token VARCHAR(32)  NOT NULL UNIQUE,
            expires_at  TIMESTAMP    NULL,
            view_count  INT          DEFAULT 0,
            created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_share_token (share_token),
            INDEX idx_share_user  (user_id)
        )
    """)

    # ══════════════════════════════════════════════════════
    # SPRINT v7 — ESQ ENHANCEMENT + WEEKLY REVIEW + ONBOARDING
    # ══════════════════════════════════════════════════════

    # ── esq_values ──
    # Nilai-nilai hidup yang user tetapkan sendiri
    # category: iman | keluarga | karir | kesehatan | sosial | ilmu | custom
    c.execute("""
        CREATE TABLE IF NOT EXISTS esq_values (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT          NOT NULL,
            title       VARCHAR(200) NOT NULL,
            description TEXT,
            category    VARCHAR(30)  DEFAULT 'custom',
            emoji       VARCHAR(10)  DEFAULT '⭐',
            color       VARCHAR(7)   DEFAULT '#6366f1',
            priority    TINYINT      DEFAULT 1,
            is_active   BOOLEAN      DEFAULT TRUE,
            created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_values_user (user_id, is_active)
        )
    """)

    # ── esq_reflections ──
    # Refleksi mendalam harian/mingguan
    # type: daily | weekly | milestone | gratitude | muhasabah
    c.execute("""
        CREATE TABLE IF NOT EXISTS esq_reflections (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL,
            type            VARCHAR(20)  DEFAULT 'daily',
            reflection_date DATE         NOT NULL,
            content         TEXT         NOT NULL,
            mood_score      TINYINT      DEFAULT 3,
            energy          TINYINT      DEFAULT 3,
            gratitude       TEXT,
            lessons         TEXT,
            tomorrow_intent TEXT,
            isq_score       TINYINT      DEFAULT NULL,
            is_private      BOOLEAN      DEFAULT TRUE,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_refl (user_id, type, reflection_date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_refl_date (user_id, reflection_date)
        )
    """)

    # ── esq_spiritual_log ──
    # Log ibadah & aktivitas spiritual harian
    # activity: sholat_subuh/dzuhur/ashar/maghrib/isya | quran | dzikir |
    #           sedekah | puasa | tahajud | dhuha | custom
    c.execute("""
        CREATE TABLE IF NOT EXISTS esq_spiritual_log (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT          NOT NULL,
            log_date    DATE         NOT NULL,
            activity    VARCHAR(50)  NOT NULL,
            label       VARCHAR(100) DEFAULT NULL,
            is_done     BOOLEAN      DEFAULT FALSE,
            done_at     TIMESTAMP    NULL,
            quantity    DECIMAL(6,2) DEFAULT NULL,
            unit        VARCHAR(20)  DEFAULT NULL,
            notes       VARCHAR(255) DEFAULT NULL,
            created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY  uniq_spiritual (user_id, log_date, activity),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_spiritual_date (user_id, log_date)
        )
    """)

    # ── weekly_review_generated ──
    # Weekly review yang di-generate otomatis setiap Minggu
    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_review_generated (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL,
            week_start      DATE         NOT NULL,
            week_end        DATE         NOT NULL,
            tasks_done      INT          DEFAULT 0,
            tasks_total     INT          DEFAULT 0,
            reminders_pct   DECIMAL(5,2) DEFAULT 0,
            avg_mood        DECIMAL(4,2) DEFAULT NULL,
            top_streaks     JSON,
            goal_progress   JSON,
            saving_amount   DECIMAL(20,2) DEFAULT 0,
            xp_earned       INT          DEFAULT 0,
            spiritual_score TINYINT      DEFAULT 0,
            highlight       VARCHAR(255),
            ai_summary      TEXT,
            is_read         BOOLEAN      DEFAULT FALSE,
            share_token     VARCHAR(32)  NULL UNIQUE,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_week_review (user_id, week_start),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_wrev_user (user_id, week_start)
        )
    """)

    # ── user_profile_setup ──
    # Onboarding: profil dan preferensi awal user
    # profile_type: pelajar | mahasiswa | profesional | ibu_rumah_tangga |
    #               wirausaha | pensiunan | lainnya
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profile_setup (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT          NOT NULL UNIQUE,
            profile_type    VARCHAR(30)  DEFAULT 'lainnya',
            profile_emoji   VARCHAR(10)  DEFAULT '👤',
            focus_areas     JSON,
            work_hours_start TIME        DEFAULT '08:00:00',
            work_hours_end   TIME        DEFAULT '17:00:00',
            sleep_time      TIME         DEFAULT '22:00:00',
            wake_time       TIME         DEFAULT '05:00:00',
            religion        VARCHAR(20)  DEFAULT NULL,
            timezone        VARCHAR(50)  DEFAULT 'Asia/Jakarta',
            setup_complete  BOOLEAN      DEFAULT FALSE,
            setup_step      TINYINT      DEFAULT 0,
            created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # ── level_rewards ──
    # Reward yang unlock per level (tema, fitur, badge)
    c.execute("""
        CREATE TABLE IF NOT EXISTS level_rewards (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            level       TINYINT      NOT NULL,
            reward_type VARCHAR(20)  NOT NULL,
            reward_key  VARCHAR(50)  NOT NULL,
            reward_name VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            UNIQUE KEY uniq_reward (level, reward_key)
        )
    """)

    conn.commit(); c.close(); conn.close()
    print("[DB] ✅ Sprint v4 tables ready")


def get_fail_streak(user_id):
    """Count consecutive days with 0 tasks done"""
    conn = get_connection()
    if not conn: return 0
    c = conn.cursor(dictionary=True)
    streak = 0
    for i in range(1, 8):
        d = date.today() - timedelta(days=i)
        c.execute("""
            SELECT COUNT(*) as done FROM daily_tasks
            WHERE user_id=%s AND task_date=%s AND status='done'
        """, (user_id, d))
        row = c.fetchone()
        if row and row['done'] == 0: streak += 1
        else: break
    c.close(); conn.close()
    return streak


def save_archetype(user_id, archetype, quiz_data):
    conn = get_connection()
    if not conn: return
    c = conn.cursor()
    import json
    c.execute("""
        INSERT INTO user_archetype (user_id, archetype, quiz_data)
        VALUES (%s,%s,%s)
        ON DUPLICATE KEY UPDATE archetype=%s, quiz_data=%s
    """, (user_id, archetype, json.dumps(quiz_data), archetype, json.dumps(quiz_data)))
    conn.commit(); c.close(); conn.close()


def get_archetype(user_id):
    conn = get_connection()
    if not conn: return None
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM user_archetype WHERE user_id=%s", (user_id,))
    row = c.fetchone()
    c.close(); conn.close()
    return row


def get_ghost_data(user_id):
    """Get current week vs last week task completion per day"""
    conn = get_connection()
    if not conn: return {'current': [], 'ghost': []}
    c = conn.cursor(dictionary=True)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    def get_week(start):
        result = []
        for i in range(7):
            d = start + timedelta(days=i)
            c.execute("""
                SELECT COUNT(*) as total, SUM(status='done') as done,
                       IFNULL(SUM(duration_min),0) as minutes
                FROM daily_tasks WHERE user_id=%s AND task_date=%s
            """, (user_id, d))
            row = c.fetchone()
            result.append({
                'date': d.isoformat(),
                'day': d.strftime('%a'),
                'done': int(row['done'] or 0),
                'total': int(row['total'] or 0),
                'minutes': int(row['minutes'] or 0)
            })
        return result

    current = get_week(week_start)
    ghost   = get_week(week_start - timedelta(weeks=1))
    c.close(); conn.close()
    return {'current': current, 'ghost': ghost}

# ─── SCHEDULED TASK HELPERS ────────────────────────────────────────────────────
def get_tasks_with_schedule(user_id, task_date=None):
    """Get tasks that have start_time set for today"""
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    if task_date is None: task_date = date.today()
    c.execute("""
        SELECT t.*, u.username, u.full_name,
               CONCAT(t.task_date,' ',t.start_time) as start_datetime,
               CONCAT(t.task_date,' ',t.end_time)   as end_datetime
        FROM daily_tasks t
        JOIN users u ON u.id = t.user_id
        WHERE t.user_id=%s AND t.task_date=%s
          AND t.start_time IS NOT NULL
          AND t.status NOT IN ('done','cancelled')
        ORDER BY t.start_time ASC
    """, (user_id, task_date))
    rows = c.fetchall()
    for r in rows:
        if r.get('task_date'):    r['task_date']    = r['task_date'].isoformat()
        if r.get('start_time'):   r['start_time']   = str(r['start_time'])
        if r.get('end_time'):     r['end_time']      = str(r['end_time'])
        if r.get('created_at'):   r['created_at']   = str(r['created_at'])
        if r.get('updated_at'):   r['updated_at']   = str(r['updated_at'])
    c.close(); conn.close()
    return rows


def get_all_scheduled_tasks_today():
    """Get ALL users' scheduled tasks for today — used by APScheduler"""
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    today = date.today()
    c.execute("""
        SELECT t.id, t.title, t.start_time, t.end_time, t.status,
               t.user_id, t.task_date,
               u.full_name, u.username
        FROM daily_tasks t
        JOIN users u ON u.id = t.user_id
        WHERE t.task_date=%s
          AND t.start_time IS NOT NULL
          AND t.status NOT IN ('done','cancelled')
        ORDER BY t.user_id, t.start_time
    """, (today,))
    rows = c.fetchall()
    for r in rows:
        if r.get('start_time'): r['start_time'] = str(r['start_time'])
        if r.get('end_time'):   r['end_time']   = str(r['end_time'])
        if r.get('task_date'):  r['task_date']  = r['task_date'].isoformat()
    c.close(); conn.close()
    return rows


def get_push_subscriptions_for_user(user_id):
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT endpoint, p256dh, auth_key
        FROM push_subscriptions WHERE user_id=%s
    """, (user_id,))
    rows = c.fetchall()
    c.close(); conn.close()
    return rows


# ─── ADMIN FUNCTIONS ───────────────────────────────────────────────────────────

def get_all_users():
    """Admin: ambil semua user."""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.full_name, u.is_admin,
                   u.failed_attempts, u.locked_until, u.last_login, u.created_at,
                   u.avatar_url,
                   (SELECT COUNT(*) FROM daily_tasks WHERE user_id=u.id) as task_count,
                   (SELECT current_streak FROM activity_streaks WHERE user_id=u.id LIMIT 1) as streak
            FROM users u ORDER BY u.created_at DESC
        """)
        return cursor.fetchall()
    finally:
        cursor.close(); conn.close()

def admin_reset_password(target_user_id, new_password, admin_id, ip=None):
    """Admin: reset password user lain."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor(dictionary=True)
    try:
        # Verify admin
        cursor.execute("SELECT is_admin FROM users WHERE id=%s", (admin_id,))
        row = cursor.fetchone()
        if not row or not row['is_admin']:
            return False
        # Update password + unlock account
        new_hash = hash_password(new_password)
        cursor.execute("""
            UPDATE users SET password=%s, failed_attempts=0, locked_until=NULL WHERE id=%s
        """, (new_hash, target_user_id))
        _log_activity(cursor, admin_id, 'admin_reset_password', ip, f'reset user_id={target_user_id}')
        conn.commit()
        return True
    except Exception as e:
        print(f'[admin_reset_password] error: {e}')
        return False
    finally:
        cursor.close(); conn.close()

def admin_toggle_lock(target_user_id, lock, admin_id):
    """Admin: lock/unlock akun user."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        if lock:
            from datetime import timedelta
            locked_until = datetime.now() + timedelta(days=365)
        else:
            locked_until = None
        cursor.execute("UPDATE users SET locked_until=%s, failed_attempts=0 WHERE id=%s",
                       (locked_until, target_user_id))
        _log_activity(cursor, admin_id, 'admin_lock' if lock else 'admin_unlock',
                      detail=f'user_id={target_user_id}')
        conn.commit()
        return True
    finally:
        cursor.close(); conn.close()

def admin_toggle_admin(target_user_id, is_admin, admin_id):
    """Admin: promote/demote user jadi admin."""
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_admin=%s WHERE id=%s", (is_admin, target_user_id))
        _log_activity(cursor, admin_id, 'admin_promote' if is_admin else 'admin_demote',
                      detail=f'user_id={target_user_id}')
        conn.commit()
        return True
    finally:
        cursor.close(); conn.close()

def get_login_logs(limit=10, offset=0, q='', log_type='', date_from='', date_to=''):
    """Admin: ambil activity log dengan filter + pagination."""
    conn = get_connection()
    if not conn: return [], 0
    cursor = conn.cursor(dictionary=True)
    try:
        where = ["1=1"]
        params = []
        if q:
            where.append("u.username LIKE %s")
            params.append(f"%{q}%")
        if log_type == 'admin':
            where.append("l.action LIKE 'admin%'")
        elif log_type:
            where.append("l.action = %s")
            params.append(log_type)
        if date_from:
            where.append("DATE(l.created_at) >= %s")
            params.append(date_from)
        if date_to:
            where.append("DATE(l.created_at) <= %s")
            params.append(date_to)

        where_str = " AND ".join(where)

        # Count total
        cursor.execute(f"""
            SELECT COUNT(*) as total FROM login_logs l
            LEFT JOIN users u ON l.user_id = u.id
            WHERE {where_str}
        """, params)
        row = cursor.fetchone()
        total = row['total'] if row else 0

        # Fetch page
        cursor.execute(f"""
            SELECT l.*, u.username FROM login_logs l
            LEFT JOIN users u ON l.user_id = u.id
            WHERE {where_str}
            ORDER BY l.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cursor.fetchall()
        for r in rows:
            if r.get('created_at'):
                r['created_at'] = r['created_at'].isoformat()
        return rows, total
    finally:
        cursor.close(); conn.close()

def get_user_by_id_admin(user_id):
    """Admin: get user detail by id."""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id,username,email,full_name,is_admin,failed_attempts,
                   locked_until,last_login,created_at
            FROM users WHERE id=%s
        """, (user_id,))
        return cursor.fetchone()
    finally:
        cursor.close(); conn.close()


# ══════════════════════════════════════════════════
# REMINDER HELPERS
# ══════════════════════════════════════════════════

# Tier system berdasarkan streak
STREAK_TIERS = [
    (1000, 'immortal',    '#F9CB42', '🌟'),
    (500,  'legend',      '#97C459', '⚡'),
    (365,  'setahun',     '#7F77DD', '👑'),
    (200,  'master',      '#534AB7', '🔮'),
    (100,  'century',     '#378ADD', '🌊'),
    (50,   'disiplin',    '#1D9E75', '💎'),
    (30,   'momentum',    '#639922', '⚡'),
    (10,   'konsisten',   '#EF9F27', '🔥'),
    (1,    'pemula',      '#888780', '🌱'),
]

def get_streak_tier(streak: int) -> tuple:
    """Return (tier_name, tier_color, tier_emoji) based on streak count."""
    for min_days, name, color, emoji in STREAK_TIERS:
        if streak >= min_days:
            return name, color, emoji
    return 'pemula', '#888780', '🌱'


def get_reminders(user_id: int) -> list:
    """Ambil semua reminder aktif milik user beserta streak-nya."""
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT r.*,
               COALESCE(rs.current_streak, 0)  AS current_streak,
               COALESCE(rs.longest_streak, 0)  AS longest_streak,
               COALESCE(rs.total_done, 0)       AS total_done,
               COALESCE(rs.tier, 'pemula')      AS tier,
               COALESCE(rs.tier_color, '#888780') AS tier_color,
               rs.last_done_date
        FROM   reminders r
        LEFT JOIN reminder_streaks rs ON rs.reminder_id = r.id
        WHERE  r.user_id = %s
        ORDER  BY r.sort_order, r.remind_time
    """, (user_id,))
    rows = c.fetchall()
    for row in rows:
        if row.get('remind_time'):
            row['remind_time'] = str(row['remind_time'])
        if row.get('last_done_date'):
            row['last_done_date'] = row['last_done_date'].isoformat()                 if hasattr(row['last_done_date'], 'isoformat') else str(row['last_done_date'])
    c.close(); conn.close()
    return rows


def get_today_reminder_logs(user_id: int, date_str: str = None) -> dict:
    """Return dict {reminder_id: log_row} untuk tanggal tertentu."""
    from datetime import date
    d = date_str or date.today().isoformat()
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT * FROM reminder_logs
        WHERE  user_id = %s AND log_date = %s
    """, (user_id, d))
    rows = c.fetchall()
    c.close(); conn.close()
    result = {}
    for row in rows:
        if row.get('completed_at'):
            row['completed_at'] = row['completed_at'].isoformat()
        if row.get('snoozed_until'):
            row['snoozed_until'] = row['snoozed_until'].isoformat()
        result[row['reminder_id']] = row
    return result


def complete_reminder(reminder_id: int, user_id: int,
                      quantity_done=None, note=None) -> dict:
    """Tandai reminder selesai hari ini + update streak."""
    from datetime import date, timedelta
    today = date.today()
    conn = get_connection()
    if not conn: return {'ok': False, 'error': 'DB'}
    c = conn.cursor(dictionary=True)
    try:
        # Upsert log
        c.execute("""
            INSERT INTO reminder_logs
                (reminder_id, user_id, log_date, completed_at, quantity_done, note)
            VALUES (%s, %s, %s, NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE
                completed_at  = NOW(),
                quantity_done = VALUES(quantity_done),
                note          = VALUES(note)
        """, (reminder_id, user_id, today, quantity_done, note))

        # Update streak
        c.execute("""
            SELECT current_streak, longest_streak, total_done, last_done_date
            FROM   reminder_streaks WHERE reminder_id = %s
        """, (reminder_id,))
        rs = c.fetchone()

        yesterday = (today - timedelta(days=1)).isoformat()
        today_str  = today.isoformat()

        if rs:
            last = rs['last_done_date']
            last_str = last.isoformat() if hasattr(last, 'isoformat') else str(last) if last else None
            if last_str == today_str:
                # Sudah done hari ini sebelumnya — tidak ubah streak
                new_streak = rs['current_streak']
            elif last_str == yesterday:
                new_streak = rs['current_streak'] + 1
            else:
                new_streak = 1
            new_longest  = max(rs['longest_streak'], new_streak)
            new_total    = rs['total_done'] + (0 if last_str == today_str else 1)
        else:
            new_streak = new_longest = new_total = 1

        tier, color, _ = get_streak_tier(new_streak)

        c.execute("""
            INSERT INTO reminder_streaks
                (reminder_id, user_id, current_streak, longest_streak,
                 total_done, last_done_date, tier, tier_color)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                current_streak = VALUES(current_streak),
                longest_streak = VALUES(longest_streak),
                total_done     = VALUES(total_done),
                last_done_date = VALUES(last_done_date),
                tier           = VALUES(tier),
                tier_color     = VALUES(tier_color)
        """, (reminder_id, user_id, new_streak, new_longest,
              new_total, today_str, tier, color))

        conn.commit()
        # Award XP
        xp_source = f'streak_{new_streak}' if new_streak in (10,30,50,100,200,365,500,1000) else 'reminder_done'
        award_xp(user_id, xp_source, f'Reminder #{reminder_id}', reminder_id)
        return {
            'ok': True,
            'streak': new_streak,
            'longest': new_longest,
            'tier': tier,
            'tier_color': color,
            'milestone': new_streak in (10,30,50,100,200,365,500,1000)
        }
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}
    finally:
        c.close(); conn.close()


def uncheck_reminder(reminder_id: int, user_id: int) -> bool:
    """Batalkan centang reminder hari ini + rollback streak."""
    from datetime import date, timedelta
    today = date.today().isoformat()
    conn = get_connection()
    if not conn: return False
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""
            UPDATE reminder_logs
            SET completed_at = NULL, quantity_done = NULL
            WHERE reminder_id = %s AND user_id = %s AND log_date = %s
        """, (reminder_id, user_id, today))

        # Rollback streak — kurangi 1 jika last_done_date = today
        c.execute("""
            SELECT current_streak, longest_streak, total_done
            FROM reminder_streaks WHERE reminder_id = %s
        """, (reminder_id,))
        rs = c.fetchone()
        if rs and rs['current_streak'] > 0:
            new_streak = rs['current_streak'] - 1
            new_total  = max(0, rs['total_done'] - 1)
            tier, color, _ = get_streak_tier(new_streak)
            yesterday = (date.today() - __import__('datetime').timedelta(days=1)).isoformat()
            c.execute("""
                UPDATE reminder_streaks
                SET current_streak = %s, total_done = %s,
                    last_done_date = %s, tier = %s, tier_color = %s
                WHERE reminder_id = %s
            """, (new_streak, new_total, yesterday if new_streak > 0 else None,
                  tier, color, reminder_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        c.close(); conn.close()


def get_reminder_templates(category: str = None) -> list:
    """Ambil template library."""
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    if category:
        c.execute("""
            SELECT * FROM reminder_templates
            WHERE (is_builtin = TRUE OR user_id IS NULL)
              AND category = %s
            ORDER BY is_builtin DESC, use_count DESC
        """, (category,))
    else:
        c.execute("""
            SELECT * FROM reminder_templates
            WHERE is_builtin = TRUE OR user_id IS NULL
            ORDER BY category, is_builtin DESC, use_count DESC
        """)
    rows = c.fetchall()
    import json
    for row in rows:
        if isinstance(row.get('template_data'), str):
            try: row['template_data'] = json.loads(row['template_data'])
            except: pass
    c.close(); conn.close()
    return rows


def install_template(template_id: int, user_id: int) -> list:
    """Install template — buat semua reminder sekaligus, return list id."""
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    import json
    c.execute("SELECT * FROM reminder_templates WHERE id = %s", (template_id,))
    tpl = c.fetchone()
    if not tpl:
        c.close(); conn.close()
        return []
    items = tpl['template_data']
    if isinstance(items, str):
        items = json.loads(items)

    created_ids = []
    for item in items:
        c.execute("""
            INSERT INTO reminders
                (user_id, title, emoji, remind_time, repeat_type,
                 snooze_minutes, has_quantity, quantity_target,
                 quantity_unit, category, color)
            VALUES (%s,%s,%s,%s,'daily',%s,%s,%s,%s,%s,%s)
        """, (
            user_id,
            item.get('title', 'Reminder'),
            item.get('emoji', '🔔'),
            item.get('remind_time', '08:00'),
            item.get('snooze_minutes', 30),
            item.get('has_quantity', False),
            item.get('quantity_target'),
            item.get('quantity_unit'),
            item.get('category', 'general'),
            item.get('color', '#6366f1'),
        ))
        created_ids.append(c.lastrowid)

    # Increment use_count
    c.execute("UPDATE reminder_templates SET use_count = use_count + 1 WHERE id = %s",
              (template_id,))
    conn.commit()
    c.close(); conn.close()
    return created_ids


# ══════════════════════════════════════════════════════════
# XP / LEVEL SYSTEM
# ══════════════════════════════════════════════════════════

XP_LEVELS = [
    (1,    0,    100,  'Pemula',       '#888780'),
    (2,    100,  250,  'Penjelajah',   '#EF9F27'),
    (3,    250,  500,  'Konsisten',    '#639922'),
    (4,    500,  900,  'Disiplin',     '#1D9E75'),
    (5,    900,  1500, 'Produktif',    '#378ADD'),
    (6,    1500, 2500, 'Andal',        '#534AB7'),
    (7,    2500, 4000, 'Mahir',        '#D4537E'),
    (8,    4000, 6000, 'Ahli',         '#D85A30'),
    (9,    6000, 9000, 'Master',       '#d4af37'),
    (10,   9000, 9999999, 'Grand Master', '#7F77DD'),
]

XP_REWARDS = {
    'task_done':         10,
    'reminder_done':     8,
    'streak_10':         50,
    'streak_30':         150,
    'streak_50':         300,
    'streak_100':        600,
    'streak_200':        1000,
    'streak_365':        2000,
    'saving_deposit':    15,
    'goal_completed':    500,
    'isq_filled':        20,
    'login_streak_7':    75,
    'weekly_review':     30,
    'investment_added':  25,
}

def get_level_info(total_xp: int) -> dict:
    for lvl, xp_min, xp_max, title, color in XP_LEVELS:
        if total_xp < xp_max:
            return {
                'level': lvl, 'title': title, 'color': color,
                'total_xp': total_xp, 'xp_min': xp_min,
                'xp_max': xp_max, 'xp_to_next': xp_max - total_xp,
                'pct': round((total_xp - xp_min) / (xp_max - xp_min) * 100)
                       if xp_max > xp_min else 100
            }
    last = XP_LEVELS[-1]
    return {'level': last[0], 'title': last[3], 'color': last[4],
            'total_xp': total_xp, 'xp_min': last[1], 'xp_max': last[2],
            'xp_to_next': 0, 'pct': 100}


def award_xp(user_id: int, source: str, description: str = '',
             ref_id: int = None) -> dict:
    """Beri XP ke user dan update level. Return {'xp', 'leveled_up', 'new_level'}."""
    amount = XP_REWARDS.get(source, 5)
    conn = get_connection()
    if not conn: return {'xp': 0, 'leveled_up': False}
    c = conn.cursor(dictionary=True)
    try:
        # Log XP
        c.execute("""
            INSERT INTO xp_logs (user_id, xp_amount, source, description, ref_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, amount, source, description, ref_id))

        # Upsert user_xp
        c.execute("""
            INSERT INTO user_xp (user_id, total_xp)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE total_xp = total_xp + %s
        """, (user_id, amount, amount))

        # Get new total
        c.execute("SELECT total_xp FROM user_xp WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        new_total = row['total_xp'] if row else amount

        # Update level info
        info = get_level_info(new_total)
        c.execute("""
            UPDATE user_xp SET level=%s, level_title=%s, level_color=%s, xp_to_next=%s
            WHERE user_id=%s
        """, (info['level'], info['title'], info['color'], info['xp_to_next'], user_id))

        conn.commit()
        return {
            'xp': amount,
            'total_xp': new_total,
            'level': info['level'],
            'level_title': info['title'],
            'leveled_up': False,  # caller can check by comparing before/after
        }
    except Exception as e:
        conn.rollback()
        return {'xp': 0, 'leveled_up': False, 'error': str(e)}
    finally:
        c.close(); conn.close()


def get_user_xp(user_id: int) -> dict:
    conn = get_connection()
    if not conn: return get_level_info(0)
    c = conn.cursor(dictionary=True)
    try:
        c.execute("SELECT total_xp FROM user_xp WHERE user_id=%s", (user_id,))
        row = c.fetchone()
        total = row['total_xp'] if row else 0
        return get_level_info(total)
    finally:
        c.close(); conn.close()


# ══════════════════════════════════════════════════════════
# GOAL PROGRESS (linked reminders + tasks)
# ══════════════════════════════════════════════════════════

def get_goal_linked_stats(goal_id: int, user_id: int) -> dict:
    """Hitung progress goal dari reminder + tasks yang terhubung."""
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        from datetime import date, timedelta
        today = date.today()
        month_start = today.replace(day=1)

        # Reminders linked to this goal
        c.execute("""
            SELECT r.id, r.title, r.emoji,
                   COALESCE(rs.current_streak, 0) AS streak,
                   COALESCE(rs.total_done, 0) AS total_done,
                   COALESCE(rs.tier, 'pemula') AS tier,
                   COALESCE(rs.tier_color, '#888780') AS tier_color
            FROM reminders r
            LEFT JOIN reminder_streaks rs ON rs.reminder_id = r.id
            WHERE r.goal_id = %s AND r.user_id = %s AND r.is_active = 1
        """, (goal_id, user_id))
        reminders = c.fetchall()

        # Tasks linked to this goal this month
        c.execute("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
            FROM daily_tasks
            WHERE goal_id=%s AND user_id=%s AND task_date >= %s
        """, (goal_id, user_id, month_start))
        task_row = c.fetchone()

        # Savings linked to this goal
        c.execute("""
            SELECT sg.title, sg.target_amount, sg.currency,
                   COALESCE(SUM(sl.amount),0) AS saved
            FROM savings_goals sg
            LEFT JOIN saving_logs sl ON sl.savings_goal_id = sg.id
            WHERE sg.goal_id=%s AND sg.user_id=%s AND sg.is_active=1
            GROUP BY sg.id
        """, (goal_id, user_id))
        savings = c.fetchall()
        for s in savings:
            s['target_amount'] = float(s['target_amount'])
            s['saved'] = float(s['saved'])

        return {
            'reminders': reminders,
            'task_total': task_row['total'] if task_row else 0,
            'task_done':  task_row['done']  if task_row else 0,
            'savings':    savings,
        }
    finally:
        c.close(); conn.close()


# ══════════════════════════════════════════════════════════
# DAILY FOCUS GENERATOR
# ══════════════════════════════════════════════════════════

def generate_daily_focus(user_id: int) -> list:
    """Generate 3 prioritas hari ini berdasarkan data existing."""
    from datetime import date, timedelta
    today = date.today()
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    candidates = []

    try:
        # 1. Milestone deadline mendekat (< 14 hari)
        c.execute("""
            SELECT m.id, m.title, m.year, m.month,
                   g.title AS goal_title, g.color
            FROM milestones m
            JOIN goals g ON m.goal_id = g.id
            WHERE m.user_id = %s AND m.is_completed = 0
              AND (m.year * 100 + m.month) <= %s
            ORDER BY m.year, m.month LIMIT 3
        """, (user_id, int(today.strftime('%Y%m'))))
        for row in c.fetchall():
            candidates.append({
                'source': 'milestone_deadline',
                'title': f"Milestone: {row['title']}",
                'description': f"Bagian dari goal '{row['goal_title']}' · Deadline bulan ini",
                'ref_type': 'milestone', 'ref_id': row['id'],
                'priority': 10
            })

        # 2. Reminder streak yang hampir putus (done kemarin, belum hari ini)
        yesterday = (today - timedelta(days=1)).isoformat()
        c.execute("""
            SELECT r.id, r.title, r.emoji,
                   COALESCE(rs.current_streak, 0) AS streak
            FROM reminders r
            LEFT JOIN reminder_streaks rs ON rs.reminder_id = r.id
            LEFT JOIN reminder_logs rl
                ON rl.reminder_id = r.id AND rl.log_date = %s
            WHERE r.user_id = %s AND r.is_active = 1
              AND rs.last_done_date = %s
              AND (rl.completed_at IS NULL OR rl.reminder_id IS NULL)
            ORDER BY rs.current_streak DESC LIMIT 3
        """, (today.isoformat(), user_id, yesterday))
        for row in c.fetchall():
            streak = row['streak']
            candidates.append({
                'source': 'streak_risk',
                'title': f"{row['emoji']} {row['title']}",
                'description': f"Streak {streak} hari akan putus kalau tidak selesai hari ini!",
                'ref_type': 'reminder', 'ref_id': row['id'],
                'priority': 9 + min(streak / 10, 0.9)
            })

        # 3. Task overdue dari kemarin
        c.execute("""
            SELECT id, title, priority, task_date
            FROM daily_tasks
            WHERE user_id=%s AND status IN ('todo','in_progress')
              AND task_date < %s
            ORDER BY
              FIELD(priority,'urgent','high','medium','low'),
              task_date ASC
            LIMIT 3
        """, (user_id, today.isoformat()))
        for row in c.fetchall():
            prio_map = {'urgent': 8, 'high': 7, 'medium': 6, 'low': 5}
            candidates.append({
                'source': 'task_overdue',
                'title': f"📋 {row['title']}",
                'description': f"Task tertunda dari {row['task_date']} · Prioritas {row['priority']}",
                'ref_type': 'task', 'ref_id': row['id'],
                'priority': prio_map.get(row['priority'], 6)
            })

        # 4. Savings goal yang belum diisi minggu ini
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        c.execute("""
            SELECT sg.id, sg.title, sg.emoji, sg.period_amount, sg.currency
            FROM savings_goals sg
            WHERE sg.user_id=%s AND sg.is_active=1 AND sg.period='weekly'
              AND sg.id NOT IN (
                  SELECT DISTINCT savings_goal_id FROM saving_logs
                  WHERE user_id=%s AND log_date >= %s
              )
            LIMIT 2
        """, (user_id, user_id, week_start))
        for row in c.fetchall():
            candidates.append({
                'source': 'saving_due',
                'title': f"{row['emoji']} Setor tabungan: {row['title']}",
                'description': f"Belum setor minggu ini · Target {row['currency']} {row['period_amount']:,.0f}",
                'ref_type': 'savings', 'ref_id': row['id'],
                'priority': 7
            })

        # Sort by priority, take top 3
        candidates.sort(key=lambda x: x['priority'], reverse=True)
        top3 = candidates[:3]

        # Upsert to daily_focus table
        c.execute("DELETE FROM daily_focus WHERE user_id=%s AND focus_date=%s",
                  (user_id, today))
        for i, item in enumerate(top3, 1):
            c.execute("""
                INSERT INTO daily_focus
                    (user_id, focus_date, rank, source, title, description, ref_type, ref_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, today, i, item['source'], item['title'],
                  item['description'], item['ref_type'], item['ref_id']))

        conn.commit()
        return top3

    except Exception as e:
        print(f"[daily_focus] error: {e}")
        return []
    finally:
        c.close(); conn.close()


def get_daily_focus(user_id: int) -> list:
    """Ambil daily focus hari ini. Generate jika belum ada."""
    from datetime import date
    today = date.today().isoformat()
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""
            SELECT * FROM daily_focus
            WHERE user_id=%s AND focus_date=%s
            ORDER BY rank
        """, (user_id, today))
        rows = c.fetchall()
        if not rows:
            c.close(); conn.close()
            return generate_daily_focus(user_id)
        for r in rows:
            if r.get('focus_date'):
                r['focus_date'] = r['focus_date'].isoformat()
        return rows
    finally:
        c.close(); conn.close()


# ══════════════════════════════════════════════════════════
# FINANCIAL HELPERS
# ══════════════════════════════════════════════════════════

def get_savings_summary(user_id: int) -> dict:
    """Ringkasan tabungan semua goals dalam IDR."""
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""
            SELECT sg.*,
                   COALESCE(SUM(sl.amount * COALESCE(cur.rate_to_idr,1)), 0) AS saved_idr,
                   COALESCE(ss.current_streak, 0) AS streak,
                   COALESCE(ss.tier, 'pemula') AS tier,
                   COALESCE(ss.tier_color, '#888780') AS tier_color
            FROM savings_goals sg
            LEFT JOIN saving_logs sl ON sl.savings_goal_id = sg.id
                AND sl.type = 'deposit'
            LEFT JOIN currencies cur ON cur.code = sg.currency
            LEFT JOIN saving_streaks ss ON ss.savings_goal_id = sg.id
            WHERE sg.user_id = %s AND sg.is_active = 1
            GROUP BY sg.id
            ORDER BY sg.created_at DESC
        """, (user_id,))
        goals = c.fetchall()
        for g in goals:
            g['target_amount'] = float(g['target_amount'])
            g['saved_idr']     = float(g['saved_idr'])
            g['period_amount'] = float(g['period_amount'] or 0)
            pct = round(g['saved_idr'] / (g['target_amount'] or 1) * 100)
            g['pct'] = min(pct, 100)
            if g.get('start_date'):
                g['start_date'] = g['start_date'].isoformat()
            if g.get('target_date'):
                g['target_date'] = g['target_date'].isoformat()
        return {'goals': goals, 'total_goals': len(goals)}
    finally:
        c.close(); conn.close()


def add_saving_log(savings_goal_id: int, user_id: int,
                   amount: float, currency: str,
                   log_date: str, log_type: str = 'deposit',
                   note: str = '') -> dict:
    """Catat setoran tabungan + update streak + award XP."""
    conn = get_connection()
    if not conn: return {'ok': False}
    c = conn.cursor(dictionary=True)
    try:
        from datetime import date, timedelta
        c.execute("""
            INSERT INTO saving_logs
                (savings_goal_id, user_id, amount, currency, log_date, type, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (savings_goal_id, user_id, amount, currency, log_date, log_type, note))

        # Update saving streak (weekly)
        if log_type == 'deposit':
            log_d   = date.fromisoformat(log_date)
            # Get ISO week string e.g. "2026-W14"
            week_str = f"{log_d.isocalendar()[0]}-W{log_d.isocalendar()[1]:02d}"

            c.execute("""
                SELECT current_streak, longest_streak, total_periods, last_period
                FROM saving_streaks WHERE savings_goal_id=%s
            """, (savings_goal_id,))
            ss = c.fetchone()
            if ss:
                last = ss['last_period']
                # Compute previous week
                prev_week_d = log_d - timedelta(weeks=1)
                prev_week   = f"{prev_week_d.isocalendar()[0]}-W{prev_week_d.isocalendar()[1]:02d}"
                if last == week_str:
                    new_streak = ss['current_streak']
                    new_total  = ss['total_periods']
                elif last == prev_week:
                    new_streak = ss['current_streak'] + 1
                    new_total  = ss['total_periods'] + 1
                else:
                    new_streak = 1
                    new_total  = ss['total_periods'] + 1
                new_longest = max(ss['longest_streak'], new_streak)
            else:
                new_streak = new_longest = new_total = 1

            tier, color, _ = get_streak_tier(new_streak)
            c.execute("""
                INSERT INTO saving_streaks
                    (savings_goal_id, user_id, current_streak, longest_streak,
                     total_periods, last_period, tier, tier_color)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    current_streak=VALUES(current_streak),
                    longest_streak=VALUES(longest_streak),
                    total_periods=VALUES(total_periods),
                    last_period=VALUES(last_period),
                    tier=VALUES(tier), tier_color=VALUES(tier_color)
            """, (savings_goal_id, user_id, new_streak, new_longest,
                  new_total, week_str, tier, color))

        conn.commit()
        # Award XP
        award_xp(user_id, 'saving_deposit', f'Setor tabungan #{savings_goal_id}', savings_goal_id)
        return {'ok': True}
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}
    finally:
        c.close(); conn.close()


def get_portfolio_summary(user_id: int) -> dict:
    """Ringkasan portofolio investasi."""
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""
            SELECT i.*,
                   (i.buy_price * i.units * COALESCE(bc.rate_to_idr,1)) AS modal_idr,
                   (COALESCE(i.current_price, i.buy_price) * i.units
                    * COALESCE(bc.rate_to_idr,1)) AS nilai_idr
            FROM investments i
            LEFT JOIN currencies bc ON bc.code = i.currency
            WHERE i.user_id=%s AND i.is_active=1
            ORDER BY i.buy_date DESC
        """, (user_id,))
        items = c.fetchall()
        total_modal = 0
        total_nilai = 0
        for inv in items:
            inv['modal_idr'] = float(inv['modal_idr'] or 0)
            inv['nilai_idr'] = float(inv['nilai_idr'] or 0)
            inv['buy_price'] = float(inv['buy_price'])
            inv['units']     = float(inv['units'])
            inv['current_price'] = float(inv['current_price'] or inv['buy_price'])
            pnl = inv['nilai_idr'] - inv['modal_idr']
            inv['pnl_idr']  = round(pnl, 2)
            inv['pnl_pct']  = round(pnl / inv['modal_idr'] * 100, 2) if inv['modal_idr'] else 0
            if inv.get('buy_date'):
                inv['buy_date'] = inv['buy_date'].isoformat()
            total_modal += inv['modal_idr']
            total_nilai += inv['nilai_idr']

        total_pnl = total_nilai - total_modal
        return {
            'investments': items,
            'total_modal': round(total_modal, 2),
            'total_nilai': round(total_nilai, 2),
            'total_pnl':   round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl / total_modal * 100, 2) if total_modal else 0,
        }
    finally:
        c.close(); conn.close()


# ══════════════════════════════════════════════════════
# KANBAN HELPERS
# ══════════════════════════════════════════════════════

BOARD_THEMES = {
    'default':  {'todo':'#888780','doing':'#378ADD','done':'#10b981'},
    'forest':   {'todo':'#9FE1CB','doing':'#1D9E75','done':'#085041'},
    'sunset':   {'todo':'#FAC775','doing':'#EF9F27','done':'#854F0B'},
    'ocean':    {'todo':'#85B7EB','doing':'#185FA5','done':'#042C53'},
    'cherry':   {'todo':'#F4C0D1','doing':'#D4537E','done':'#4B1528'},
    'minimal':  {'todo':'#D3D1C7','doing':'#5F5E5A','done':'#2C2C2A'},
    'gold':     {'todo':'#FAC775','doing':'#d4af37','done':'#412402'},
}

import secrets as _secrets

def create_board(user_id: int, title: str, description: str = '',
                 emoji: str = '📋', theme: str = 'default',
                 visibility: str = 'private', board_type: str = 'personal',
                 goal_id: int = None) -> dict:
    """Create board with default 3 columns."""
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        invite = None
        if visibility in ('team', 'public'):
            invite = _secrets.token_hex(4).upper()

        c.execute("""
            INSERT INTO boards
                (user_id, goal_id, title, description, emoji, theme,
                 visibility, type, invite_code)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, goal_id, title, description, emoji, theme,
               visibility, board_type, invite))
        board_id = c.lastrowid

        # Default columns
        theme_colors = BOARD_THEMES.get(theme, BOARD_THEMES['default'])
        cols = [
            ('To Do',  theme_colors['todo'],  0),
            ('Doing',  theme_colors['doing'], 1),
            ('Done',   theme_colors['done'],  2),
        ]
        for col_title, color, order in cols:
            c.execute("""
                INSERT INTO board_columns (board_id, title, color, sort_order)
                VALUES (%s,%s,%s,%s)
            """, (board_id, col_title, color, order))

        # Add creator as owner member
        c.execute("""
            INSERT INTO board_members (board_id, user_id, role)
            VALUES (%s,%s,'owner')
        """, (board_id, user_id))

        conn.commit()
        return {'id': board_id, 'invite_code': invite}
    except Exception as e:
        conn.rollback()
        return {'error': str(e)}
    finally:
        c.close(); conn.close()


def get_boards(user_id: int) -> list:
    """Get all boards accessible by user (owned + member)."""
    conn = get_connection()
    if not conn: return []
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""
            SELECT DISTINCT b.*,
                   bm.role AS user_role,
                   (SELECT COUNT(*) FROM board_cards bc
                    WHERE bc.board_id = b.id AND bc.archived_at IS NULL) AS card_count,
                   (SELECT COUNT(*) FROM board_cards bc
                    WHERE bc.board_id = b.id AND bc.completed_at IS NOT NULL
                    AND bc.archived_at IS NULL) AS done_count
            FROM boards b
            JOIN board_members bm ON bm.board_id = b.id AND bm.user_id = %s
            WHERE b.is_active = 1
            ORDER BY b.sort_order, b.created_at DESC
        """, (user_id,))
        boards = c.fetchall()
        for b in boards:
            if b.get('created_at'):
                b['created_at'] = b['created_at'].isoformat()
        return boards
    finally:
        c.close(); conn.close()


def get_board_detail(board_id: int, user_id: int) -> dict:
    """Get full board with columns and cards."""
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        # Verify access
        c.execute("""
            SELECT b.*, bm.role AS user_role
            FROM boards b
            JOIN board_members bm ON bm.board_id = b.id AND bm.user_id = %s
            WHERE b.id = %s AND b.is_active = 1
        """, (user_id, board_id))
        board = c.fetchone()
        if not board: return {}

        # Get columns
        c.execute("""
            SELECT * FROM board_columns
            WHERE board_id = %s ORDER BY sort_order
        """, (board_id,))
        columns = c.fetchall()

        # Get cards per column
        for col in columns:
            c.execute("""
                SELECT bc.*,
                       u.username AS assigned_username,
                       u.full_name AS assigned_name,
                       (SELECT COUNT(*) FROM card_subtasks cs WHERE cs.card_id = bc.id) AS subtask_total,
                       (SELECT COUNT(*) FROM card_subtasks cs WHERE cs.card_id = bc.id AND cs.is_done=1) AS subtask_done,
                       (SELECT COUNT(*) FROM card_comments cc WHERE cc.card_id = bc.id) AS comment_count
                FROM board_cards bc
                LEFT JOIN users u ON u.id = bc.assigned_to
                WHERE bc.column_id = %s AND bc.archived_at IS NULL
                ORDER BY bc.sort_order, bc.created_at
            """, (col['id'],))
            cards = c.fetchall()
            for card in cards:
                for k in ['due_date','completed_at','created_at','updated_at']:
                    if card.get(k) and hasattr(card[k], 'isoformat'):
                        card[k] = card[k].isoformat()
            col['cards'] = cards

        # Get members
        c.execute("""
            SELECT bm.role, u.id, u.username, u.full_name, u.avatar_url
            FROM board_members bm
            JOIN users u ON u.id = bm.user_id
            WHERE bm.board_id = %s
        """, (board_id,))
        members = c.fetchall()

        board['columns'] = columns
        board['members'] = members
        if board.get('created_at') and hasattr(board['created_at'], 'isoformat'):
            board['created_at'] = board['created_at'].isoformat()
        return board
    finally:
        c.close(); conn.close()


def move_card(card_id: int, column_id: int, user_id: int, sort_order: int = 0) -> bool:
    """Move card to different column (drag & drop)."""
    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    try:
        # Check if column done → mark completed_at
        c.execute("""
            SELECT bc.title, bcol.title AS col_title
            FROM board_cards bc
            JOIN board_columns bcol ON bcol.id = %s
            WHERE bc.id = %s
        """, (column_id, card_id))
        row = c.fetchone()

        is_done_col = row and 'done' in (row[1] or '').lower() if row else False

        c.execute("""
            UPDATE board_cards
            SET column_id = %s, sort_order = %s,
                completed_at = %s
            WHERE id = %s
        """, (column_id, sort_order,
               'NOW()' if is_done_col else None, card_id))
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        c.close(); conn.close()


def generate_share_report(user_id: int, report_type: str) -> dict:
    """Generate shareable report token."""
    import json as _json
    from datetime import date, timedelta
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        token = _secrets.token_hex(16)
        expires = (date.today() + timedelta(days=7)).isoformat()

        # Gather data based on type
        data = {}
        if report_type == 'weekly_summary':
            c.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done
                FROM daily_tasks
                WHERE user_id=%s AND task_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """, (user_id,))
            tasks = c.fetchone()
            c.execute("""
                SELECT AVG(mood_score) as avg_mood
                FROM user_moods WHERE user_id=%s
                AND mood_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """, (user_id,))
            mood = c.fetchone()
            data = {
                'tasks_done': int(tasks['done'] or 0) if tasks else 0,
                'tasks_total': int(tasks['total'] or 0) if tasks else 0,
                'avg_mood': float(mood['avg_mood'] or 0) if mood else 0,
            }
        elif report_type == 'streak':
            c.execute("""
                SELECT r.title, r.emoji, rs.current_streak, rs.longest_streak, rs.tier
                FROM reminders r
                JOIN reminder_streaks rs ON rs.reminder_id = r.id
                WHERE r.user_id = %s AND r.is_active = 1
                ORDER BY rs.current_streak DESC LIMIT 5
            """, (user_id,))
            data = {'streaks': c.fetchall()}
        elif report_type == 'goal_progress':
            c.execute("""
                SELECT title, icon, color FROM goals
                WHERE user_id=%s AND is_active=1 LIMIT 5
            """, (user_id,))
            data = {'goals': c.fetchall()}

        c.execute("""
            INSERT INTO share_reports (user_id, type, data, share_token, expires_at)
            VALUES (%s,%s,%s,%s,%s)
        """, (user_id, report_type, _json.dumps(data), token, expires))
        conn.commit()
        return {'token': token, 'expires_at': expires}
    except Exception as e:
        conn.rollback()
        return {'error': str(e)}
    finally:
        c.close(); conn.close()


# ══════════════════════════════════════════════════════════
# ESQ HELPERS — VALUES + REFLECTIONS + SPIRITUAL
# ══════════════════════════════════════════════════════════

# Built-in spiritual activities
SPIRITUAL_ACTIVITIES = [
    ('sholat_subuh',  'Sholat Subuh',  '🌅', None, None),
    ('sholat_dzuhur', 'Sholat Dzuhur', '☀️',  None, None),
    ('sholat_ashar',  'Sholat Ashar',  '🌤',  None, None),
    ('sholat_maghrib','Sholat Maghrib','🌆', None, None),
    ('sholat_isya',   'Sholat Isya',   '🌙', None, None),
    ('quran',         'Baca Al-Quran', '📖', 1.0,  'halaman'),
    ('dzikir_pagi',   'Dzikir Pagi',   '🌿', None, None),
    ('dzikir_malam',  'Dzikir Malam',  '✨', None, None),
    ('tahajud',       'Sholat Tahajud','🌟', None, None),
    ('dhuha',         'Sholat Dhuha',  '🌞', None, None),
    ('sedekah',       'Sedekah',       '💝', None, None),
    ('puasa',         'Puasa Sunnah',  '🤲', None, None),
]

PROFILE_TYPES = {
    'pelajar':          ('🎒', 'Pelajar/Siswa',       ['belajar','kesehatan','ibadah']),
    'mahasiswa':        ('🎓', 'Mahasiswa',            ['akademik','produktivitas','ibadah']),
    'profesional':      ('💼', 'Profesional/Karyawan', ['karir','kesehatan','keluarga']),
    'ibu_rumah_tangga': ('🏠', 'Ibu Rumah Tangga',     ['keluarga','ibadah','kesehatan']),
    'wirausaha':        ('🚀', 'Wirausahawan',          ['bisnis','finansial','kesehatan']),
    'pensiunan':        ('🌸', 'Pensiunan',             ['kesehatan','ibadah','keluarga']),
    'lainnya':          ('👤', 'Lainnya',               ['produktivitas','kesehatan']),
}

LEVEL_SYSTEM = [
    (1,  0,     100,   'Pemula',       '#888780', '🌱'),
    (2,  100,   250,   'Penjelajah',   '#EF9F27', '🔍'),
    (3,  250,   500,   'Konsisten',    '#639922', '⚡'),
    (4,  500,   900,   'Disiplin',     '#1D9E75', '💎'),
    (5,  900,   1500,  'Produktif',    '#378ADD', '🌊'),
    (6,  1500,  2500,  'Andal',        '#534AB7', '🔮'),
    (7,  2500,  4000,  'Mahir',        '#D4537E', '🌸'),
    (8,  4000,  6000,  'Ahli',         '#D85A30', '🔥'),
    (9,  6000,  9000,  'Master',       '#d4af37', '👑'),
    (10, 9000,  99999, 'Grand Master', '#7F77DD', '🌟'),
]


def get_esq_today(user_id: int, date_str: str = None) -> dict:
    """Get today's ESQ data: morning, evening, spiritual log, reflection."""
    from datetime import date
    d = date_str or date.today().isoformat()
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        # Morning ISQ
        c.execute("SELECT * FROM isq_morning WHERE user_id=%s AND entry_date=%s",
                  (user_id, d))
        morning = c.fetchone()

        # Evening ISQ
        c.execute("SELECT * FROM isq_evening WHERE user_id=%s AND entry_date=%s",
                  (user_id, d))
        evening = c.fetchone()

        # Spiritual log
        c.execute("""SELECT * FROM esq_spiritual_log
                     WHERE user_id=%s AND log_date=%s ORDER BY activity""",
                  (user_id, d))
        spiritual = c.fetchall()
        spiritual_map = {s['activity']: s for s in spiritual}

        # Reflection
        c.execute("""SELECT * FROM esq_reflections
                     WHERE user_id=%s AND type='daily' AND reflection_date=%s""",
                  (user_id, d))
        reflection = c.fetchone()
        if reflection and reflection.get('reflection_date'):
            reflection['reflection_date'] = reflection['reflection_date'].isoformat()                 if hasattr(reflection['reflection_date'], 'isoformat') else str(reflection['reflection_date'])

        # User values
        c.execute("""SELECT * FROM esq_values
                     WHERE user_id=%s AND is_active=1 ORDER BY priority""",
                  (user_id,))
        values = c.fetchall()

        return {
            'morning': morning,
            'evening': evening,
            'spiritual': spiritual_map,
            'reflection': reflection,
            'values': values,
            'date': d,
        }
    finally:
        c.close(); conn.close()


def toggle_spiritual(user_id: int, activity: str, date_str: str,
                     label: str = None, quantity=None, unit: str = None) -> dict:
    """Toggle spiritual activity done/undone."""
    conn = get_connection()
    if not conn: return {'ok': False}
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""SELECT id, is_done FROM esq_spiritual_log
                     WHERE user_id=%s AND log_date=%s AND activity=%s""",
                  (user_id, date_str, activity))
        existing = c.fetchone()
        if existing:
            new_done = not existing['is_done']
            c.execute("""UPDATE esq_spiritual_log
                         SET is_done=%s, done_at=IF(%s,NOW(),NULL)
                         WHERE id=%s""",
                      (new_done, new_done, existing['id']))
        else:
            c.execute("""INSERT INTO esq_spiritual_log
                            (user_id, log_date, activity, label, is_done,
                             done_at, quantity, unit)
                         VALUES (%s,%s,%s,%s,TRUE,NOW(),%s,%s)""",
                      (user_id, date_str, activity, label, quantity, unit))
            new_done = True

        conn.commit()
        if new_done:
            award_xp(user_id, 'isq_filled', f'Ibadah: {activity}')
        return {'ok': True, 'is_done': new_done}
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}
    finally:
        c.close(); conn.close()


def save_reflection(user_id: int, date_str: str, content: str,
                    gratitude: str = None, lessons: str = None,
                    tomorrow_intent: str = None,
                    mood_score: int = 3, energy: int = 3,
                    ref_type: str = 'daily') -> dict:
    """Save or update daily/weekly reflection."""
    conn = get_connection()
    if not conn: return {'ok': False}
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO esq_reflections
                (user_id, type, reflection_date, content, gratitude,
                 lessons, tomorrow_intent, mood_score, energy)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                content=VALUES(content),
                gratitude=VALUES(gratitude),
                lessons=VALUES(lessons),
                tomorrow_intent=VALUES(tomorrow_intent),
                mood_score=VALUES(mood_score),
                energy=VALUES(energy)
        """, (user_id, ref_type, date_str, content, gratitude,
               lessons, tomorrow_intent, mood_score, energy))
        conn.commit()
        award_xp(user_id, 'isq_filled', 'Refleksi harian')
        return {'ok': True}
    except Exception as e:
        conn.rollback()
        return {'ok': False, 'error': str(e)}
    finally:
        c.close(); conn.close()


def generate_weekly_review(user_id: int) -> dict:
    """Generate weekly review for current week."""
    from datetime import date, timedelta
    import json as _json
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    week_end   = (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat()

    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        # Tasks this week
        c.execute("""SELECT COUNT(*) as total,
                            SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done
                     FROM daily_tasks
                     WHERE user_id=%s AND task_date BETWEEN %s AND %s""",
                  (user_id, week_start, week_end))
        task_row = c.fetchone()
        tasks_done  = int(task_row['done']  or 0) if task_row else 0
        tasks_total = int(task_row['total'] or 0) if task_row else 0

        # Reminder completion this week
        c.execute("""SELECT COUNT(*) as total,
                            SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) as done
                     FROM reminder_logs
                     WHERE user_id=%s AND log_date BETWEEN %s AND %s""",
                  (user_id, week_start, week_end))
        rem_row = c.fetchone()
        rem_done  = int(rem_row['done']  or 0) if rem_row else 0
        rem_total = int(rem_row['total'] or 0) if rem_row else 0
        rem_pct   = round(rem_done / rem_total * 100, 1) if rem_total else 0

        # Average mood
        c.execute("""SELECT AVG(mood_score) as avg_mood FROM user_moods
                     WHERE user_id=%s AND mood_date BETWEEN %s AND %s""",
                  (user_id, week_start, week_end))
        mood_row  = c.fetchone()
        avg_mood  = round(float(mood_row['avg_mood'] or 0), 1) if mood_row else 0

        # Top streaks
        c.execute("""SELECT r.title, r.emoji, rs.current_streak, rs.tier
                     FROM reminders r JOIN reminder_streaks rs ON rs.reminder_id=r.id
                     WHERE r.user_id=%s AND r.is_active=1
                     ORDER BY rs.current_streak DESC LIMIT 3""",
                  (user_id,))
        top_streaks = c.fetchall()

        # XP earned this week
        c.execute("""SELECT COALESCE(SUM(xp_amount),0) as total FROM xp_logs
                     WHERE user_id=%s AND earned_at >= %s""",
                  (user_id, week_start))
        xp_row = c.fetchone()
        xp_earned = int(xp_row['total'] or 0) if xp_row else 0

        # Spiritual score (how many activities done)
        c.execute("""SELECT COUNT(*) as cnt FROM esq_spiritual_log
                     WHERE user_id=%s AND log_date BETWEEN %s AND %s AND is_done=1""",
                  (user_id, week_start, week_end))
        spi_row = c.fetchone()
        spiritual_score = int(spi_row['cnt'] or 0) if spi_row else 0

        # Savings this week
        c.execute("""SELECT COALESCE(SUM(amount),0) as total FROM saving_logs
                     WHERE user_id=%s AND log_date BETWEEN %s AND %s AND type='deposit'""",
                  (user_id, week_start, week_end))
        sav_row = c.fetchone()
        saving_amount = float(sav_row['total'] or 0) if sav_row else 0

        # Generate highlight text
        highlights = []
        if tasks_done > 0:
            highlights.append(f"{tasks_done} task selesai")
        if rem_pct >= 80:
            highlights.append(f"reminder {rem_pct}% konsisten")
        if spiritual_score >= 7:
            highlights.append(f"{spiritual_score} ibadah tercatat")
        if xp_earned > 0:
            highlights.append(f"+{xp_earned} XP")
        highlight = " · ".join(highlights) if highlights else "Minggu yang dilewati"

        # Upsert review
        c.execute("""
            INSERT INTO weekly_review_generated
                (user_id, week_start, week_end, tasks_done, tasks_total,
                 reminders_pct, avg_mood, top_streaks, xp_earned,
                 spiritual_score, saving_amount, highlight)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                tasks_done=VALUES(tasks_done),
                tasks_total=VALUES(tasks_total),
                reminders_pct=VALUES(reminders_pct),
                avg_mood=VALUES(avg_mood),
                top_streaks=VALUES(top_streaks),
                xp_earned=VALUES(xp_earned),
                spiritual_score=VALUES(spiritual_score),
                saving_amount=VALUES(saving_amount),
                highlight=VALUES(highlight)
        """, (user_id, week_start, week_end, tasks_done, tasks_total,
               rem_pct, avg_mood, _json.dumps(top_streaks),
               xp_earned, spiritual_score, saving_amount, highlight))
        conn.commit()

        return {
            'week_start': week_start,
            'week_end': week_end,
            'tasks_done': tasks_done,
            'tasks_total': tasks_total,
            'reminders_pct': rem_pct,
            'avg_mood': avg_mood,
            'top_streaks': top_streaks,
            'xp_earned': xp_earned,
            'spiritual_score': spiritual_score,
            'saving_amount': saving_amount,
            'highlight': highlight,
        }
    except Exception as e:
        conn.rollback()
        return {'error': str(e)}
    finally:
        c.close(); conn.close()


def get_user_profile(user_id: int) -> dict:
    """Get user profile setup."""
    conn = get_connection()
    if not conn: return {}
    c = conn.cursor(dictionary=True)
    try:
        c.execute("SELECT * FROM user_profile_setup WHERE user_id=%s", (user_id,))
        profile = c.fetchone()
        if not profile:
            return {'setup_complete': False, 'setup_step': 0}
        for k in ['work_hours_start','work_hours_end','sleep_time','wake_time']:
            if profile.get(k): profile[k] = str(profile[k])
        return profile
    finally:
        c.close(); conn.close()


def save_user_profile(user_id: int, profile_type: str,
                      focus_areas: list, work_start: str = '08:00',
                      work_end: str = '17:00', sleep_time: str = '22:00',
                      wake_time: str = '05:00', religion: str = None) -> bool:
    import json as _json
    emoji, _, _ = PROFILE_TYPES.get(profile_type, ('👤', '', []))
    conn = get_connection()
    if not conn: return False
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO user_profile_setup
                (user_id, profile_type, profile_emoji, focus_areas,
                 work_hours_start, work_hours_end, sleep_time, wake_time,
                 religion, setup_complete, setup_step)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,5)
            ON DUPLICATE KEY UPDATE
                profile_type=VALUES(profile_type),
                profile_emoji=VALUES(profile_emoji),
                focus_areas=VALUES(focus_areas),
                work_hours_start=VALUES(work_hours_start),
                work_hours_end=VALUES(work_hours_end),
                sleep_time=VALUES(sleep_time),
                wake_time=VALUES(wake_time),
                religion=VALUES(religion),
                setup_complete=TRUE, setup_step=5
        """, (user_id, profile_type, emoji,
               _json.dumps(focus_areas),
               work_start, work_end, sleep_time, wake_time, religion))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        c.close(); conn.close()
