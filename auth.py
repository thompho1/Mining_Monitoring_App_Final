import bcrypt 
import getpass 
import json 
import os 
import sys 
import time 
from dataclasses import dataclass 
 
@dataclass # decorator
class User: 
    user_number: int 
    password_hash: bytes 
    role: str 

def _hash(password: str) -> bytes: 

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()) 
 
def build_default_users() -> dict: 
    
    raw_users = { 
        1: ("Rabi121#", "Administrator"), 
        2: ("Rabi122#", "Safety Officer"), 
        3: ("Rabi123#", "Mining Engineer"), 
        4: ("Rabi124#", "Maintenance Engineer"), 
        5: ("Rabi125#", "Manager"), 
    } 
    return { 
        num: User(user_number=num, password_hash=_hash(pw), role=role) 
        for num, (pw, role) in raw_users.items() 
    } 
 
def load_users_from_file(path: str) -> dict: 
     # users.json -> open() -> f
    with open(path, "r", encoding="utf-8") as f: 
        raw = json.load(f) 
    return { 
        int(num): User( 
            user_number=int(num), 
            password_hash=data["password_hash"].encode("utf-8"), 
            role=data["role"], 
        ) 
        for num, data in raw.items() 
    } 
# Maximum number of failed login attempts
MAX_ATTEMPTS = 3 
LOCKOUT_SECONDS = 30 
 
def authenticate(users: dict, user_number: int, password: str) -> str | None: 
     
    user = users.get(user_number) 
    if user is None: 
         
        bcrypt.checkpw(b"dummy", bcrypt.gensalt()) 
        return None 
 
    if bcrypt.checkpw(password.encode("utf-8"), user.password_hash): 
        return user.role 
    return None 
 
 
def login(users: dict) -> tuple[int, str] | None: 
    attempts = 0 
 
    while attempts < MAX_ATTEMPTS: 
        # try_catch, exception
        try: 
            user_number = int(input("Enter your user number: ")) 
        except ValueError: 
            print("User number must be an integer.") #  
            attempts += 1 # attempts = attempts + 1, 
            continue 
 
        password = getpass.getpass("Enter your password: ")  # hides input 
 
        role = authenticate(users, user_number, password) 
        if role is not None: 
            print("Login successful") 
            print("Role:", role) 
            return user_number, role 
 
        attempts += 1 
        remaining = MAX_ATTEMPTS - attempts 
        if remaining > 0: 
            print(f"Access denied. {remaining} attempt(s) remaining.") 
        else: 
            print(f"Too many failed attempts. Locked out for {LOCKOUT_SECONDS} seconds.") 
            time.sleep(LOCKOUT_SECONDS) 
 
    return None 
# contols the overall flow of the program
def main(): 
    
    users_path = os.environ.get("USERS_FILE", "users.json") 
    if os.path.exists(users_path): 
        users = load_users_from_file(users_path) 
    else: 
        users = build_default_users() 
 
    result = login(users) 
    if result is None: 
        print("Access denied") 
        sys.exit(1)   
 
if __name__ == "__main__": 
    main()
