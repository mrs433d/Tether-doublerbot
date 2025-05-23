# db.py
user_data = {}

def get_balance(user_id):
    return user_data.get(user_id, {}).get("balance", 0.0)

def add_balance(user_id, amount):
    user_data.setdefault(user_id, {})["balance"] = get_balance(user_id) + amount

def get_user_state(user_id):
    return user_data.get(user_id, {}).get("state", None)

def set_user_state(user_id, state):
    user_data.setdefault(user_id, {})["state"] = state
