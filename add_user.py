import mysql.connector
from werkzeug.security import generate_password_hash
from config import Config
from database import get_db_connection

def add_user():
    print("--- Create a New Bakery User ---")
    username = input("Enter new username: ")
    password = input("Enter new password: ")
    role = input("Enter role (Admin/Staff) [Default: Staff]: ")
    
    if not role:
        role = "Staff"
    elif role.capitalize() not in ['Admin', 'Staff']:
        print("Invalid role. Setting to 'Staff'.")
        role = "Staff"
    else:
        role = role.capitalize()
    
    # We must scramble (hash) the password before saving it to the database!
    hashed_password = generate_password_hash(password)
    
    conn = get_db_connection()
    if not conn:
        print("Database connection failed. Please check your MySQL server and config.py.")
        return
        
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, hashed_password, role)
        )
        conn.commit()
        print(f"\nSuccess! User '{username}' has been securely added to the database.")
        print("You can now use this account to log into the web app.")
    except mysql.connector.IntegrityError:
        print(f"\nError: The username '{username}' already exists in the database!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    add_user()
