import yaml
import json
import collections
import dataclasses
import re

with open("reviews.yaml") as data:
    reviews = yaml.load(data, Loader=yaml.Loader)

with open("steam.json", errors="ignore") as steam_data:
    steam_list = json.load(steam_data)

keywords = collections.defaultdict(list)


@dataclasses.dataclass
class GameInfo:
    game_id: str
    game_name: str
    game_lower: str
    game_words: set[str]
    is_demo: bool = False


def split_words(name):
    return set(name.lower().strip().split())


game_list = {}
for game in steam_list["applist"]["apps"]:
    game_id = game["appid"]
    game_name = game["name"]
    game_list[game_id] = game_info = GameInfo(
        game_id=game_id,
        game_name=game_name,
        game_lower=game_name.lower(),
        game_words=split_words(game_name),
    )
    ignore_words = {
        "demo",
        "soundtrack",
        "ost",
        "artbook",
        "playtest",
        "beta",
        "dlc",
        "pack",
        "content",
    }
    if game_info.game_words.intersection(ignore_words):
        game_info.is_demo = True

not_matched = {}
matches = {}

for i, item in enumerate(reviews):
    title = item["title"]
    title_pat = re.compile(re.escape(title) + r"\b", re.I)
    title_lower = title.lower()
    potential_games = []
    title_words = split_words(title)

    # if i > 5:
    #     break

    for game_info in game_list.values():
        game_name = ""
        game_id = ""

        #        if (title_lower in game_info.game_lower and
        #                not (title_words - game_info.game_words)):
        if title_pat.match(game_info.game_lower):
            potential_games.append(game_info)
            print(title, game_info.game_name)

    if len(potential_games) > 1:
        for game_info in list(potential_games):
            if game_info.is_demo:
                potential_games.remove(game_info)

    if len(potential_games) == 1:
        game_match = potential_games[0]
        matches[title] = (game_match.game_id, game_match.game_name)
        print(f"App id is: {game_match.game_id} {game_match.game_name}")
    else:
        not_matched[title] = potential_games

    print("-" * 10)

print("not matched:")
for title in not_matched:
    print(title)

with open("steam_matches.json", "w") as fp:
    json.dump(matches, fp, indent=4)

with open("steam_no_match.txt", "w") as fp:
    print("count", len(not_matched), file=fp)
    for title, games in not_matched.items():
        print(title, file=fp)
        for g in games:
            print("  ", g.game_id, g.game_name, file=fp)
