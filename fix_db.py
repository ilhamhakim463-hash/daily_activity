"""
fix_db.py — Jalankan sekali untuk repair database ActivityOS
Usage: python fix_db.py
"""
import sys
sys.path.insert(0, '.')
import db as dbmod

print("=" * 50)
print("ActivityOS — Database Repair Tool")
print("=" * 50)

conn = dbmod.get_connection()
if not conn:
    print("❌ Tidak bisa konek ke MySQL! Pastikan XAMPP jalan dan port 3307 benar.")
    sys.exit(1)

cursor = conn.cursor()

# 1. Pastikan kolom start_time & end_time ada di daily_tasks
print("\n[1] Cek kolom daily_tasks...")
cursor.execute("SHOW COLUMNS FROM daily_tasks")
cols = {r[0] for r in cursor.fetchall()}
print(f"    Kolom ada: {sorted(cols)}")

if 'start_time' not in cols:
    cursor.execute("ALTER TABLE daily_tasks ADD COLUMN start_time TIME NULL")
    print("    ✅ Kolom start_time ditambahkan")
if 'end_time' not in cols:
    cursor.execute("ALTER TABLE daily_tasks ADD COLUMN end_time TIME NULL")
    print("    ✅ Kolom end_time ditambahkan")
if 'tags' not in cols:
    cursor.execute("ALTER TABLE daily_tasks ADD COLUMN tags VARCHAR(255) DEFAULT ''")
    print("    ✅ Kolom tags ditambahkan")

# 2. Pastikan priority ENUM benar (ada 'urgent')
print("\n[2] Cek ENUM priority...")
cursor.execute("SHOW COLUMNS FROM daily_tasks LIKE 'priority'")
row = cursor.fetchone()
if row:
    col_type = str(row[1])
    print(f"    Type: {col_type}")
    if 'urgent' not in col_type:
        cursor.execute("ALTER TABLE daily_tasks MODIFY COLUMN priority ENUM('low','medium','high','urgent') DEFAULT 'medium'")
        print("    ✅ ENUM priority diperbaiki (urgent ditambahkan)")
    else:
        print("    ✅ ENUM priority sudah benar")

