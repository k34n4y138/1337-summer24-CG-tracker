import sqlite3, requests, time, json



INTRA_UID = 'XXXXX'
INTRA_SECRETgit = 'XXXXXX'


"""
this script will patch the database to include new columns for the existing tables
"""

db = sqlite3.connect('data.sqlite')

conn = db.cursor()

# add intra_avatar and cg_avatar to codingamer
if not any('intra_avatar' in column for column in conn.execute('PRAGMA table_info(codingamer)')):
    conn.execute('ALTER TABLE codingamer ADD COLUMN intra_avatar TEXT DEFAULT NULL')
if not any('cg_avatar' in column for column in conn.execute('PRAGMA table_info(codingamer)')):
    conn.execute('ALTER TABLE codingamer ADD COLUMN cg_avatar TEXT DEFAULT NULL')
if not any("staff_ban" in column for column in conn.execute('PRAGMA table_info(codingamer)')):
    conn.execute('ALTER TABLE codingamer ADD COLUMN staff_ban BOOLEAN DEFAULT FALSE') # manual flagging for removal from the leaderboard.



auth_req = requests.post('https://api.intra.42.fr/oauth/token', data={
    'grant_type': 'client_credentials',
    'client_id': INTRA_UID,
    'client_secret': INTRA_SECRET
})
if auth_req.status_code != 200:
    print('Failed to authenticate with intra: ', auth_req.status_code)
    exit(1)

AUTH_TOKEN = "Bearer " + auth_req.json()['access_token']


targets = conn.execute('SELECT id, intra_login FROM codingamer WHERE intra_avatar IS NULL AND intra_login IS NOT NULL').fetchall()


for row in targets:
    intra_login = row[1].lower().strip()
    response = requests.get(f'https://api.intra.42.fr/v2/users/{intra_login}', headers={'Authorization': AUTH_TOKEN})
    if response.status_code == 200:
        data = response.json()
        avatar_url = data['image']['versions']['medium']
        conn.execute('UPDATE codingamer SET intra_avatar = ? WHERE id = ?', (avatar_url, row[0]))
    else:
        print(f'Failed to fetch avatar for {intra_login}: {response.status_code}')
    time.sleep(0.3)

db.commit()

"""
{
    "id": 1,
    "intra_login": "s4t2ud",
    "intra_avatar": "https://cdn.intra.42.fr/users/s4t2ud.jpg",
    "intra_url": "https://profile.intra.42.fr/users/s4t2ud",
    "cg_username": "s4t2ud",
    "cg_avatar": "https://www.codingame.com/servlet/fileservlet?id=2000000000000",
    "cg_url": "https://www.codingame.com/profile/2000000000000",
    "school_rank: 1,
    "global_rank": 1,
    "league": "legend"
}
"""

targets = conn.execute('SELECT id, intra_login, intra_avatar, cg_username, cg_avatar, intra_campus FROM codingamer WHERE intra_login IS NOT NULL and staff_ban = 0').fetchall()

export = []

leagues = ['wood_2', 'wood_1', 'bronze', 'silver', 'gold', 'legend']

for player in targets:
    cg_url = f'https://www.codingame.com/profile/{player[3]}'
    intra_url = f'https://profile.intra.42.fr/users/{player[1]}'
    last_scrap = conn.execute('SELECT id, global_rank, school_rank, league_id FROM rankscrap WHERE codingamer_id = ? ORDER BY id DESC LIMIT 1', (player[0],)).fetchone()
    if not last_scrap:
        continue # skip players who have never been ranked
    league = leagues[last_scrap[3]]
    export.append({
        'id': player[0],
        'intra_login': player[1],
        'intra_avatar': player[2] if player[2] else 'https://static.codingame.com/servlet/fileservlet?id=124500926983867',
        'intra_campus': player[5],
        'intra_url': intra_url,
        'cg_username': player[3],
        'cg_avatar': player[4],
        'cg_url': cg_url,
        'school_rank': last_scrap[2],
        'global_rank': last_scrap[1],
        'league': league
    })


with open('data.json', 'w') as f:
    # sort by global rank
    export.sort(key=lambda x: x['global_rank'])
    for i, player in enumerate(export):
        player['school_rank'] = i + 1
    json.dump(export, f, indent=4)
