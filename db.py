import json
import pandas as pd

DB_PATH = "./db.json"

def load_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

_db = load_from_file(DB_PATH)

def write_to_file(file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(_db, file, ensure_ascii=False)
    
def get_groups():
    return _db["groups"]

def get_users_by_groups(groups: list):
    matching_users = []
    # Iterate through each user and their details
    for user, details in _db['users'].items():
        # Check if any of the user's battalion, company, or platoon match the given criteria
        for _, detail in details.items():
            if detail in groups:
                matching_users.append((user, details))
                break

    return matching_users

def get_users_by_fields(properties: dict):
    matching_users = []
    # Iterate through each user and their details
    for key, val in properties.items():
        # Check if any of the user's battalion, company, or platoon match the given criteria
        for user in _db['users'].keys():
            if key in _db['users'][user].keys() and _db['users'][user][key] == val:
                matching_users.append(_db['users'][user])
                break

    return matching_users

def get_user_by_chat_id(chat_id: int) -> tuple:
    for username, details in _db['users'].items():
        if details.get('chat_id') == chat_id:
            return (username, details)
    return None

def get_user_by_uid(uid: str) -> tuple:
    if uid in _db['users'].keys():
        return (uid, _db['users'][uid])
    return None

def update_db(data: dict):
    """
        Write to DB with @data in the following format:
        {"user_id": {
            "property": new_val
            }
        }
    """
    for name, vals in data.items():
        for key, val in vals.items():
            print(f"{name=}, {key=}, {val=}")
            _db["users"][name][key] = val

    write_to_file(DB_PATH)

def load_db_from_excel(filename: str):
    pass
    
def main():
    users = get_users_by_groups(["22"])
    print(f"{users=}")

if __name__ == "__main__":
    main()