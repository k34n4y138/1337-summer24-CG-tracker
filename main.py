import sqlite3,os, requests, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build



DATABASE_NAME = 'data.sqlite'
SCHEMA_FILE = 'manifest_schema.sql'

CG_LINK = "https://www.codingame.com/services/Leaderboards/getFilteredChallengeLeaderboard"
CG_PAYLOAD = ["summer-challenge-2024-olymbits","fdad4e510321da452fcccccc7e268cf40952875","school",{"active":False,"column":"","filter":""}]


PARTICIPATION_SHEET_ID = "1EvNap72tjC70Hj-5Si8x7RkE4WvDm-ZG1xpMHDZ2f7M"
PARTICIPATION_SHEET_RANGE = "Réponses au formulaire 1!A1:G1000"
GSHEET_CRED_FILE = "gsheet_credentials.json"
GSHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


if not os.path.exists(DATABASE_NAME):
    with sqlite3.connect(DATABASE_NAME) as conn:
        with open(SCHEMA_FILE) as f:
            conn.executescript(f.read())
            conn.commit()


DATABASE_CONNECTION = sqlite3.connect(DATABASE_NAME)
DB_CURR = DATABASE_CONNECTION.cursor()


def get_gsheet_data():
    credentials = service_account.Credentials.from_service_account_file(GSHEET_CRED_FILE, scopes=GSHEET_SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets().values().get(spreadsheetId=PARTICIPATION_SHEET_ID, range=PARTICIPATION_SHEET_RANGE).execute()
    values = sheet.get('values', [])
    fields = ['FILL_DATE', 'INTRA_LOGIN', 'CG_USERNAME', 'CG_URL','PARTICIPATED_PREVIOUSLY', 'PARTICIPATION_MOTIVE', 'CAMPUS']
    return list(map(lambda x: dict(zip(fields, x)), values))


def extract_cg_uuid(cg_url):
    _ = cg_url.split('/')
    while len(_) and len(_[-1]) != 39:
        _.pop()
    return _[-1] if len(_) and len(_[-1]) == 39 else None # submitted link is not a cg profile


def get_create_user(cg_uuid, cg_username, intra_login, campus):
    '''
    check if user exists in the database, if not create a new user
    check order: cg_uuid -> intra_login
    '''
    DB_CURR.execute('SELECT id, intra_login, intra_campus, cg_uuid, cg_username FROM codingamer WHERE cg_uuid = ?', (cg_uuid,))
    user = DB_CURR.fetchone()
    if user:
        return user
    NEW_USER = (intra_login, campus, cg_uuid, cg_username)
    DB_CURR.execute('INSERT INTO codingamer (intra_login, intra_campus, cg_uuid, cg_username) VALUES (?, ?, ?, ?)', NEW_USER)
    DATABASE_CONNECTION.commit()
    DB_CURR.execute('SELECT id, intra_login, intra_campus, cg_uuid, cg_username FROM codingamer WHERE cg_uuid = ?', (cg_uuid,))
    return DB_CURR.fetchone()


def populate_from_gsheet():
    gsheet = get_gsheet_data()
    for row in gsheet:
        cg_uuid = extract_cg_uuid(row['CG_URL'])
        if not cg_uuid:
            with open('invalid_links.txt', 'a') as f: #form filled badly
                f.write("%s\t%s\t%s\n" % (row['INTRA_LOGIN'], row['CG_USERNAME'], row['CG_URL']))
            continue
        user = get_create_user(cg_uuid, row['CG_USERNAME'], row['INTRA_LOGIN'], row['CAMPUS'])
        if not user[1]: # grabbing a user from database without intra_login means user filled participation form later after competition started
            DB_CURR.execute('UPDATE users SET intra_login = ?, intra_campus = ? WHERE id = ?', (row['INTRA_LOGIN'], row['CAMPUS'], user[0]))
            DATABASE_CONNECTION.commit()



def fetch_ranking():
    response = requests.post(CG_LINK, json=CG_PAYLOAD)
    data = response.json()
    rankings = []
    for user in data['users']:
        new = {
            'user' : {
            'cg_uuid': user['codingamer']['publicHandle'],
            'username':user['pseudo'],
            'online_since': user['codingamer'].get('onlineSince', None)
            },
            'ranking': {
            'session_uuid':user['testSessionHandle'],
            'submission_time':user['creationTime'], #submission time
            'stability_percentage': user['percentage'],
            'score': user['score'],
            'language_used':user['programmingLanguage'],
            'league_id':user['league']['divisionIndex'],
            'global_rank':user['globalRank'],
            'school_rank': user['rank'],
            }
        }
        rankings.append(new)
    return rankings


def push_ranking_to_db(scrap_unit, codingamer_id):
    query = '''
    INSERT INTO rankscrap (
        codingamer_id,
        online_since,
        session_uuid,
        submission_time,
        stability_percentage,
        score,
        language_used,
        league_id,
        global_rank,
        school_rank
        )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    DB_CURR.execute(query, (
        codingamer_id,
        scrap_unit['user']['online_since'],
        scrap_unit['ranking']['session_uuid'],
        scrap_unit['ranking']['submission_time'],
        scrap_unit['ranking']['stability_percentage'],
        scrap_unit['ranking']['score'],
        scrap_unit['ranking']['language_used'],
        scrap_unit['ranking']['league_id'],
        scrap_unit['ranking']['global_rank'],
        scrap_unit['ranking']['school_rank']
        ))
    DATABASE_CONNECTION.commit()

def save_rankings(data):
    for user in data: # user not guaranteed to be already in the database
        db_user = get_create_user(user['user']['cg_uuid'], user['user']['username'], None, None)
        push_ranking_to_db(user, db_user[0])


if __name__ == '__main__':
    populate_from_gsheet()
    rankings = fetch_ranking()
    save_rankings(rankings)
    DATABASE_CONNECTION.close()