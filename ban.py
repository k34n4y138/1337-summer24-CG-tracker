import sqlite3, sys
#takes one argument, the intra_login of the user to ban

DB = "data.sqlite"
CONN = sqlite3.connect(DB)

def ban(intra_login):
    c = CONN.cursor()
    c.execute("SELECT * FROM codingamer WHERE intra_login = ?", (intra_login,))
    user = c.fetchone()
    if user == None:
        print("User not found")
        return
    c.execute("UPDATE codingamer SET staff_ban = 1 WHERE intra_login = ?", (intra_login,))
    CONN.commit()
    print(f"{intra_login} has been banned")
    CONN.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ban.py intra_login")
    else:
        ban(sys.argv[1])
