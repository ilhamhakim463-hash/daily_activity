from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime, date, timedelta
from functools import wraps
import os, uuid, json, decimal
import db

app = Flask(__name__)

# ─── Custom JSON encoder — fix MySQL date/time/timedelta/Decimal not serializable ──
class MySQLJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            # Convert timedelta (TIME columns) to HH:MM:SS string
            total = int(obj.total_seconds())
            h, rem = divmod(abs(total), 3600)
            m, s   = divmod(rem, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        return super().default(obj)

app.json_encoder = MySQLJSONEncoder

def serialize_row(row):
    """Convert a MySQL dict row to JSON-safe dict."""
    if not row:
        return row
    result = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            result[k] = v.isoformat()
        elif isinstance(v, timedelta):
            total = int(v.total_seconds())
            h, rem = divmod(abs(total), 3600)
            m, s   = divmod(rem, 60)
            result[k] = f"{h:02d}:{m:02d}:{s:02d}"
        elif isinstance(v, decimal.Decimal):
            result[k] = float(v)
        elif isinstance(v, bytes):
            result[k] = v.decode('utf-8', errors='replace')
        else:
            result[k] = v
    return result

def serialize_rows(rows):
    return [serialize_row(r) for r in rows]

# ─── APScheduler for push notifications ───────────────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit, json as _json
_scheduler = BackgroundScheduler(daemon=True)
app.secret_key = 'daily-activity-secret-key-2025-CHANGE-IN-PRODUCTION'
app.jinja_env.globals.update(now=datetime.now)

# Session timeout: 7 hari
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY']    = True
app.config['SESSION_COOKIE_SAMESITE']   = 'Lax'

def admin_required(f):
    """Decorator: route hanya bisa diakses admin."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Akses ditolak. Halaman ini khusus admin.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

@app.before_request
def sync_admin_status():
    """Sync is_admin dari DB setiap request — cegah session lama bypass."""
    if session.get('user_id') and 'is_admin' not in session:
        conn = db.get_connection()
        if conn:
            try:
                c = conn.cursor(dictionary=True)
                c.execute("SELECT is_admin FROM users WHERE id=%s", (session['user_id'],))
                row = c.fetchone()
                session['is_admin'] = bool(row['is_admin']) if row else False
            except Exception:
                session['is_admin'] = False
            finally:
                c.close(); conn.close()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'avatars')
ALLOWED_EXT   = {'png','jpg','jpeg','gif','webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        ip       = request.remote_addr

        user, status = db.get_user_by_login(username, password, ip)

        if status == 'ok' and user:
            session['user_id']    = user['id']
            session['username']   = user['username']
            session['full_name']  = user['full_name'] or user['username']
            session['avatar_url'] = user['avatar_url'] or ''
            session['theme']      = user['theme_pref'] or 'dark'
            session['onboarded']  = bool(user['onboarded'])
            session['is_admin']   = bool(user.get('is_admin', False))
            session.permanent     = True
            # Admin langsung ke admin panel, user ke dashboard
            if session['is_admin']:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('dashboard'))
        elif status and status.startswith('locked:'):
            minutes = status.split(':')[1]
            if minutes == '0':
                flash('Terlalu banyak percobaan! Akun terkunci 5 menit.', 'error')
            else:
                flash(f'Akun terkunci. Coba lagi dalam {minutes} menit.', 'error')
        elif status == 'db_error':
            flash('Terjadi kesalahan server. Coba lagi.', 'error')
        else:
            flash('Username atau password salah.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username  = request.form.get('username','').strip()
        email     = request.form.get('email','').strip()
        password  = request.form.get('password','')
        full_name = request.form.get('full_name','').strip()
        user_id, error = db.register_user(username, email, password, full_name)
        if error:
            flash(error, 'error')
        else:
            session['user_id']   = user_id
            session['username']  = username
            session['full_name'] = full_name or username
            session['avatar_url']= ''
            session['theme']     = 'dark'
            session['onboarded'] = False
            session['is_admin']  = False   # user baru tidak pernah admin
            session.permanent    = True
            return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── ONBOARDING ────────────────────────────────────────────────────────────────
@app.route('/api/onboarded', methods=['POST'])
@login_required
def api_onboarded():
    db.mark_onboarded(session['user_id'])
    session['onboarded'] = True
    return jsonify({'ok': True})

# ─── THEME ─────────────────────────────────────────────────────────────────────
@app.route('/api/theme', methods=['POST'])
@login_required
def api_theme():
    theme = request.get_json().get('theme','dark')
    conn = db.get_connection()
    if conn:
        c = conn.cursor()
        c.execute("UPDATE users SET theme_pref=%s WHERE id=%s", (theme, session['user_id']))
        conn.commit(); c.close(); conn.close()
    session['theme'] = theme
    return jsonify({'ok': True})

# ─── AVATAR UPLOAD ─────────────────────────────────────────────────────────────
@app.route('/api/avatar', methods=['POST'])
@login_required
def api_upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['avatar']
    if f.filename == '' or not allowed_file(f.filename):
        return jsonify({'error': 'File tidak valid'}), 400
    ext      = f.filename.rsplit('.',1)[1].lower()
    filename = f"{session['user_id']}_{uuid.uuid4().hex[:8]}.{ext}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    url = f"/static/uploads/avatars/{filename}"
    db.update_avatar(session['user_id'], url)
    session['avatar_url'] = url
    return jsonify({'url': url})

# ─── MOOD ──────────────────────────────────────────────────────────────────────
@app.route('/api/mood', methods=['POST'])
@login_required
def api_save_mood():
    data = request.get_json()
    db.save_mood(session['user_id'], data.get('mood','😊'), data.get('label','Happy'), data.get('note',''))
    return jsonify({'ok': True})

@app.route('/api/mood/today')
@login_required
def api_today_mood():
    mood = db.get_today_mood(session['user_id'])
    return jsonify(mood or {})

# ─── SEARCH (Command Palette) ──────────────────────────────────────────────────
@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q','').strip()
    if len(q) < 2: return jsonify([])
    results = db.search_all(session['user_id'], q)
    return jsonify(results)

# ─── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    today = date.today()
    tasks  = db.get_daily_tasks(uid, today)
    goals  = db.get_goals_with_progress(uid)
    streak = db.get_streak(uid)
    weekly = db.get_weekly_summary(uid)
    grid   = db.get_contribution_grid(uid)
    mood   = db.get_today_mood(uid)
    done_today  = sum(1 for t in tasks if t['status']=='done')
    total_today = len(tasks)
    pct_today   = round(done_today/total_today*100) if total_today else 0
    return render_template('dashboard.html',
        tasks=tasks, goals=goals, streak=streak, weekly=weekly,
        grid=grid, mood=mood,
        done_today=done_today, total_today=total_today, pct_today=pct_today,
        today_str=today.strftime('%A, %d %B %Y'))

# ─── TASKS ─────────────────────────────────────────────────────────────────────
@app.route('/api/tasks', methods=['GET'])
@login_required
def api_get_tasks():
    ds = request.args.get('date')
    task_date = datetime.strptime(ds,'%Y-%m-%d').date() if ds else date.today()
    tasks = serialize_rows(db.get_daily_tasks(session['user_id'], task_date))
    return jsonify({'tasks': tasks, 'date': task_date.isoformat()})

@app.route('/api/tasks', methods=['POST'])
@login_required
def api_create_task():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error': 'Title wajib'}), 400
    return jsonify({'id': db.create_task(session['user_id'], data)}), 201

@app.route('/api/tasks/<int:task_id>/status', methods=['PATCH'])
@login_required
def api_update_status(task_id):
    status = request.get_json().get('status')
    if status not in ('todo','in_progress','done','cancelled'):
        return jsonify({'error': 'Status invalid'}), 400
    ok = db.update_task_status(task_id, session['user_id'], status)
    return jsonify({'success': ok})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def api_delete_task(task_id):
    return jsonify({'success': db.delete_task(task_id, session['user_id'])})

# ─── GOALS ─────────────────────────────────────────────────────────────────────
@app.route('/roadmap')
@login_required
def roadmap():
    uid  = session['user_id']
    year = request.args.get('year', datetime.now().year, type=int)
    goals = db.get_goals_with_progress(uid, year)
    for g in goals: g['milestones'] = db.get_milestones(uid, goal_id=g['id'])
    return render_template('roadmap.html', goals=goals, year=year)

@app.route('/api/goals', methods=['POST'])
@login_required
def api_create_goal():
    data = request.get_json()
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB Error'}),500
    c = conn.cursor()
    c.execute("""INSERT INTO goals (user_id,title,description,year,category,color,icon)
                 VALUES (%s,%s,%s,%s,%s,%s,%s)""",
              (session['user_id'], data.get('title'), data.get('description',''),
               data.get('year', datetime.now().year), data.get('category','general'),
               data.get('color','#6366f1'), data.get('icon','target')))
    gid = c.lastrowid; conn.commit(); c.close(); conn.close()
    return jsonify({'id': gid}), 201

# ─── ANALYTICS ─────────────────────────────────────────────────────────────────
@app.route('/analytics')
@login_required
def analytics():
    uid = session['user_id']
    return render_template('analytics.html',
        streak=db.get_streak(uid), weekly=db.get_weekly_summary(uid),
        grid=db.get_contribution_grid(uid, weeks=20),
        goals=db.get_goals_with_progress(uid))

@app.route('/api/analytics/weekly')
@login_required
def api_weekly():
    ws = db.get_weekly_summary(session['user_id'], request.args.get('offset',0,type=int))
    return jsonify(serialize_row(ws) if isinstance(ws, dict) else serialize_rows(ws) if isinstance(ws, list) else ws)

# ─── TASKS PAGE ────────────────────────────────────────────────────────────────
@app.route('/tasks')
@login_required
def tasks_page():
    uid = session['user_id']
    today = date.today()
    return render_template('tasks.html',
        tasks=db.get_daily_tasks(uid, today),
        goals=db.get_goals_with_progress(uid),
        milestones=db.get_milestones(uid),
        today_str=today.isoformat())



# ─── TASK EDIT ─────────────────────────────────────────────────────────────────
@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@login_required
def api_get_task(task_id):
    conn = db.get_connection()
    if not conn: return jsonify({}), 500
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM daily_tasks WHERE id=%s AND user_id=%s", (task_id, session['user_id']))
    t = c.fetchone()
    c.close(); conn.close()
    return jsonify(serialize_row(t) if t else {})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def api_edit_task(task_id):
    data = request.get_json()
    if not data or not data.get('title','').strip():
        return jsonify({'error':'Title wajib'}), 400
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    c.execute("""UPDATE daily_tasks SET title=%s,description=%s,priority=%s,
                 duration_min=%s,category=%s,tags=%s,updated_at=NOW()
                 WHERE id=%s AND user_id=%s""",
              (data['title'].strip(), data.get('description',''),
               data.get('priority','medium'), int(data.get('duration_min',0)),
               data.get('category','general'), data.get('tags',''),
               task_id, session['user_id']))
    conn.commit(); ok = c.rowcount > 0
    c.close(); conn.close()
    return jsonify({'success': ok})

# ─── MILESTONE CREATE ───────────────────────────────────────────────────────────
@app.route('/api/milestones', methods=['GET'])
@login_required
def api_get_milestones():
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT m.id, m.title, m.goal_id, m.month, m.year,
               g.title as goal_title, g.color
        FROM milestones m
        JOIN goals g ON m.goal_id = g.id
        WHERE m.user_id=%s
        ORDER BY m.year, m.month, m.id
    """, (session['user_id'],))
    rows = c.fetchall()
    c.close(); conn.close()
    return jsonify(rows)

