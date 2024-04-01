import textwrap
import json
import xml.etree.ElementTree as et
import yaml

root = et.parse("workflowy_game_reviews.opml")


def get_text(e):
    return e.attrib.get("text")


with open("steam_matches.json") as steam_db:
    data = json.load(steam_db)

reviews = []
body = root.find("body")
for e in body:
    if e.tag == "outline":
        review = {}
        workflowy_title = get_text(e)
        game = data[workflowy_title]
        review["content"] = get_text(e[0])
        review["appid"] = game[0]
        review["title"] = game[1]
        review["store"] = "steam"
        reviews.append(review)

"""
indent = " " * 8
for i, (title, body) in enumerate(reviews):
    game = data[title]
    appid = game[0]
    title = game[1]
    print(f"- title: {title}")
    print(f"  appid: {appid}")
    print(f"  body: |")
    print(textwrap.fill(body, initial_indent=indent, subsequent_indent=indent))
    print("")
"""
with open("reviews.yaml", "w") as fp:
    yaml.dump(reviews, fp)