# 3. Pastikan tabel quick_notes ada (untuk fitur Quick Notes di Dashboard)
print("\n[3] Cek tabel quick_notes...")
cursor.execute("SHOW TABLES")
existing_tables = {r[0] for r in cursor.fetchall()}
if 'quick_notes' not in existing_tables:
    cursor.execute("""
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
    conn.commit()
    print("    ✅ Tabel quick_notes berhasil dibuat!")
else:
    print("    ✅ quick_notes sudah ada")

if 'login_logs' not in existing_tables:
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
    print("    ✅ Tabel login_logs berhasil dibuat!")
else:
    print("    ✅ login_logs sudah ada")

# 3b. Cek tabel lainnya
print("\n[3b] Cek tabel tambahan...")
tables_needed = ['user_archetype', 'time_capsules', 'ghost_snapshots', 'push_subscriptions', 'isq_morning', 'isq_evening']
cursor.execute("SHOW TABLES")
existing = {r[0] for r in cursor.fetchall()}
for t in tables_needed:
    if t in existing:
        print(f"    ✅ {t} ada")
    else:
        print(f"    ⚠️  {t} tidak ada — akan dibuat oleh init_db()")

# 4. Jalankan init_db untuk buat tabel yang kurang
print("\n[4] Jalankan init_db untuk tabel yang kurang...")
try:
    dbmod.init_db()
    print("    ✅ init_db selesai")
except Exception as e:
    print(f"    ⚠️  init_db error: {e}")

# 5. Cek apakah ada user demo
print("\n[5] Cek user demo...")
cursor.execute("SELECT id, username FROM users LIMIT 5")
users = cursor.fetchall()
if users:
    for u in users:
        print(f"    User #{u[0]}: {u[1]}")
else:
    print("    ⚠️  Tidak ada user! Jalankan python app.py untuk seed demo data")

# 6. Test query daily_tasks
print("\n[6] Test query daily_tasks...")
try:
    cursor.execute("SELECT COUNT(*) FROM daily_tasks")
    count = cursor.fetchone()[0]
    print(f"    Total tasks: {count}")
    cursor.execute("SELECT id, title, task_date, start_time, end_time FROM daily_tasks LIMIT 3")
    rows = cursor.fetchall()
    for r in rows:
        print(f"    Task #{r[0]}: '{r[1]}' | date={r[2]} | start={r[3]} | end={r[4]}")
except Exception as e:
    print(f"    ❌ Error: {e}")

conn.commit()
cursor.close()
conn.close()

print("\n" + "=" * 50)
print("✅ Database repair selesai! Sekarang jalankan: python app.py")
print("=" * 50)

# ═══════════════════════════════════════════════════════
# SECURITY MIGRATION v2 — Jalankan setelah update kode
# ═══════════════════════════════════════════════════════
print("\n" + "="*50)
print("SECURITY MIGRATION v2")
print("="*50)

conn2 = dbmod.get_connection()
if conn2:
    c = conn2.cursor()

    migrations = [
        # Kolom baru di users
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE",
         "users.is_admin"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_attempts INT DEFAULT 0",
         "users.failed_attempts"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until DATETIME NULL",
         "users.locked_until"),
        ("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login DATETIME NULL",
         "users.last_login"),

        # Tabel login_logs baru
        ("""CREATE TABLE IF NOT EXISTS login_logs (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            action      VARCHAR(50) NOT NULL,
            ip_address  VARCHAR(45),
            detail      VARCHAR(255),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_created_at (created_at)
        )""", "login_logs table"),
    ]

    for sql, label in migrations:
        try:
            c.execute(sql)
            conn2.commit()
            print(f"  ✅ {label}")
        except Exception as e:
            print(f"  ⚠️  {label}: {e}")

    # Set admin=TRUE untuk user 'admin'
    try:
        c.execute("UPDATE users SET is_admin=TRUE WHERE username='admin'")
        conn2.commit()
        print("  ✅ user 'admin' set is_admin=TRUE")
    except Exception as e:
        print(f"  ⚠️  set admin: {e}")

    # Upgrade password admin dari SHA256 → PBKDF2
    # (hanya jika masih SHA256 format)
    try:
        c.execute("SELECT id, password FROM users WHERE username='admin'")
        row = c.fetchone()
        if row and not row[1].startswith('pbkdf2$'):
            new_hash = dbmod.hash_password('admin123')
            c.execute("UPDATE users SET password=%s WHERE id=%s", (new_hash, row[0]))
            conn2.commit()
            print("  ✅ Password admin di-upgrade ke PBKDF2")
            print("  ℹ️  Password admin masih: admin123 (ganti segera!)")
        else:
            print("  ✅ Password admin sudah PBKDF2")
    except Exception as e:
        print(f"  ⚠️  upgrade password: {e}")

    c.close()
    conn2.close()
    print("\n✅ Security migration selesai!")
    print("⚠️  PENTING: Ganti password admin segera di halaman /admin")
else:
    print("❌ Koneksi DB gagal untuk security migration")

# ── Migration: quick_notes note_date column ──
print("\n── quick_notes date migration ──")
try:
    conn3 = dbmod.get_connection()
    c3 = conn3.cursor()
    c3.execute("ALTER TABLE quick_notes ADD COLUMN note_date DATE NOT NULL DEFAULT '2024-01-01'")
    c3.execute("UPDATE quick_notes SET note_date = DATE(created_at)")
    conn3.commit()
    print("✅ quick_notes.note_date ditambahkan")
    c3.close()
    conn3.close()
except Exception as e:
    if '1060' in str(e) or 'Duplicate' in str(e):
        print("   note_date sudah ada ✅")
    else:
        print(f"   ⚠️  {e}")


# ══════════════════════════════════════════════════════
# MIGRATION: Reminder System — Sprint v5
# ══════════════════════════════════════════════════════
print("\n── Reminder System migration ──")

_reminder_tables = [
    ("reminders", """
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_rem_user_active (user_id, is_active),
            INDEX idx_rem_user_time   (user_id, remind_time)
        )
    """),
    ("reminder_logs", """
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
    """),
    ("reminder_streaks", """
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
    """),
    ("reminder_groups", """
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
    """),
    ("reminder_group_members", """
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
    """),
    ("reminder_group_challenges", """
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
    """),
    ("reminder_challenge_logs", """
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
    """),
    ("reminder_templates", """
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
    """),
]

try:
    conn_r = dbmod.get_connection()
    if not conn_r:
        raise Exception("Tidak bisa konek ke DB")
    cr = conn_r.cursor(dictionary=True)

    for tname, sql in _reminder_tables:
        try:
            cr.execute(sql)
            conn_r.commit()
            print(f"   ✅ {tname}")
        except Exception as e:
            if '1050' in str(e) or 'already exists' in str(e).lower():
                print(f"   ✓  {tname} (sudah ada)")
            else:
                print(f"   ⚠️  {tname}: {e}")

    # Seed built-in templates
    cr.execute("SELECT COUNT(*) as n FROM reminder_templates WHERE is_builtin=1")
    row = cr.fetchone()
    if (row['n'] if row else 0) == 0:
        import json as _json
        _builtin = [
            ('Paket Ibadah', 'Sholat 5 waktu, Al-Quran, dan dzikir harian', 'ibadah', '🕌',
             _json.dumps([
                {'title':'Sholat Subuh',  'emoji':'🌅','remind_time':'04:30','snooze_minutes':10,'category':'ibadah','color':'#6366f1'},
                {'title':'Sholat Dzuhur', 'emoji':'☀️','remind_time':'12:00','snooze_minutes':15,'category':'ibadah','color':'#6366f1'},
                {'title':'Sholat Ashar',  'emoji':'🌤','remind_time':'15:30','snooze_minutes':15,'category':'ibadah','color':'#6366f1'},
                {'title':'Sholat Maghrib','emoji':'🌆','remind_time':'18:00','snooze_minutes':10,'category':'ibadah','color':'#6366f1'},
                {'title':'Sholat Isya',   'emoji':'🌙','remind_time':'19:30','snooze_minutes':15,'category':'ibadah','color':'#6366f1'},
                {'title':'Baca Al-Quran', 'emoji':'📖','remind_time':'05:00','snooze_minutes':30,'has_quantity':True,'quantity_target':1,'quantity_unit':'juz','category':'ibadah','color':'#10b981'},
                {'title':'Dzikir Pagi',   'emoji':'🌿','remind_time':'06:00','snooze_minutes':20,'category':'ibadah','color':'#10b981'},
                {'title':'Dzikir Malam',  'emoji':'✨','remind_time':'21:00','snooze_minutes':20,'category':'ibadah','color':'#8b5cf6'},
             ])),
            ('Paket Kesehatan', 'Olahraga, hidrasi, tidur, dan vitamin', 'kesehatan', '💪',
             _json.dumps([
                {'title':'Minum Air Pagi',   'emoji':'💧','remind_time':'07:00','snooze_minutes':30,'has_quantity':True,'quantity_target':2,'quantity_unit':'gelas','category':'kesehatan','color':'#0ea5e9'},
                {'title':'Minum Air Siang',  'emoji':'💧','remind_time':'12:00','snooze_minutes':30,'has_quantity':True,'quantity_target':2,'quantity_unit':'gelas','category':'kesehatan','color':'#0ea5e9'},
                {'title':'Minum Air Sore',   'emoji':'💧','remind_time':'16:00','snooze_minutes':30,'has_quantity':True,'quantity_target':2,'quantity_unit':'gelas','category':'kesehatan','color':'#0ea5e9'},
                {'title':'Olahraga',         'emoji':'🏃','remind_time':'06:00','snooze_minutes':30,'has_quantity':True,'quantity_target':30,'quantity_unit':'menit','category':'kesehatan','color':'#f59e0b'},
                {'title':'Minum Vitamin',    'emoji':'💊','remind_time':'08:00','snooze_minutes':60,'category':'kesehatan','color':'#ec4899'},
                {'title':'Tidur Tepat Waktu','emoji':'😴','remind_time':'22:00','snooze_minutes':30,'category':'kesehatan','color':'#8b5cf6'},
             ])),
            ('Paket Produktivitas', 'Review pagi, fokus kerja, dan refleksi malam', 'produktivitas', '⚡',
             _json.dumps([
                {'title':'Review Tasks Pagi',  'emoji':'📋','remind_time':'07:30','snooze_minutes':15,'category':'produktivitas','color':'#6366f1'},
                {'title':'Deep Work Pagi',     'emoji':'🎯','remind_time':'08:00','snooze_minutes':30,'has_quantity':True,'quantity_target':90,'quantity_unit':'menit','category':'produktivitas','color':'#f59e0b'},
                {'title':'Cek Progress Siang', 'emoji':'📊','remind_time':'13:00','snooze_minutes':30,'category':'produktivitas','color':'#6366f1'},
                {'title':'Baca Buku',          'emoji':'📚','remind_time':'20:00','snooze_minutes':30,'has_quantity':True,'quantity_target':20,'quantity_unit':'halaman','category':'produktivitas','color':'#10b981'},
                {'title':'Jurnal Malam',       'emoji':'📝','remind_time':'21:30','snooze_minutes':30,'category':'produktivitas','color':'#8b5cf6'},
                {'title':'Review Hari Ini',    'emoji':'🌙','remind_time':'22:00','snooze_minutes':20,'category':'produktivitas','color':'#8b5cf6'},
             ])),
        ]
        for name, desc, cat, emoji, tdata in _builtin:
            cr.execute("""
                INSERT INTO reminder_templates
                    (user_id, name, description, category, emoji, template_data, is_builtin)
                VALUES (NULL, %s, %s, %s, %s, %s, TRUE)
            """, (name, desc, cat, emoji, tdata))
        conn_r.commit()
        print("   ✅ Built-in templates seeded (3 paket)")
    else:
        print("   ✓  Built-in templates (sudah ada)")

    cr.close()
    conn_r.close()
    print("\n✅ Reminder System migration selesai!")

except Exception as e:
    print(f"❌ Reminder migration error: {e}")


# ══════════════════════════════════════════════════════
# MIGRATION: Sprint v5 — Goal Connection + Finance + XP
# ══════════════════════════════════════════════════════
print("\n── Sprint v5 migration ──")

try:
    conn_v5 = dbmod.get_connection()
    if not conn_v5:
        raise Exception("Tidak bisa konek ke DB")
    cv5 = conn_v5.cursor(dictionary=True)

    # ── ADD COLUMNS (ALTER TABLE, skip jika sudah ada) ──
    alter_ops = [
        ("reminders",   "goal_id INT NULL DEFAULT NULL"),
        ("daily_tasks", "goal_id INT NULL DEFAULT NULL"),
    ]
    for table, col_def in alter_ops:
        col_name = col_def.split()[0]
        try:
            cv5.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            conn_v5.commit()
            print(f"   ✅ {table}.{col_name} ditambahkan")
        except Exception as e:
            if '1060' in str(e) or 'Duplicate' in str(e):
                print(f"   ✓  {table}.{col_name} (sudah ada)")
            else:
                print(f"   ⚠️  {table}.{col_name}: {e}")

    # ── ADD FK INDEXES ──
    fk_ops = [
        ("reminders",   "fk_rem_goal",   "goal_id", "goals", "id"),
        ("daily_tasks", "fk_task_goal",  "goal_id", "goals", "id"),
    ]
    for table, fk_name, col, ref_table, ref_col in fk_ops:
        try:
            cv5.execute(f"""
                ALTER TABLE {table}
                ADD CONSTRAINT {fk_name}
                FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col})
                ON DELETE SET NULL
            """)
            conn_v5.commit()
            print(f"   ✅ FK {fk_name} added")
        except Exception as e:
            if '1826' in str(e) or '1005' in str(e) or 'already exists' in str(e).lower() or 'Duplicate' in str(e):
                print(f"   ✓  FK {fk_name} (sudah ada)")
            else:
                print(f"   ⚠️  FK {fk_name}: {e}")

    # ── CREATE NEW TABLES ──
    import json as _json
    new_tables_v5 = [
        ("daily_focus", """
            CREATE TABLE IF NOT EXISTS daily_focus (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL, focus_date DATE NOT NULL,
                rank TINYINT NOT NULL DEFAULT 1,
                source VARCHAR(30) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description VARCHAR(255),
                ref_type VARCHAR(30), ref_id INT,
                is_done BOOLEAN DEFAULT FALSE,
                done_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_focus (user_id, focus_date, rank),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_focus_date (user_id, focus_date)
            )
        """),
        ("currencies", """
            CREATE TABLE IF NOT EXISTS currencies (
                code VARCHAR(10) PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                symbol VARCHAR(5) NOT NULL,
                rate_to_idr DECIMAL(20,6) DEFAULT 1.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """),
        ("savings_goals", """
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL, goal_id INT NULL,
                title VARCHAR(200) NOT NULL,
                emoji VARCHAR(10) DEFAULT '💰',
                target_amount DECIMAL(20,2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'IDR',
                period ENUM('weekly','monthly','custom') DEFAULT 'weekly',
                period_amount DECIMAL(20,2) DEFAULT 0,
                start_date DATE NOT NULL,
                target_date DATE NULL,
                color VARCHAR(7) DEFAULT '#10b981',
                is_active BOOLEAN DEFAULT TRUE,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP NULL, notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
            )
        """),
        ("saving_logs", """
            CREATE TABLE IF NOT EXISTS saving_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                savings_goal_id INT NOT NULL, user_id INT NOT NULL,
                amount DECIMAL(20,2) NOT NULL,
                type ENUM('deposit','withdrawal','adjustment') DEFAULT 'deposit',
                currency VARCHAR(10) DEFAULT 'IDR',
                log_date DATE NOT NULL, note VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (savings_goal_id) REFERENCES savings_goals(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_savlog_goal (savings_goal_id, log_date),
                INDEX idx_savlog_user (user_id, log_date)
            )
        """),
        ("saving_streaks", """
            CREATE TABLE IF NOT EXISTS saving_streaks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                savings_goal_id INT NOT NULL UNIQUE, user_id INT NOT NULL,
                current_streak INT DEFAULT 0, longest_streak INT DEFAULT 0,
                total_periods INT DEFAULT 0, last_period VARCHAR(10) NULL,
                tier VARCHAR(20) DEFAULT 'pemula',
                tier_color VARCHAR(7) DEFAULT '#888780',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (savings_goal_id) REFERENCES savings_goals(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("investments", """
            CREATE TABLE IF NOT EXISTS investments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL, goal_id INT NULL,
                title VARCHAR(200) NOT NULL,
                type VARCHAR(30) DEFAULT 'lainnya',
                emoji VARCHAR(10) DEFAULT '📈',
                buy_price DECIMAL(20,6) NOT NULL,
                units DECIMAL(20,6) DEFAULT 1.0,
                currency VARCHAR(10) DEFAULT 'IDR',
                buy_date DATE NOT NULL,
                current_price DECIMAL(20,6) NULL,
                price_updated_at TIMESTAMP NULL,
                platform VARCHAR(100), notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
            )
        """),
        ("investment_logs", """
            CREATE TABLE IF NOT EXISTS investment_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                investment_id INT NOT NULL, user_id INT NOT NULL,
                type VARCHAR(20) DEFAULT 'price_update',
                price DECIMAL(20,6) NOT NULL,
                units DECIMAL(20,6) DEFAULT 0,
                log_date DATE NOT NULL, note VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (investment_id) REFERENCES investments(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_invlog_inv (investment_id, log_date)
            )
        """),
        ("fixed_expenses", """
            CREATE TABLE IF NOT EXISTS fixed_expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                emoji VARCHAR(10) DEFAULT '💳',
                amount DECIMAL(20,2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'IDR',
                category VARCHAR(30) DEFAULT 'lainnya',
                billing_day TINYINT DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                notes VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("weekly_reviews", """
            CREATE TABLE IF NOT EXISTS weekly_reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                week_start DATE NOT NULL, week_end DATE NOT NULL,
                tasks_done INT DEFAULT 0, tasks_total INT DEFAULT 0,
                reminders_done INT DEFAULT 0, reminders_total INT DEFAULT 0,
                avg_mood DECIMAL(4,2) DEFAULT NULL,
                streaks_gained INT DEFAULT 0, streaks_lost INT DEFAULT 0,
                saving_amount DECIMAL(20,2) DEFAULT 0,
                goal_progress JSON, top_streak JSON,
                summary_text TEXT, is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_review (user_id, week_start),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("user_xp", """
            CREATE TABLE IF NOT EXISTS user_xp (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                total_xp INT DEFAULT 0,
                level TINYINT DEFAULT 1,
                level_title VARCHAR(50) DEFAULT 'Pemula',
                level_color VARCHAR(7) DEFAULT '#888780',
                xp_to_next INT DEFAULT 100,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("xp_logs", """
            CREATE TABLE IF NOT EXISTS xp_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                xp_amount INT NOT NULL,
                source VARCHAR(50) NOT NULL,
                description VARCHAR(200),
                ref_id INT NULL,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_xp_user (user_id, earned_at)
            )
        """),
    ]

    for tname, sql in new_tables_v5:
        try:
            cv5.execute(sql)
            conn_v5.commit()
            print(f"   ✅ {tname}")
        except Exception as e:
            if '1050' in str(e) or 'already exists' in str(e).lower():
                print(f"   ✓  {tname} (sudah ada)")
            else:
                print(f"   ⚠️  {tname}: {e}")

    # ── Seed currencies ──
    cv5.execute("SELECT COUNT(*) as n FROM currencies")
    row = cv5.fetchone()
    if (row['n'] if row else 0) == 0:
        cv5.executemany(
            "INSERT IGNORE INTO currencies (code,name,symbol,rate_to_idr) VALUES (%s,%s,%s,%s)",
            [
                ('IDR','Rupiah Indonesia','Rp',1.0),
                ('USD','US Dollar','$',16000.0),
                ('EUR','Euro','€',17500.0),
                ('SGD','Singapore Dollar','S$',12000.0),
                ('MYR','Ringgit Malaysia','RM',3500.0),
                ('SAR','Riyal Saudi Arabia','SR',4200.0),
                ('GBP','British Pound','£',20000.0),
                ('JPY','Japanese Yen','¥',110.0),
                ('AUD','Australian Dollar','A$',10500.0),
            ]
        )
        conn_v5.commit()
        print("   ✅ Currencies seeded (9 mata uang)")
    else:
        print("   ✓  Currencies (sudah ada)")

    cv5.close()
    conn_v5.close()
    print("\n✅ Sprint v5 migration selesai!")
    print("   Total tabel baru: 11 (daily_focus, currencies, savings_goals,")
    print("   saving_logs, saving_streaks, investments, investment_logs,")
    print("   fixed_expenses, weekly_reviews, user_xp, xp_logs)")

except Exception as e:
    print(f"❌ Sprint v5 migration error: {e}")
    import traceback; traceback.print_exc()


# ══════════════════════════════════════════════════════
# MIGRATION: Sprint v6 — Kanban + Workspace + Share
# ══════════════════════════════════════════════════════
print("\n── Sprint v6: Kanban + Share migration ──")

try:
    conn_v6 = dbmod.get_connection()
    if not conn_v6:
        raise Exception("DB tidak tersedia")
    cv6 = conn_v6.cursor(dictionary=True)

    v6_tables = [
        ("boards", """
            CREATE TABLE IF NOT EXISTS boards (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL, goal_id INT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                emoji VARCHAR(10) DEFAULT '📋',
                theme VARCHAR(20) DEFAULT 'default',
                visibility ENUM('private','team','public') DEFAULT 'private',
                type ENUM('personal','project','team') DEFAULT 'personal',
                invite_code VARCHAR(8) NULL UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
            )
        """),
        ("board_columns", """
            CREATE TABLE IF NOT EXISTS board_columns (
                id INT AUTO_INCREMENT PRIMARY KEY,
                board_id INT NOT NULL,
                title VARCHAR(100) NOT NULL,
                color VARCHAR(7) DEFAULT '#888780',
                sort_order INT DEFAULT 0,
                wip_limit INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
            )
        """),
        ("board_members", """
            CREATE TABLE IF NOT EXISTS board_members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                board_id INT NOT NULL, user_id INT NOT NULL,
                role ENUM('owner','editor','viewer') DEFAULT 'editor',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_bm (board_id, user_id),
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("board_cards", """
            CREATE TABLE IF NOT EXISTS board_cards (
                id INT AUTO_INCREMENT PRIMARY KEY,
                board_id INT NOT NULL, column_id INT NOT NULL,
                user_id INT NOT NULL, assigned_to INT NULL, goal_id INT NULL,
                title VARCHAR(255) NOT NULL, description TEXT,
                priority ENUM('low','medium','high','urgent') DEFAULT 'medium',
                label_color VARCHAR(7) NULL, label_text VARCHAR(50) NULL,
                due_date DATE NULL, est_hours DECIMAL(5,2) NULL,
                is_recurring BOOLEAN DEFAULT FALSE, recur_type VARCHAR(20) NULL,
                sort_order INT DEFAULT 0,
                completed_at TIMESTAMP NULL, archived_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
                FOREIGN KEY (column_id) REFERENCES board_columns(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
            )
        """),
        ("card_subtasks", """
            CREATE TABLE IF NOT EXISTS card_subtasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                card_id INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                is_done BOOLEAN DEFAULT FALSE,
                done_at TIMESTAMP NULL,
                sort_order INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (card_id) REFERENCES board_cards(id) ON DELETE CASCADE
            )
        """),
        ("card_comments", """
            CREATE TABLE IF NOT EXISTS card_comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                card_id INT NOT NULL, user_id INT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (card_id) REFERENCES board_cards(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("share_reports", """
            CREATE TABLE IF NOT EXISTS share_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                type VARCHAR(30) NOT NULL,
                title VARCHAR(200),
                data JSON,
                platform VARCHAR(20) DEFAULT 'general',
                share_token VARCHAR(32) NOT NULL UNIQUE,
                expires_at TIMESTAMP NULL,
                view_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_share_token (share_token)
            )
        """),
    ]

    for tname, sql in v6_tables:
        try:
            cv6.execute(sql)
            conn_v6.commit()
            print(f"   ✅ {tname}")
        except Exception as e:
            if '1050' in str(e) or 'already exists' in str(e).lower():
                print(f"   ✓  {tname} (sudah ada)")
            else:
                print(f"   ⚠️  {tname}: {e}")

    cv6.close()
    conn_v6.close()
    print("\n✅ Sprint v6 migration selesai!")
    print("   7 tabel baru: boards, board_columns, board_members,")
    print("   board_cards, card_subtasks, card_comments, share_reports")

except Exception as e:
    print(f"❌ Sprint v6 error: {e}")
    import traceback; traceback.print_exc()


# ══════════════════════════════════════════════════════
# MIGRATION: Sprint v7 — ESQ + Weekly Review + Onboarding + Level
# ══════════════════════════════════════════════════════
print("\n── Sprint v7: ESQ + Weekly Review + Onboarding ──")

try:
    conn_v7 = dbmod.get_connection()
    if not conn_v7:
        raise Exception("DB tidak tersedia")
    cv7 = conn_v7.cursor(dictionary=True)

    v7_tables = [
        ("esq_values", """
            CREATE TABLE IF NOT EXISTS esq_values (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                category VARCHAR(30) DEFAULT 'custom',
                emoji VARCHAR(10) DEFAULT '⭐',
                color VARCHAR(7) DEFAULT '#6366f1',
                priority TINYINT DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("esq_reflections", """
            CREATE TABLE IF NOT EXISTS esq_reflections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                type VARCHAR(20) DEFAULT 'daily',
                reflection_date DATE NOT NULL,
                content TEXT NOT NULL,
                mood_score TINYINT DEFAULT 3,
                energy TINYINT DEFAULT 3,
                gratitude TEXT, lessons TEXT, tomorrow_intent TEXT,
                isq_score TINYINT DEFAULT NULL,
                is_private BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_refl (user_id, type, reflection_date),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("esq_spiritual_log", """
            CREATE TABLE IF NOT EXISTS esq_spiritual_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                log_date DATE NOT NULL,
                activity VARCHAR(50) NOT NULL,
                label VARCHAR(100) DEFAULT NULL,
                is_done BOOLEAN DEFAULT FALSE,
                done_at TIMESTAMP NULL,
                quantity DECIMAL(6,2) DEFAULT NULL,
                unit VARCHAR(20) DEFAULT NULL,
                notes VARCHAR(255) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_spiritual (user_id, log_date, activity),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_spiritual_date (user_id, log_date)
            )
        """),
        ("weekly_review_generated", """
            CREATE TABLE IF NOT EXISTS weekly_review_generated (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                week_start DATE NOT NULL, week_end DATE NOT NULL,
                tasks_done INT DEFAULT 0, tasks_total INT DEFAULT 0,
                reminders_pct DECIMAL(5,2) DEFAULT 0,
                avg_mood DECIMAL(4,2) DEFAULT NULL,
                top_streaks JSON, goal_progress JSON,
                xp_earned INT DEFAULT 0,
                spiritual_score TINYINT DEFAULT 0,
                saving_amount DECIMAL(20,2) DEFAULT 0,
                highlight VARCHAR(255),
                ai_summary TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                share_token VARCHAR(32) NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_week_review (user_id, week_start),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("user_profile_setup", """
            CREATE TABLE IF NOT EXISTS user_profile_setup (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                profile_type VARCHAR(30) DEFAULT 'lainnya',
                profile_emoji VARCHAR(10) DEFAULT '👤',
                focus_areas JSON,
                work_hours_start TIME DEFAULT '08:00:00',
                work_hours_end TIME DEFAULT '17:00:00',
                sleep_time TIME DEFAULT '22:00:00',
                wake_time TIME DEFAULT '05:00:00',
                religion VARCHAR(20) DEFAULT NULL,
                timezone VARCHAR(50) DEFAULT 'Asia/Jakarta',
                setup_complete BOOLEAN DEFAULT FALSE,
                setup_step TINYINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """),
        ("level_rewards", """
            CREATE TABLE IF NOT EXISTS level_rewards (
                id INT AUTO_INCREMENT PRIMARY KEY,
                level TINYINT NOT NULL,
                reward_type VARCHAR(20) NOT NULL,
                reward_key VARCHAR(50) NOT NULL,
                reward_name VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                UNIQUE KEY uniq_reward (level, reward_key)
            )
        """),
    ]

    for tname, sql in v7_tables:
        try:
            cv7.execute(sql)
            conn_v7.commit()
            print(f"   ✅ {tname}")
        except Exception as e:
            if '1050' in str(e) or 'already exists' in str(e).lower():
                print(f"   ✓  {tname} (sudah ada)")
            else:
                print(f"   ⚠️  {tname}: {e}")

    cv7.close()
    conn_v7.close()
    print("\n✅ Sprint v7 migration selesai!")

except Exception as e:
    print(f"❌ Sprint v7 error: {e}")
    import traceback; traceback.print_exc()
