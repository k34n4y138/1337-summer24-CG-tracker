import sqlite3, requests, time, json



INTRA_UID = 'u-s4t2ud-f2f56b1301f6140a758d6622f62730d3deb221be1fa9a374bb5281e842f0e7d5'
INTRA_SECRET = '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'

COMPETITION_START_DATE = "2021-06-11T00:00:00Z"
COMPETITION_END_DATE = "2021-06-24T23:59:59Z"

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
    "rank_history": [
    {
    "date": "2021-01-01T00:00:00Z",
    "school_rank": 1,
    "global_rank": 1,
    "league": "legend"
    "logtime": 15,
    "submissions": 5
    },{
     {
    "date": "2021-01-02",
    "school_rank": 5, // highest rank of that day
    "global_rank": 1, // highest rank of that day
    "league": "legend" / highest league of that day
    "logtime": 27 // count of how many instances with online since
    "submissions": 5 // count of distinct submission ids of that day
    }
    },{...}
    ],
}
"""

def get_player_logtime(cg_id):
    # count the number of instances with online since per day
    # date field is created_at and is datetime, group by date
    cursor = conn.execute('SELECT strftime("%Y-%m-%d", created_at) as date, count(*) as logtime FROM rankscrap WHERE codingamer_id = ? AND online_since NOT NULL GROUP BY date', (cg_id,))
    return {row[0]: row[1] for row in cursor}


def get_player_submissions(cg_id):
    """
    get the number of distinct submission per day, group by date
    submission_id is not unique, and might appear in multiple days
    assign it to the first date it appears in
    """
    query = '''
        SELECT date, count(submission_time) as submissions 
        FROM (
            SELECT submission_time, min(strftime("%Y-%m-%d", created_at)) as date 
            FROM rankscrap 
            WHERE codingamer_id = ? 
            GROUP BY submission_time
        ) 
        GROUP BY date
    '''
    cursor = conn.execute(query, (cg_id,))
    return {row[0]: row[1] for row in cursor}


def get_player_rank_advancement(cg_id):
    """
    get the highest rank of a player since first occurrence
    """
    query = '''
        SELECT strftime("%Y-%m-%d", created_at) as date, min(global_rank) as global_rank, min(school_rank) as school_rank, max(league_id) as league_id
        FROM rankscrap
        WHERE codingamer_id = ?
        GROUP BY date
    '''
    cursor = conn.execute(query, (cg_id,))
    return {row[0]: {'global_rank': row[1], 'school_rank': row[2], 'league_id': row[3]} for row in cursor}


def get_player_history(cg_id):
    """
    merge the logtime, submissions, ranks and leagues of a player
    """
    logtime = get_player_logtime(cg_id)
    submissions = get_player_submissions(cg_id)
    rank_advancement = get_player_rank_advancement(cg_id)
    history = []
    for date in sorted(set(logtime.keys()) | set(submissions.keys()) | set(rank_advancement.keys())):
        history.append({
            'date': date,
            'logtime': logtime.get(date, 0) * 15, # 15 minutes per logtime
            'submissions': submissions.get(date, 0),
            **rank_advancement.get(date, {'global_rank': -1, 'league_id': 0})
        })
        history[-1]['league'] = leagues[history[-1]['league_id']]
    return history

leagues = ['wood_2', 'wood_1', 'bronze', 'silver', 'gold', 'legend']


def get_player_league_inception(cg_id):
    """
    for each league, extract the date the player entered it
    """
    query = '''
        SELECT min(strftime("%Y-%m-%d", created_at)) as date, league_id
        FROM rankscrap
        WHERE codingamer_id = ?
        GROUP BY league_id
    '''
    cursor = conn.execute(query, (cg_id,))
    return {leagues[row[1]]: row[0] for row in cursor}

targets = conn.execute('SELECT id, intra_login, intra_avatar, cg_username, cg_avatar, intra_campus, cg_uuid FROM codingamer WHERE intra_login IS NOT NULL and staff_ban = 0').fetchall()

export = []


for player in targets:
    cg_url = f'https://www.codingame.com/profile/{player[6]}'
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
        'league': league,
        'rank_history': get_player_history(player[0]),
        'league_inception': get_player_league_inception(player[0])
    })


with open('data.json', 'w') as f:
    # sort by global rank
    export.sort(key=lambda x: x['global_rank'])
    for i, player in enumerate(export):
        player['school_rank'] = i + 1
    json.dump(export, f, indent=4)
