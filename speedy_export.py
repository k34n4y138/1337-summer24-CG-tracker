import json, requests
import math

def export_speedy_data(data):
    with open('speedy_data.json', 'w') as f:
        json.dump(data, f)


def export_spedy_data_excel(data):
    URL = "https://api.products.aspose.app/cells/conversion/api/ConversionApi/Convert?outputType=XLSX"
    files = {
        "156124648": ("convert.json", json.dumps(data))
    }

    data = {
        "MultipleWorksheets": "true",
        "filePwd": "",
        "UploadOptions": "JSON"
    }
    cookie = {
        "user_info": "bmFtZT16bW91bWVuMTMzN0BnbWFpbC5jb20mZW1haWw9em1vdW1lbjEzMzdAZ21haWwuY29t"
    }

    response = requests.post(URL, files=files, data=data, cookies=cookie)
    rdata = response.json()
    if rdata['FileName'] == 'None':
        raise Exception("Error while exporting data to excel")
    download_link = f"https://api.products.aspose.app/cells/conversion/api/Download/{rdata['FolderName']}?file={rdata['FileName']}"
    download = requests.get(download_link)
    with open('speedy_data.xlsx', 'wb') as f:
        f.write(download.content)


def speedy_player_treatment(player):
    return {
        "School rank": player['school_rank'],
        "Global rank": player['global_rank'],
        "Login": player['intra_login'],
        "Campus": player['intra_campus'],
        "CG username": player['cg_username'],
        "Total logtime":math.ceil(sum([rank['logtime'] for rank in player['rank_history']]) / 60), # 
        "Total  submissions":sum([rank['submissions'] for rank in player['rank_history']]),
        "Leage inceptions":{
            "wood 2": player['league_inception'].get('wood_2', ""),
            "Wood 1": player['league_inception'].get('wood_1', ""),
            "Bronze": player['league_inception'].get('bronze', ""),
            "Silver": player['league_inception'].get('silver', ""),
            "Gold": player['league_inception'].get('gold', ""),
            "Legend": player['league_inception'].get('legend', ""),
        }
    }



with open('data.json', 'r') as f:
    data = json.load(f)
    speedy_data = [speedy_player_treatment(player) for player in data]
    export_spedy_data_excel(speedy_data)
    print("speedy data exported to excel successfully")
