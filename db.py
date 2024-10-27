import json
import os
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

def get_roles():
    return _db["roles"]

def get_users_by_groups_OR(groups: list):
    matching_users = []
    # Iterate through each user and their details
    for user, details in _db['users'].items():
        # Check if any of the user's battalion, company, or platoon match the given criteria
        for _, detail in details.items():
            try:
                if detail in groups:
                    matching_users.append((user, details))
                    break
            except TypeError:
                pass

    return matching_users

def _to_set(input: list) -> set:
    output = set()
    for value in input:
        if type(value) == list or type(value) == dict or type(value) == set:
            continue
        output.add(value)
    
    return output

def get_users_by_groups_AND(properties: list):
    matching_users = []
    print("PROPERTIES:")
    print(set(properties))
    for user in _db['users'].keys():
        print("TEST")
        print(_to_set(_db['users'][user].values()))
        if _to_set(_db['users'][user].values()) & set(properties) == set(properties):
            matching_users.append((user, _db['users'][user]))
    return matching_users

def get_users_by_fields(properties: dict):
    matching_users = []
    for user in _db['users'].keys():
        flag = True
        for key, val in properties.items():
            if not (key in _db['users'][user].keys() and _db['users'][user][key] == val):
                flag = False
                break
        if flag:
            matching_users.append(_db['users'][user])

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

def update_users_db(data: dict):
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
            if not (name in _db["users"].keys()):
                _db["users"][name] = {}
            _db["users"][name][key] = val

    write_to_file(DB_PATH)

def load_db_from_excel(filename: str):
    # Load the Excel file into a pandas DataFrame
    df = pd.read_excel(filename)
    groups = {}
    all_roles = set()
    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        name = row['name']
        battalion = row['battalion']
        company = row['company']
        team = str(row['team'])
        roles = [] if str(row['roles']) == 'nan' else [role.strip() for role in str(row['roles']).split(",")]
        if roles == ['']:
            roles = []
        # add to db
        all_roles = all_roles | set(roles)
        if battalion not in groups.keys():
            groups[battalion] = dict()
        if company not in groups[battalion].keys():
            groups[battalion][company] = []
        if team not in groups[battalion][company]:
            groups[battalion][company].append(team)
        # Add user to the database
        _db['users'][name] = {
            "name": name,
            "battalion": battalion,
            "company": company,
            "team": team,
            "points": 0,  # Default points can be set to 0
            "roles": roles
        }
    _db["roles"] = list(set(_db["roles"]) | all_roles)
    for battalion in groups:
        if battalion not in _db["groups"].keys():
            _db["groups"][battalion] = dict()
        for company in groups[battalion]:
            if company not in _db["groups"][battalion].keys():
                _db["groups"][battalion][company] = []
            for team in groups[battalion][company]:
                if team not in _db["groups"][battalion][company]:
                    _db["groups"][battalion][company].append(team)
    os.remove(filename)
    write_to_file(DB_PATH)

def main():
    load_db_from_excel("temp_excel_files\\Harel_data.xlsx")
    

if __name__ == "__main__":
    main()