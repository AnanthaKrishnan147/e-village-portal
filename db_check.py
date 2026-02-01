import sqlite3

def check_users():
    try:
        # Connect to your project database
        conn = sqlite3.connect('village_office.db')
        cursor = conn.cursor()
        
        # Select the key fields to verify security
        cursor.execute("SELECT id, role, full_name, email, password_hash FROM users")
        rows = cursor.fetchall()
        
        print("\n" + "="*100)
        print(f"{'ID':<3} | {'ROLE':<10} | {'NAME':<20} | {'EMAIL':<25} | {'PASSWORD HASH (SCRYPT)'}")
        print("-" * 100)
        
        for row in rows:
            # We only show the first 30 chars of the hash to keep the table clean
            print(f"{row[0]:<3} | {row[1]:<10} | {row[2]:<20} | {row[3]:<25} | {row[4][:40]}...")
            
        print("="*100 + "\n")
        
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    check_users()