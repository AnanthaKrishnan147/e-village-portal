import sqlite3

def delete_all_data():
    conn = sqlite3.connect('village_office.db')
    cursor = conn.cursor()
    # This deletes all rows but keeps the table structure
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    print("Database cleared successfully.")

if __name__ == "__main__":
    delete_all_data()