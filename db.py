import json

DB_PATH = "./db.json"

def load_json_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

_db = load_json_from_file(DB_PATH)

def get_groups():
    return _db["groups"]

def get_users_by_groups(groups: dict):
    matching_users = []
    # Iterate through each user and their details
    for user, details in _db['users'].items():
        # Check if any of the user's battalion, company, or platoon match the given criteria
        for _, detail in details.items():
            if detail in groups:
                matching_users.append((user, details))
                break

    return matching_users


def main():
    users = get_users_by_groups(["22"])
    print(f"{users=}")

if __name__ == "__main__":
    main()