@app.route('/api/milestones', methods=['POST'])
@login_required
def api_create_milestone():
    data = request.get_json()
    if not data or not data.get('title','').strip() or not data.get('goal_id'):
        return jsonify({'error':'title & goal_id wajib'}), 400
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    c.execute("""INSERT INTO milestones (goal_id,user_id,title,description,month,year)
                 VALUES (%s,%s,%s,%s,%s,%s)""",
              (data['goal_id'], session['user_id'], data['title'].strip(),
               data.get('description',''),
               data.get('month', datetime.now().month),
               data.get('year',  datetime.now().year)))
    mid = c.lastrowid; conn.commit(); c.close(); conn.close()
    return jsonify({'id': mid}), 201

# ─── PASSWORD CHANGE ────────────────────────────────────────────────────────────
@app.route('/api/password', methods=['POST'])
@login_required
def api_change_password():
    data   = request.get_json()
    old_pw = data.get('old_password','')
    new_pw = data.get('new_password','')
    if len(new_pw) < 6:
        return jsonify({'error':'Password baru min. 6 karakter'}), 400
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB error'}), 500
    c = conn.cursor(dictionary=True)
    try:
        c.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],))
        row = c.fetchone()
        if not row or not db.verify_password(old_pw, row['password']):
            return jsonify({'error':'Password lama salah'}), 400
        new_hash = db.hash_password(new_pw)
        c.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

# ─── ADMIN PANEL ────────────────────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin_panel():
    users = db.get_all_users()
    logs, total_logs = db.get_login_logs(limit=10)
    for u in users:
        for k in ['last_login','created_at','locked_until']:
            if u.get(k): u[k] = u[k].isoformat() if hasattr(u[k],'isoformat') else str(u[k])
    return render_template('admin.html', users=users, logs=logs,
                           total_logs=total_logs,
                           current_admin_id=session['user_id'])

