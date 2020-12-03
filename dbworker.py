from vedis import Vedis
from enum import Enum

class States(Enum):
    S_START = "0"
    S_ENTER_CCY = "1"
    S_ENTER_BEGIN_DAY = "2"

db_file = 'database.vdb'

def get_current_state(user_id):
    with Vedis(db_file) as db:
        try:
            return db[user_id].decode()
        except KeyError:
            return States.S_START.value


def del_state(field):
    with Vedis(db_file) as db:
        try:
            del(db[field])
            return True
        except:
            return False


def set_state(user_id, value):
    with Vedis(db_file) as db:
        try:
            db[user_id] = value
            return True
        except:
            return False
