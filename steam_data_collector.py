import json
import time
from pathlib import Path

import requests


def get_request(url, parameters=None):

    response = requests.get(url=url, params=parameters)

    if response:
        return response.json()
    else:
        return None


def parse_steam_request(appid, name):
    url = "http://store.steampowered.com/api/appdetails/"
    parameters = {"appids": appid}

    json_data = get_request(url, parameters=parameters)
    if json_data is None:
        print(f"Request failed, {name}: {appid}")
        return None

    json_app_data = json_data[str(appid)]

    if json_app_data["success"]:
        data = json_app_data["data"]
    else:
        data = {"name": name, "steam_appid": appid}

    return data


def main():
    with open("steam_matches.json") as fp:
        app_list = json.load(fp)

    steam_data = Path("steam_data")
    steam_data.mkdir(exist_ok=True)

    for app in app_list.values():
        appid, app_name = app

        game_path = (steam_data / str(appid)).with_suffix(".json")
        if game_path.exists():
            continue

        game_data = parse_steam_request(appid, app_name)
        if game_data is None:
            continue

        with open(game_path, "w") as fp:
            json.dump(game_data, fp, indent=4)

        time.sleep(1)


if __name__ == "__main__":
    main()
