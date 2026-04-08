from db import get_connection, hash_password
from datetime import datetime


def force_reset_admin():
    conn = get_connection()
    if not conn:
        print("❌ Gagal terhubung ke database. Pastikan XAMPP (MySQL) menyala di port 3307.")
        return

    try:
        cursor = conn.cursor()

        # 1. Buat Hash Password Baru (admin123)
        new_password_hash = hash_password("admin123")

        # 2. Update Password dan Bersihkan Status Lockout/Failed Attempts
        query = """
            UPDATE users 
            SET password = %s, 
                failed_attempts = 0, 
                locked_until = NULL,
                onboarded = 1
            WHERE username = 'admin' OR email = 'admin@example.com'
        """

        cursor.execute(query, (new_password_hash,))
        conn.commit()

        if cursor.rowcount > 0:
            print("✅ Berhasil! Akun Admin telah direset.")
            print("--- Detail Login Baru ---")
            print("Username: admin")
            print("Password: admin123")
            print("-------------------------")
        else:
            print("⚠️ Akun admin tidak ditemukan di database.")

    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    force_reset_admin()