@app.route('/admin/logs')
@admin_required
def admin_logs_page():
    PER_PAGE = 20
    page      = max(1, int(request.args.get('page', 1)))
    q         = request.args.get('q', '').strip()
    log_type  = request.args.get('type', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to', '').strip()
    offset    = (page - 1) * PER_PAGE

    logs, total_filtered = db.get_login_logs(
        limit=PER_PAGE, offset=offset,
        q=q, log_type=log_type,
        date_from=date_from, date_to=date_to
    )
    # total all logs for header stat
    _, total_all = db.get_login_logs(limit=1)

    import math
    total_pages = max(1, math.ceil(total_filtered / PER_PAGE))

    return render_template('admin_logs.html',
        logs=logs,
        page=page,
        per_page=PER_PAGE,
        total_logs=total_all,
        total_filtered=total_filtered,
        total_pages=total_pages,
        q=q, type=log_type,
        date_from=date_from,
        date_to=date_to,
    )

@app.route('/admin/logs/export')
@admin_required
def admin_logs_export():
    """Export activity log sebagai CSV."""
    import csv, io
    q         = request.args.get('q', '').strip()
    log_type  = request.args.get('type', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to', '').strip()

    logs, _ = db.get_login_logs(
        limit=10000, offset=0,
        q=q, log_type=log_type,
        date_from=date_from, date_to=date_to
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['username', 'action', 'ip_address', 'detail', 'timestamp'])
    for l in logs:
        writer.writerow([
            l.get('username', ''),
            l.get('action', ''),
            l.get('ip_address', ''),
            l.get('detail', ''),
            l.get('created_at', ''),
        ])

    from flask import Response
    from datetime import date
    filename = f"activityos_logs_{date.today().isoformat()}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/api/admin/reset-password', methods=['POST'])
@admin_required
def api_admin_reset_password():
    data    = request.get_json()
    user_id = data.get('user_id')
    new_pw  = data.get('new_password','')
    if not user_id or len(new_pw) < 6:
        return jsonify({'error':'user_id dan password min 6 karakter wajib diisi'}), 400
    ok = db.admin_reset_password(user_id, new_pw, session['user_id'], request.remote_addr)
    return jsonify({'ok': ok}) if ok else jsonify({'error':'Gagal reset password'}), 500

@app.route('/api/admin/toggle-lock', methods=['POST'])
@admin_required
def api_admin_toggle_lock():
    data    = request.get_json()
    user_id = data.get('user_id')
    lock    = data.get('lock', True)
    if not user_id: return jsonify({'error':'user_id required'}), 400
    ok = db.admin_toggle_lock(user_id, lock, session['user_id'])
    return jsonify({'ok': ok})

@app.route('/api/admin/toggle-admin', methods=['POST'])
@admin_required
def api_admin_toggle_admin():
    data      = request.get_json()
    user_id   = data.get('user_id')
    is_admin  = data.get('is_admin', False)
    if not user_id: return jsonify({'error':'user_id required'}), 400
    # Cegah admin cabut privilege dirinya sendiri
    if user_id == session['user_id'] and not is_admin:
        return jsonify({'error':'Tidak bisa cabut privilege admin diri sendiri'}), 400
    ok = db.admin_toggle_admin(user_id, is_admin, session['user_id'])
    return jsonify({'ok': ok})

# ─── QUICK NOTES ────────────────────────────────────────────────────────────────
@app.route('/api/notes', methods=['GET'])
@login_required
def api_get_notes():
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM quick_notes WHERE user_id=%s ORDER BY updated_at DESC LIMIT 20", (session['user_id'],))
    notes = c.fetchall()
    for n in notes:
        if n.get('created_at'): n['created_at'] = n['created_at'].isoformat()
        if n.get('updated_at'): n['updated_at'] = n['updated_at'].isoformat()
    c.close(); conn.close()
    return jsonify(notes)

@app.route('/api/notes/archive', methods=['GET'])
@login_required
def api_notes_archive():
    """Return dates that have notes (for archive)"""
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""SELECT note_date, COUNT(*) as count FROM quick_notes
                     WHERE user_id=%s GROUP BY note_date ORDER BY note_date DESC LIMIT 60""",
                  (session['user_id'],))
        dates = c.fetchall()
        for d in dates:
            if d.get('note_date'):
                d['note_date'] = d['note_date'].isoformat() if hasattr(d['note_date'], 'isoformat') else str(d['note_date'])
    except Exception:
        dates = []
    c.close(); conn.close()
    return jsonify(dates)


@app.route('/api/notes', methods=['POST'])
@login_required
def api_create_note():
    from datetime import date as dt_date
    data = request.get_json()
    note_date = data.get('note_date', dt_date.today().isoformat())
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("INSERT INTO quick_notes (user_id,content,color,note_date) VALUES (%s,%s,%s,%s)",
                  (session['user_id'], data.get('content',''), data.get('color','#6366f1'), note_date))
    except Exception:
        c.execute("INSERT INTO quick_notes (user_id,content,color) VALUES (%s,%s,%s)",
                  (session['user_id'], data.get('content',''), data.get('color','#6366f1')))
    nid = c.lastrowid; conn.commit(); c.close(); conn.close()
    return jsonify({'id': nid, 'note_date': note_date}), 201

@app.route('/api/notes/<int:note_id>', methods=['PUT'])
@login_required
def api_update_note(note_id):
    data = request.get_json()
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    c.execute("UPDATE quick_notes SET content=%s,color=%s,updated_at=NOW() WHERE id=%s AND user_id=%s",
              (data.get('content',''), data.get('color','#6366f1'), note_id, session['user_id']))
    conn.commit(); c.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@login_required
def api_delete_note(note_id):
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    c.execute("DELETE FROM quick_notes WHERE id=%s AND user_id=%s", (note_id, session['user_id']))
    conn.commit(); ok = c.rowcount > 0; c.close(); conn.close()
    return jsonify({'ok': ok})

# ─── WEB PUSH NOTIFICATIONS ─────────────────────────────────────────────────────
@app.route('/api/push/subscribe', methods=['POST'])
@login_required
def api_push_subscribe():
    data = request.get_json()
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    import json
    c.execute("""INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth_key)
                 VALUES (%s,%s,%s,%s)
                 ON DUPLICATE KEY UPDATE p256dh=%s, auth_key=%s""",
              (session['user_id'],
               data.get('endpoint',''),
               data.get('keys',{}).get('p256dh',''),
               data.get('keys',{}).get('auth',''),
               data.get('keys',{}).get('p256dh',''),
               data.get('keys',{}).get('auth','')))
    conn.commit(); c.close(); conn.close()
    return jsonify({'ok': True})

# ─── EXPORT PDF ─────────────────────────────────────────────────────────────────
@app.route('/export/daily')
@login_required
def export_daily():
    from datetime import date as dt
    ds = request.args.get('date', dt.today().isoformat())
    try: task_date = datetime.strptime(ds, '%Y-%m-%d').date()
    except: task_date = dt.today()
    uid   = session['user_id']
    tasks = db.get_daily_tasks(uid, task_date)
    streak= db.get_streak(uid)
    mood  = db.get_today_mood(uid)
    done  = sum(1 for t in tasks if t['status']=='done')
    total = len(tasks)
    return render_template('export_daily.html',
        tasks=tasks, streak=streak, mood=mood,
        done=done, total=total,
        date_str=task_date.strftime('%A, %d %B %Y'),
        username=session.get('full_name','User'),
        pct=round(done/total*100) if total else 0)

# ─── 404 & ERROR HANDLERS ───────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', code=500, msg="Internal Server Error"), 500

# ─── ISQ ROUTES ────────────────────────────────────────────────────────────────
@app.route('/isq')
@login_required
def isq_page():
    uid     = session['user_id']
    today   = db.get_isq_today(uid)
    history = db.get_isq_history(uid, days=30)
    context = db.get_isq_context(uid)
    capsules= db.get_due_capsules(uid)
    streak  = db.get_streak(uid)
    return render_template('isq.html',
        today=today, history=history, context=context,
        capsules=capsules, streak=streak,
        today_str=date.today().strftime('%A, %d %B %Y'),
        today_iso=date.today().isoformat())

@app.route('/api/isq/morning', methods=['POST'])
@login_required
def api_isq_morning():
    data = request.get_json()
    data['date'] = date.today().isoformat()
    db.save_isq_morning(session['user_id'], data)
    return jsonify({'ok': True})

@app.route('/api/isq/evening', methods=['POST'])
@login_required
def api_isq_evening():
    data  = request.get_json()
    data['date'] = date.today().isoformat()
    score = db.save_isq_evening(session['user_id'], data)
    return jsonify({'ok': True, 'score': score})

@app.route('/api/isq/today')
@login_required
def api_isq_today():
    isq_data = db.get_isq_today(session['user_id'])
    if isinstance(isq_data, dict):
        isq_data = {k: serialize_row(v) if isinstance(v, dict) else v for k, v in isq_data.items()}
    return jsonify(isq_data)

@app.route('/api/isq/context')
@login_required
def api_isq_context():
    ctx = db.get_isq_context(session['user_id'])
    return jsonify(serialize_row(ctx) if isinstance(ctx, dict) else ctx)

@app.route('/api/isq/voice-script')
@login_required
def api_voice_script():
    """Generate contextual AI voice script based on user state"""
    slot    = request.args.get('slot', 'morning')  # morning / evening / reminder
    ctx     = db.get_isq_context(session['user_id'])
    name    = session.get('full_name','').split()[0] or 'kamu'
    streak  = ctx.get('streak', 0)
    done    = ctx.get('tasks_done', 0)
    total   = ctx.get('tasks_total', 0)
    moods   = ctx.get('recent_moods', [])
    morning = ctx.get('morning')
    energy  = morning.get('energy_level', 3) if morning else 3
    word    = morning.get('word_of_day','') if morning else ''
    pct     = round(done/total*100) if total else 0

    scripts = {
        'morning': _morning_script(name, streak, energy, word),
        'evening': _evening_script(name, done, total, pct, word, moods),
        'reminder': _reminder_script(name, done, total, streak, moods),
        'milestone': _milestone_script(name, streak),
    }
    text = scripts.get(slot, scripts['morning'])
    return jsonify({'text': text, 'slot': slot})

def _morning_script(name, streak, energy, word):
    import random
    low_energy = [
        f"Hei {name}, energimu pagi ini emang lagi nggak penuh. Itu bukan masalah — itu manusiawi. Mulai dari yang paling kecil dulu.",
        f"Pagi {name}. Badan minta pelan-pelan hari ini? Dengerin aja. Tapi tetap mulai — satu langkah kecil udah cukup.",
        f"Lo nggak harus jadi produktif penuh hari ini, {name}. Yang penting: jangan berhenti sepenuhnya.",
    ]
    high_energy = [
        f"Woah {name}! Energimu hari ini beda — pakai ini sebaik mungkin. Satu keputusan jam segini bisa nentuin kualitas malammu.",
        f"Pagi {name}! Vibes hari ini bagus. Yuk kunci 3 hal yang HARUS selesai — sisanya bonus.",
        f"Hei {name}, ini pagi yang bagus buat nyerang tugas yang udah lama lo tunda. Lo punya energinya sekarang.",
    ]
    streak_bonus = f" Streak lo {streak} hari — sayang banget kalau putus hari ini." if streak >= 5 else ""
    word_bonus   = f" Kata lo hari ini: '{word}'. Bawa itu ke semua yang lo lakuin." if word else ""
    base = random.choice(low_energy if energy <= 2 else high_energy)
    return base + streak_bonus + word_bonus

def _evening_script(name, done, total, pct, word, moods):
    import random
    if pct == 100:
        msgs = [
            f"CLEAN SWEEP, {name}! Semua task hari ini selesai. Ini bukan keberuntungan — ini kebiasaan yang lo bangun setiap hari.",
            f"{name}, lo baru aja nyapu bersih semua task. Serius, nggak semua orang bisa kayak gini. Rayakan ini.",
            f"Hari ini lo menang, {name}. 100 persen. Tidur dengan tenang malam ini — lo deserve it.",
        ]
    elif pct >= 60:
        msgs = [
            f"{done} dari {total} selesai, {name}. Itu bukan kegagalan — itu progress. Yang belum? Besok giliran mereka.",
            f"Lebih dari setengah udah beres, {name}. Raksasa dibangun dari butiran pasir. Lo udah numpahin banyak hari ini.",
            f"{pct} persen hari ini, {name}. Lo mau bilang itu buruk? Kebanyakan orang bahkan nggak mulai.",
        ]
    else:
        msgs = [
            f"Hari ini berat ya, {name}? Cuma {done} dari {total}. Nggak apa-apa. Istirahat dulu — besok kita coba lagi dengan cara yang lebih simpel.",
            f"{name}, hari ini mungkin nggak sesuai rencana. Tapi lo masih di sini, masih refleksi. Itu udah lebih dari cukup.",
            f"Gak apa-apa hari ini berat, {name}. Besok kita kecilkan skalanya. Yang penting: jangan menyerah.",
        ]
    word_close = f" Kata lo tadi pagi: '{word}' — udah sesuai belum sama yang lo lakuin hari ini?" if word else ""
    return random.choice(msgs) + word_close

def _reminder_script(name, done, total, streak, moods):
    import random
    if total == 0:
        return f"Hei {name}. Belum ada task hari ini. Mulai dari yang paling kecil — literally apa aja. Momentum itu awalnya dari satu langkah."
    remaining = total - done
    low_mood_days = sum(1 for m in moods if m and m.lower() in ['tired','frustrated','struggling'])
    if streak >= 7 and remaining > 0:
        return f"{name}, streak lo {streak} hari! Sayang banget kalau harus putus hari ini. Masih ada {remaining} task — selesaikan satu aja, streak aman."
    if low_mood_days >= 2:
        return f"{name}, beberapa hari ini kelihatan berat. Lo nggak harus sempurna. Tapi coba satu task kecil — bukan buat produktivitas, tapi buat bilang ke diri sendiri bahwa lo masih bisa."
    return random.choice([
        f"Siang {name}. Tugas kecilmu sudah beres? Ingat — raksasa dibangun dari butiran pasir. {remaining} task lagi.",
        f"{name}, hari hampir habis. Masih {remaining} yang belum selesai. Satu lagi — just one more.",
        f"Hei {name}! Satu keputusan jam segini bakal nentuin kualitas malammu. {remaining} task nunggu.",
    ])

def _milestone_script(name, streak):
    milestones = {7:'seminggu', 14:'dua minggu', 30:'sebulan', 60:'dua bulan', 100:'seratus hari'}
    label = milestones.get(streak, f'{streak} hari')
    return f"WOW {name}! Streak kamu baru nyentuh {label} berturut-turut! Ini bukan kebetulan — ini bukti komitmen kamu. Rayakan ini!"

# ─── SHARE CARD DATA ────────────────────────────────────────────────────────────
@app.route('/api/share-card/data')
@login_required
def api_share_card_data():
    uid   = session['user_id']
    today = date.today()
    ctx   = db.get_isq_context(uid)
    streak= db.get_streak(uid)
    isq   = db.get_isq_today(uid)
    tasks = db.get_daily_tasks(uid, today)
    done  = sum(1 for t in tasks if t['status']=='done')
    total = len(tasks)
    morning = isq.get('morning') or {}
    evening = isq.get('evening') or {}
    return jsonify({
        'name':       session.get('full_name','').split()[0],
        'date':       today.strftime('%A, %d %B %Y'),
        'streak':     streak.get('current_streak', 0),
        'tasks_done': done,
        'tasks_total': total,
        'word_of_day': morning.get('word_of_day',''),
        'energy':     morning.get('energy_level', 0),
        'isq_mode':   evening.get('isq_mode', ''),
        'isq_score':  evening.get('isq_score', 0),
        'highlight':  evening.get('highlight',''),
        'micro_journal': evening.get('micro_journal',''),
    })

# ─── TIME CAPSULE ───────────────────────────────────────────────────────────────
@app.route('/api/capsule', methods=['POST'])
@login_required
def api_create_capsule():
    data = request.get_json()
    msg  = data.get('message','').strip()
    od   = data.get('open_date')
    if not msg or not od:
        return jsonify({'error':'message & open_date wajib'}), 400
    db.save_time_capsule(session['user_id'], msg, od)
    return jsonify({'ok': True})

@app.route('/api/capsule/<int:cid>/open', methods=['POST'])
@login_required
def api_open_capsule(cid):
    db.open_capsule(cid, session['user_id'])
    return jsonify({'ok': True})


# ─── COMPASS QUIZ ──────────────────────────────────────────────────────────────
@app.route('/api/compass', methods=['POST'])
@login_required
def api_compass():
    data      = request.get_json()
    answers   = data.get('answers', [])
    # Score answers to determine archetype
    scores    = {'builder': 0, 'zen': 0, 'achiever': 0, 'explorer': 0}
    for a in answers:
        tag = a.get('tag','')
        if tag in scores: scores[tag] += 1
    archetype = max(scores, key=scores.get)
    db.save_archetype(session['user_id'], archetype, answers)
    session['archetype'] = archetype
    archetypes = {
        'builder':  {'label':'The Builder',       'emoji':'🔨', 'desc':'Kamu fokus membangun skill dan karya nyata.', 'color':'#6366f1'},
        'zen':      {'label':'The Zen Master',     'emoji':'🧘', 'desc':'Kamu butuh ketenangan dan keseimbangan hidup.', 'color':'#10b981'},
        'achiever': {'label':'The High Achiever',  'emoji':'🚀', 'desc':'Kamu ambisius dan ingin capai target besar.', 'color':'#f59e0b'},
        'explorer': {'label':'The Explorer',       'emoji':'🧭', 'desc':'Kamu suka eksplorasi dan hal-hal baru.', 'color':'#06b6d4'},
    }
    return jsonify({'archetype': archetype, 'info': archetypes.get(archetype, archetypes['explorer'])})

@app.route('/api/archetype')
@login_required
def api_get_archetype():
    row = db.get_archetype(session['user_id'])
    return jsonify(row or {})

# ─── ADAPTIVE ROADMAP ──────────────────────────────────────────────────────────
@app.route('/api/adaptive/check')
@login_required
def api_adaptive_check():
    fail_streak = db.get_fail_streak(session['user_id'])
    msg = None
    if fail_streak >= 3:
        msgs = [
            "Sepertinya kamu lagi sibuk banget. Mau kita kecilkan skala tugas hari ini jadi 5 menit saja?",
            "3 hari ini berat ya? Nggak apa-apa. Besok kita mulai dari tugas 2 menit dulu.",
            "Istirahat juga bagian dari tumbuh. Mau reset ke tugas yang lebih kecil hari ini?",
        ]
        import random
        msg = random.choice(msgs)
    return jsonify({'fail_streak': fail_streak, 'adaptive_msg': msg})

# ─── GHOST DATA ────────────────────────────────────────────────────────────────
@app.route('/api/ghost')
@login_required
def api_ghost():
    gd = db.get_ghost_data(session['user_id'])
    return jsonify(serialize_row(gd) if isinstance(gd, dict) else gd)

# ─── DOMINO PROGRESS ───────────────────────────────────────────────────────────
@app.route('/api/domino/<int:goal_id>')
@login_required
def api_domino(goal_id):
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    c.execute("""
        SELECT m.id, m.title, m.month, m.year, m.is_completed,
               COUNT(t.id) as total_tasks,
               SUM(t.status='done') as done_tasks,
               IFNULL(ROUND(SUM(t.status='done')/NULLIF(COUNT(t.id),0)*100),0) as pct
        FROM milestones m
        LEFT JOIN daily_tasks t ON t.milestone_id=m.id
        WHERE m.goal_id=%s AND m.user_id=%s
        GROUP BY m.id ORDER BY m.year, m.month
    """, (goal_id, session['user_id']))
    rows = c.fetchall()
    c.close(); conn.close()
    return jsonify(rows)

# ─── FIRST DOMINO TASK ─────────────────────────────────────────────────────────
@app.route('/api/first-domino', methods=['POST'])
@login_required
def api_first_domino():
    """Create the ridiculously small first task"""
    uid = session['user_id']
    archetype = (db.get_archetype(uid) or {}).get('archetype', 'explorer')
    tasks_map = {
        'builder':  ('Buka editor kode dan tulis 1 baris komentar', 'tech'),
        'zen':      ('Tarik napas dalam 3x dan senyum sebentar', 'health'),
        'achiever': ('Tulis 1 goal hari ini di kertas atau notes', 'general'),
        'explorer': ('Buka satu artikel menarik dan baca 1 paragraf', 'study'),
    }
    title, cat = tasks_map.get(archetype, ('Minum satu gelas air putih sekarang', 'health'))
    task_id = db.create_task(uid, {
        'title': title, 'category': cat,
        'priority': 'low', 'duration_min': 2,
        'task_date': date.today().isoformat(),
        'description': 'Tugas pertamamu — cuma 1-2 menit. Mulai dari sini!'
    })
    return jsonify({'id': task_id, 'title': title})

# ─── ESQ RENAME (was ISQ) ──────────────────────────────────────────────────────
# /isq route already exists above — just add alias
@app.route('/esq')
@login_required
def esq_redirect():
    return redirect(url_for('isq_page'))


# ─── PUSH NOTIFICATION SENDER ──────────────────────────────────────────────────
def _send_push(user_id, title, body, url='/tasks'):
    """Send Web Push notification to all subscriptions of a user"""
    try:
        from pywebpush import webpush, WebPushException
        subs = db.get_push_subscriptions_for_user(user_id)
        for sub in subs:
            if not sub.get('endpoint'): continue
            payload = _json.dumps({'title': title, 'body': body, 'url': url})
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub['endpoint'],
                        'keys': {'p256dh': sub['p256dh'], 'auth': sub['auth_key']}
                    },
                    data=payload,
                    vapid_private_key=app.config.get('VAPID_PRIVATE_KEY',''),
                    vapid_claims={'sub': 'mailto:admin@dailyactivity.app'}
                )
            except Exception as e:
                print(f"[PUSH] Failed for user {user_id}: {e}")
    except ImportError:
        pass  # pywebpush not installed, skip silently


def _scheduler_tick():
    """Run every minute — check scheduled tasks and send notifications"""
    from datetime import datetime, timedelta
    now   = datetime.now()
    tasks = db.get_all_scheduled_tasks_today()

    for t in tasks:
        if not t.get('start_time'): continue
        try:
            # parse start_time (could be HH:MM:SS or timedelta from MySQL)
            st_raw = t['start_time']
            if isinstance(st_raw, str):
                parts = st_raw.split(':')
                h, m = int(parts[0]), int(parts[1])
            else:
                total_sec = int(st_raw.total_seconds())
                h, m = total_sec // 3600, (total_sec % 3600) // 60

            task_start = now.replace(hour=h, minute=m, second=0, microsecond=0)
            diff_min   = (task_start - now).total_seconds() / 60
            name       = (t.get('full_name') or t.get('username') or 'kamu').split()[0]
            title_task = t['title']

            notif = None
            if 14 <= diff_min <= 16:
                notif = (f"⏰ {name}, 15 menit lagi!", f"Waktunya {title_task} sebentar lagi. Siap-siap ya!")
            elif 4 <= diff_min <= 6:
                notif = (f"🔔 {name}, 5 menit lagi!", f"{title_task} mau dimulai. Yuk bersiap!")
            elif -1 <= diff_min <= 1:
                notif = (f"🚀 Sekarang waktunya!", f"Hei {name}, waktunya {title_task}. Gas sekarang!")
            elif -16 <= diff_min <= -14:
                notif = (f"⚠️ {name}, sudah 15 menit!", f"{title_task} harusnya sudah jalan — belum done nih?")

            if notif:
                _send_push(t['user_id'], notif[0], notif[1])

        except Exception as e:
            print(f"[SCHEDULER] Error on task {t.get('id')}: {e}")


# ─── API: GET SCHEDULED TASKS ──────────────────────────────────────────────────
@app.route('/api/tasks/scheduled')
@login_required
def api_scheduled_tasks():
    tasks = db.get_tasks_with_schedule(session['user_id'])
    return jsonify({'tasks': tasks})


# ─── API: SET TIME PROMPT (check if task needs time) ──────────────────────────
@app.route('/api/tasks/<int:task_id>/set-time', methods=['POST'])
@login_required
def api_set_task_time(task_id):
    data = request.get_json()
    start = data.get('start_time')
    end   = data.get('end_time')
    if not start:
        return jsonify({'error': 'start_time wajib'}), 400
    if not end:
        return jsonify({'error': 'end_time wajib jika start_time diisi'}), 400
    conn = db.get_connection()
    if not conn: return jsonify({'error': 'DB'}), 500
    c = conn.cursor()
    c.execute("""
        UPDATE daily_tasks SET start_time=%s, end_time=%s, updated_at=NOW()
        WHERE id=%s AND user_id=%s
    """, (start, end, task_id, session['user_id']))
    conn.commit(); ok = c.rowcount > 0
    c.close(); conn.close()
    return jsonify({'ok': ok})

# ═══════════════════════════════════════════════════
# REMINDER ROUTES
# ═══════════════════════════════════════════════════

@app.route('/reminders')
@login_required
def reminders_page():
    reminders  = db.get_reminders(session['user_id'])
    today_logs = db.get_today_reminder_logs(session['user_id'])
    templates  = db.get_reminder_templates()
    # Pisah per kategori template
    tpl_by_cat = {}
    for t in templates:
        tpl_by_cat.setdefault(t['category'], []).append(t)
    return render_template('reminders.html',
        reminders=reminders,
        today_logs=today_logs,
        tpl_by_cat=tpl_by_cat,
    )

# ── CRUD Reminder ──────────────────────────────────
@app.route('/api/reminders', methods=['GET'])
@login_required
def api_get_reminders():
    items = db.get_reminders(session['user_id'])
    logs  = db.get_today_reminder_logs(session['user_id'])
    return jsonify({'reminders': items, 'today_logs': logs})

@app.route('/api/reminders', methods=['POST'])
@login_required
def api_create_reminder():
    d = request.get_json() or {}
    if not d.get('title') or not d.get('remind_time'):
        return jsonify({'error': 'title dan remind_time wajib'}), 400
    conn = db.get_connection()
    if not conn: return jsonify({'error': 'DB'}), 500
    c = conn.cursor(dictionary=True)
    try:
        import json
        repeat_days = d.get('repeat_days')
        if isinstance(repeat_days, list):
            repeat_days = json.dumps(repeat_days)
        c.execute("""
            INSERT INTO reminders
                (user_id, title, emoji, remind_time, repeat_type,
                 repeat_days, snooze_minutes, is_active,
                 has_quantity, quantity_target, quantity_unit,
                 category, color, sort_order)
            VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            d['title'].strip(),
            d.get('emoji', '🔔'),
            d['remind_time'],
            d.get('repeat_type', 'daily'),
            repeat_days,
            int(d.get('snooze_minutes', 30)),
            bool(d.get('has_quantity', False)),
            d.get('quantity_target'),
            d.get('quantity_unit', ''),
            d.get('category', 'general'),
            d.get('color', '#6366f1'),
            int(d.get('sort_order', 0)),
        ))
        new_id = c.lastrowid
        conn.commit()
        return jsonify({'id': new_id, 'ok': True}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        c.close(); conn.close()

@app.route('/api/reminders/<int:rid>', methods=['PUT'])
@login_required
def api_update_reminder(rid):
    d = request.get_json() or {}
    conn = db.get_connection()
    if not conn: return jsonify({'error': 'DB'}), 500
    c = conn.cursor()
    try:
        import json
        repeat_days = d.get('repeat_days')
        if isinstance(repeat_days, list):
            repeat_days = json.dumps(repeat_days)
        c.execute("""
            UPDATE reminders SET
                title=%s, emoji=%s, remind_time=%s,
                repeat_type=%s, repeat_days=%s, snooze_minutes=%s,
                has_quantity=%s, quantity_target=%s, quantity_unit=%s,
                category=%s, color=%s, is_active=%s
            WHERE id=%s AND user_id=%s
        """, (
            d.get('title'), d.get('emoji','🔔'),
            d.get('remind_time'), d.get('repeat_type','daily'),
            repeat_days, int(d.get('snooze_minutes',30)),
            bool(d.get('has_quantity',False)),
            d.get('quantity_target'), d.get('quantity_unit',''),
            d.get('category','general'), d.get('color','#6366f1'),
            bool(d.get('is_active', True)),
            rid, session['user_id']
        ))
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        c.close(); conn.close()

@app.route('/api/reminders/<int:rid>', methods=['DELETE'])
@login_required
def api_delete_reminder(rid):
    conn = db.get_connection()
    if not conn: return jsonify({'error': 'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("DELETE FROM reminders WHERE id=%s AND user_id=%s",
                  (rid, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

@app.route('/api/reminders/<int:rid>/toggle-active', methods=['POST'])
@login_required
def api_toggle_reminder(rid):
    conn = db.get_connection()
    if not conn: return jsonify({'error': 'DB'}), 500
    c = conn.cursor(dictionary=True)
    try:
        c.execute("SELECT is_active FROM reminders WHERE id=%s AND user_id=%s",
                  (rid, session['user_id']))
        row = c.fetchone()
        if not row: return jsonify({'error': 'Not found'}), 404
        new_val = not row['is_active']
        c.execute("UPDATE reminders SET is_active=%s WHERE id=%s",
                  (new_val, rid))
        conn.commit()
        return jsonify({'ok': True, 'is_active': new_val})
    finally:
        c.close(); conn.close()

# ── Complete / Uncheck ─────────────────────────────
@app.route('/api/reminders/<int:rid>/complete', methods=['POST'])
@login_required
def api_complete_reminder(rid):
    d = request.get_json() or {}
    result = db.complete_reminder(
        rid, session['user_id'],
        quantity_done=d.get('quantity_done'),
        note=d.get('note')
    )
    if result.get('milestone'):
        result['milestone_msg'] = f"🎉 {result['streak']} hari streak! Tier baru: {result['tier']}"
    return jsonify(result)

@app.route('/api/reminders/<int:rid>/uncheck', methods=['POST'])
@login_required
def api_uncheck_reminder(rid):
    ok = db.uncheck_reminder(rid, session['user_id'])
    return jsonify({'ok': ok})

# ── Today summary (untuk dashboard widget) ─────────
@app.route('/api/reminders/today', methods=['GET'])
@login_required
def api_reminders_today():
    from datetime import date
    reminders  = db.get_reminders(session['user_id'])
    today_logs = db.get_today_reminder_logs(session['user_id'])
    today      = date.today()
    day_of_week = today.weekday()  # 0=Mon..6=Sun

    result = []
    for r in reminders:
        if not r.get('is_active'): continue
        # Filter by repeat_type
        rt = r.get('repeat_type', 'daily')
        if rt == 'weekdays' and day_of_week >= 5: continue
        if rt == 'weekend'  and day_of_week < 5:  continue
        if rt == 'weekly':
            import json
            days = r.get('repeat_days') or []
            if isinstance(days, str):
                try: days = json.loads(days)
                except: days = []
            if day_of_week not in days: continue

        log = today_logs.get(r['id'], {})
        r['done']        = bool(log.get('completed_at'))
        r['log']         = log
        result.append(r)

    done  = sum(1 for r in result if r['done'])
    total = len(result)
    return jsonify({
        'reminders': result,
        'done': done,
        'total': total,
        'pct': round(done/total*100) if total else 0,
    })

# ── Templates ──────────────────────────────────────
@app.route('/api/reminders/templates', methods=['GET'])
@login_required
def api_reminder_templates():
    templates = db.get_reminder_templates()
    return jsonify(templates)

@app.route('/api/reminders/templates/<int:tid>/install', methods=['POST'])
@login_required
def api_install_template(tid):
    ids = db.install_template(tid, session['user_id'])
    if not ids:
        return jsonify({'error': 'Template tidak ditemukan'}), 404
    return jsonify({'ok': True, 'created': len(ids), 'ids': ids})

# ── Reorder ────────────────────────────────────────
@app.route('/api/reminders/reorder', methods=['POST'])
@login_required
def api_reorder_reminders():
    d = request.get_json() or {}
    order = d.get('order', [])  # list of ids
    conn = db.get_connection()
    if not conn: return jsonify({'error': 'DB'}), 500
    c = conn.cursor()
    try:
        for idx, rid in enumerate(order):
            c.execute(
                "UPDATE reminders SET sort_order=%s WHERE id=%s AND user_id=%s",
                (idx, rid, session['user_id'])
            )
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

# ═══════════════════════════════════════════════════
# DAILY FOCUS ROUTES
# ═══════════════════════════════════════════════════

@app.route('/api/focus/today', methods=['GET'])
@login_required
def api_focus_today():
    items = db.get_daily_focus(session['user_id'])
    for i in items:
        if i.get('focus_date'):
            i['focus_date'] = str(i['focus_date'])
        if i.get('done_at'):
            i['done_at'] = i['done_at'].isoformat()
    return jsonify(items)

@app.route('/api/focus/<int:fid>/done', methods=['POST'])
@login_required
def api_focus_done(fid):
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("""UPDATE daily_focus SET is_done=TRUE, done_at=NOW()
                     WHERE id=%s AND user_id=%s""",
                  (fid, session['user_id']))
        conn.commit()
        db.award_xp(session['user_id'], 'task_done', 'Daily focus selesai', fid)
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

@app.route('/api/focus/regenerate', methods=['POST'])
@login_required
def api_focus_regen():
    items = db.generate_daily_focus(session['user_id'])
    return jsonify(items)

# ═══════════════════════════════════════════════════
# XP / LEVEL ROUTES
# ═══════════════════════════════════════════════════

@app.route('/api/xp', methods=['GET'])
@login_required
def api_get_xp():
    info = db.get_user_xp(session['user_id'])
    return jsonify(info)

@app.route('/api/xp/logs', methods=['GET'])
@login_required
def api_xp_logs():
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""SELECT * FROM xp_logs WHERE user_id=%s
                     ORDER BY earned_at DESC LIMIT 50""",
                  (session['user_id'],))
        rows = c.fetchall()
        for r in rows:
            if r.get('earned_at'):
                r['earned_at'] = r['earned_at'].isoformat()
        return jsonify(rows)
    finally:
        c.close(); conn.close()

# ═══════════════════════════════════════════════════
# GOAL LINKED STATS
# ═══════════════════════════════════════════════════

@app.route('/api/goals/<int:gid>/stats', methods=['GET'])
@login_required
def api_goal_stats(gid):
    stats = db.get_goal_linked_stats(gid, session['user_id'])
    return jsonify(stats)

@app.route('/api/reminders/<int:rid>/link-goal', methods=['POST'])
@login_required
def api_link_reminder_goal(rid):
    d = request.get_json() or {}
    goal_id = d.get('goal_id')
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("UPDATE reminders SET goal_id=%s WHERE id=%s AND user_id=%s",
                  (goal_id, rid, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

@app.route('/api/tasks/<int:tid>/link-goal', methods=['POST'])
@login_required
def api_link_task_goal(tid):
    d = request.get_json() or {}
    goal_id = d.get('goal_id')
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("UPDATE daily_tasks SET goal_id=%s WHERE id=%s AND user_id=%s",
                  (goal_id, tid, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

# ═══════════════════════════════════════════════════
# FINANCE PAGE + ROUTES
# ═══════════════════════════════════════════════════

@app.route('/finance')
@login_required
def finance_page():
    savings   = db.get_savings_summary(session['user_id'])
    portfolio = db.get_portfolio_summary(session['user_id'])
    # Fixed expenses
    conn = db.get_connection()
    expenses = []
    currencies = []
    if conn:
        c = conn.cursor(dictionary=True)
        c.execute("""SELECT fe.*, cur.symbol FROM fixed_expenses fe
                     LEFT JOIN currencies cur ON cur.code = fe.currency
                     WHERE fe.user_id=%s AND fe.is_active=1
                     ORDER BY fe.amount DESC""",
                  (session['user_id'],))
        expenses = c.fetchall()
        for e in expenses:
            e['amount'] = float(e['amount'])
        c.execute("SELECT * FROM currencies ORDER BY code")
        currencies = c.fetchall()
        c.close(); conn.close()

    goals_list = db.get_goals_with_progress(session['user_id'])
    xp_info    = db.get_user_xp(session['user_id'])
    return render_template('finance.html',
        savings=savings, portfolio=portfolio,
        expenses=expenses, currencies=currencies,
        goals=goals_list, xp_info=xp_info,
    )

# ── Savings Goals CRUD ─────────────────────────────
@app.route('/api/savings', methods=['GET'])
@login_required
def api_get_savings():
    return jsonify(db.get_savings_summary(session['user_id']))

@app.route('/api/savings', methods=['POST'])
@login_required
def api_create_savings():
    d = request.get_json() or {}
    if not d.get('title') or not d.get('target_amount'):
        return jsonify({'error': 'title dan target_amount wajib'}), 400
    from datetime import date
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO savings_goals
                (user_id, goal_id, title, emoji, target_amount, currency,
                 period, period_amount, start_date, target_date, color, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            d.get('goal_id') or None,
            d['title'].strip(),
            d.get('emoji', '💰'),
            float(d['target_amount']),
            d.get('currency', 'IDR'),
            d.get('period', 'weekly'),
            float(d.get('period_amount', 0)),
            d.get('start_date', date.today().isoformat()),
            d.get('target_date') or None,
            d.get('color', '#10b981'),
            d.get('notes', ''),
        ))
        new_id = c.lastrowid
        conn.commit()
        # Auto-create reminder if period_amount > 0
        if float(d.get('period_amount', 0)) > 0 and d.get('create_reminder'):
            period = d.get('period', 'weekly')
            repeat = 'weekly' if period == 'weekly' else 'monthly'
            c.execute("""
                INSERT INTO reminders
                    (user_id, title, emoji, remind_time, repeat_type,
                     snooze_minutes, category, color, goal_id)
                VALUES (%s,%s,%s,'08:00',%s,30,'kesehatan',%s,%s)
            """, (
                session['user_id'],
                f"Setor tabungan: {d['title']}",
                d.get('emoji', '💰'),
                repeat,
                d.get('color', '#10b981'),
                d.get('goal_id') or None,
            ))
            conn.commit()
        db.award_xp(session['user_id'], 'saving_deposit', 'Buat savings goal baru', new_id)
        return jsonify({'ok': True, 'id': new_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        c.close(); conn.close()

@app.route('/api/savings/<int:sid>', methods=['PUT'])
@login_required
def api_update_savings(sid):
    d = request.get_json() or {}
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE savings_goals SET
                title=%s, emoji=%s, target_amount=%s, currency=%s,
                period=%s, period_amount=%s, target_date=%s,
                color=%s, notes=%s, goal_id=%s
            WHERE id=%s AND user_id=%s
        """, (
            d.get('title'), d.get('emoji','💰'),
            float(d.get('target_amount',0)), d.get('currency','IDR'),
            d.get('period','weekly'), float(d.get('period_amount',0)),
            d.get('target_date') or None,
            d.get('color','#10b981'), d.get('notes',''),
            d.get('goal_id') or None,
            sid, session['user_id']
        ))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

@app.route('/api/savings/<int:sid>', methods=['DELETE'])
@login_required
def api_delete_savings(sid):
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("DELETE FROM savings_goals WHERE id=%s AND user_id=%s",
                  (sid, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

@app.route('/api/savings/<int:sid>/deposit', methods=['POST'])
@login_required
def api_savings_deposit(sid):
    d = request.get_json() or {}
    from datetime import date
    result = db.add_saving_log(
        sid, session['user_id'],
        amount   = float(d.get('amount', 0)),
        currency = d.get('currency', 'IDR'),
        log_date = d.get('log_date', date.today().isoformat()),
        log_type = d.get('type', 'deposit'),
        note     = d.get('note', ''),
    )
    return jsonify(result)

@app.route('/api/savings/<int:sid>/logs', methods=['GET'])
@login_required
def api_savings_logs(sid):
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""
            SELECT sl.*, cur.symbol FROM saving_logs sl
            LEFT JOIN currencies cur ON cur.code = sl.currency
            WHERE sl.savings_goal_id=%s AND sl.user_id=%s
            ORDER BY sl.log_date DESC LIMIT 50
        """, (sid, session['user_id']))
        rows = c.fetchall()
        for r in rows:
            r['amount'] = float(r['amount'])
            if r.get('log_date'):
                r['log_date'] = r['log_date'].isoformat()
        return jsonify(rows)
    finally:
        c.close(); conn.close()

# ── Investments CRUD ───────────────────────────────
@app.route('/api/investments', methods=['GET'])
@login_required
def api_get_investments():
    return jsonify(db.get_portfolio_summary(session['user_id']))

@app.route('/api/investments', methods=['POST'])
@login_required
def api_create_investment():
    d = request.get_json() or {}
    if not d.get('title') or not d.get('buy_price'):
        return jsonify({'error': 'title dan buy_price wajib'}), 400
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO investments
                (user_id, goal_id, title, type, emoji, buy_price, units,
                 currency, buy_date, current_price, platform, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            d.get('goal_id') or None,
            d['title'].strip(),
            d.get('type', 'lainnya'),
            d.get('emoji', '📈'),
            float(d['buy_price']),
            float(d.get('units', 1)),
            d.get('currency', 'IDR'),
            d.get('buy_date'),
            float(d['buy_price']),
            d.get('platform', ''),
            d.get('notes', ''),
        ))
        new_id = c.lastrowid
        conn.commit()
        db.award_xp(session['user_id'], 'investment_added', 'Tambah investasi baru', new_id)
        return jsonify({'ok': True, 'id': new_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        c.close(); conn.close()

@app.route('/api/investments/<int:iid>/update-price', methods=['POST'])
@login_required
def api_update_price(iid):
    d = request.get_json() or {}
    price = float(d.get('price', 0))
    if price <= 0: return jsonify({'error': 'Harga tidak valid'}), 400
    from datetime import date
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("""UPDATE investments SET current_price=%s, price_updated_at=NOW()
                     WHERE id=%s AND user_id=%s""",
                  (price, iid, session['user_id']))
        c.execute("""INSERT INTO investment_logs
                        (investment_id, user_id, type, price, log_date)
                     VALUES (%s,%s,'price_update',%s,%s)""",
                  (iid, session['user_id'], price, date.today().isoformat()))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

@app.route('/api/investments/<int:iid>', methods=['DELETE'])
@login_required
def api_delete_investment(iid):
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("DELETE FROM investments WHERE id=%s AND user_id=%s",
                  (iid, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

# ── Fixed Expenses CRUD ────────────────────────────
@app.route('/api/expenses', methods=['GET'])
@login_required
def api_get_expenses():
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    try:
        c.execute("""SELECT fe.*, cur.symbol FROM fixed_expenses fe
                     LEFT JOIN currencies cur ON cur.code = fe.currency
                     WHERE fe.user_id=%s AND fe.is_active=1
                     ORDER BY fe.amount DESC""",
                  (session['user_id'],))
        rows = c.fetchall()
        for r in rows: r['amount'] = float(r['amount'])
        return jsonify(rows)
    finally:
        c.close(); conn.close()

@app.route('/api/expenses', methods=['POST'])
@login_required
def api_create_expense():
    d = request.get_json() or {}
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO fixed_expenses
                (user_id, title, emoji, amount, currency, category, billing_day, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            d.get('title','').strip(),
            d.get('emoji','💳'),
            float(d.get('amount', 0)),
            d.get('currency','IDR'),
            d.get('category','lainnya'),
            int(d.get('billing_day', 1)),
            d.get('notes',''),
        ))
        conn.commit()
        return jsonify({'ok': True, 'id': c.lastrowid}), 201
    finally:
        c.close(); conn.close()

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
@login_required
def api_delete_expense(eid):
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("DELETE FROM fixed_expenses WHERE id=%s AND user_id=%s",
                  (eid, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

# ── Currency rates update ──────────────────────────
@app.route('/api/currencies', methods=['GET'])
@login_required
def api_get_currencies():
    conn = db.get_connection()
    if not conn: return jsonify([])
    c = conn.cursor(dictionary=True)
    try:
        c.execute("SELECT * FROM currencies ORDER BY code")
        rows = c.fetchall()
        for r in rows: r['rate_to_idr'] = float(r['rate_to_idr'])
        return jsonify(rows)
    finally:
        c.close(); conn.close()

@app.route('/api/currencies/<code>/rate', methods=['PUT'])
@login_required
def api_update_rate(code):
    d = request.get_json() or {}
    rate = float(d.get('rate', 1))
    conn = db.get_connection()
    if not conn: return jsonify({'error':'DB'}), 500
    c = conn.cursor()
    try:
        c.execute("UPDATE currencies SET rate_to_idr=%s WHERE code=%s",
                  (rate, code.upper()))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        c.close(); conn.close()

if __name__ == '__main__':
    print("🚀 Initializing database...")
    if db.init_db():
        db.add_tables_v2()
        db.add_tables_v3()
        db.add_tables_v4()
        print("✅ App ready! Buka http://localhost:5000")
        print("   Demo login: admin / admin123")
        # Start APScheduler
        _scheduler.add_job(
            func=_scheduler_tick,
            trigger=IntervalTrigger(minutes=1),
            id='task_notif_tick',
            replace_existing=True
        )
        _scheduler.start()
        atexit.register(lambda: _scheduler.shutdown())
        print("⏰ Scheduler started — task notifications active")
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    else:
        print("❌ Database gagal. Cek XAMPP & db.py")
