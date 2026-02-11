import bcrypt
import sys

def generate_hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        print("No password provided, using default 'admin' for demonstration.")
        password = "admin"
        
    print(f"\nGeneratig hash for password: '{password}'")
    hashed = generate_hash(password)
    print(f"----------------------------------------------------------------")
    print(f"AUTH_PASSWORD_HASH={hashed}")
    print(f"----------------------------------------------------------------\n")
