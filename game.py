from dotenv import load_dotenv
import os
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
import json
import random
import requests
from sqlalchemy import desc, select
from sqlalchemy.orm import joinedload
from database import db
from models import History, User

load_dotenv()

# set api endpoint
url = "https://api.restcountries.com/countries/v5"
fields = "names.common,flag.url_svg,region,subregion,classification.dependency,classification.sovereign,classification.un_observer,memberships.un"

api_key = os.getenv("REST_COUNTRIES_API_KEY")

limit = 100
offset = 0

all_countries = []

# loop to get all countries when server start, free plan limits to 100 countries per request
try:
    while True:
        response = requests.get(
            f"{url}?limit={limit}&offset={offset}&response_fields={fields}",
            headers={'Authorization': f'Bearer {api_key}'}
        )
        response.raise_for_status()

        data = response.json()["data"]

        all_countries.extend(data["objects"])

        print(data["meta"])
        if not data["meta"]["more"]:
            break

        offset += limit

    with open("restcountries.json", "w") as json_file:
        json.dump(all_countries, json_file)
except Exception as e:
    print(f"API request failed ({e}). Loading from restcountries.json fallback...")
    with open("restcountries.json") as json_file:
        all_countries = json.load(json_file)

countries = []
for country in all_countries:
    name = country.get("names", {}).get("common")
    flag_url = country.get("flag", {}).get("url_svg")
    region = country.get("region")
    subregion = country.get("subregion")
    
    is_un_member = country.get("memberships", {}).get("un", False)
    is_un_observer = country.get("classification", {}).get("un_observer", False)
    is_sovereign = country.get("classification", {}).get("sovereign", False)
    is_dependency = country.get("classification", {}).get("dependency", False)

    if (is_un_member or is_un_observer or is_sovereign) and not is_dependency:
        if name and flag_url and region != "Antarctic":
            countries.append({
                "name": name,
                "flag_url": flag_url,
                "region": region,
                "subregion": subregion
            })
    
from pprint import pprint
pprint(all_countries)

REGIONS = {
    "world": {"label": "World", "image": "world-robinson.svg"},
    "africa": {"label": "Africa", "image": "africa.svg"},
    "americas": {"label": "Americas", "image": "americas.svg"},
    "south-america": {"label": "South America", "image": "south-america.svg"},
    "north-central-america": {"label": "North & Central America", "image": "north-america.svg"},
    "asia": {"label": "Asia", "image": "asia.svg"},
    "europe": {"label": "Europe", "image": "europe.svg"},
    "oceania": {"label": "Oceania", "image": "oceania.svg"}
}

game = Blueprint("game", __name__)

def prettify_mode(game_mode):
    return game_mode.replace('-', ' ').title()


@game.route("/")
def index():
    current_region_key = session.get("current_region_key", "world")
    game_mode = session.get("game_mode", "4-alternatives")
    
    return render_template("index.html",
                           regions=REGIONS,
                           current_region=current_region_key,
                           game_mode=game_mode)


# game setup
@game.route("/setup", methods=["POST"])
def setup():
    session.pop("_flashes", None)
    session.pop("next_url", None)
    
    region_key = request.form.get("region", "world")
    game_mode = request.form.get("game-mode", "4-alternatives")
    
    if region_key not in REGIONS:
        region_key = "world"

    if region_key == "world":
        flag_ids_queue = list(range(len(countries)))
    elif region_key == "north-central-america":
        flag_ids_queue = [
            idx for idx, flag in enumerate(countries)
            if flag.get("subregion") in
            ["North America", "Northern America", "Central America", "Caribbean"]
        ]
    else:
        flag_ids_queue = [
            idx for idx, flag in enumerate(countries)
            if flag.get("region") == REGIONS[region_key]["label"]
            or flag.get("subregion") == REGIONS[region_key]["label"]
        ]
    
    session["current_region"] = REGIONS[region_key]["label"]
    session["current_region_key"] = region_key

    session["game_mode"] = game_mode
    session["pretty_mode"] = prettify_mode(game_mode)
    
    random.shuffle(flag_ids_queue)
    
    session["flag_ids_queue"] = flag_ids_queue
    session["current_id"] = 0
    session["score"] = 0
    session["history"] = []
        
    return redirect(url_for("game.play"))


# game    
@game.route("/play")
def play():
    flag_ids_queue = session.get("flag_ids_queue", [])
    if not flag_ids_queue:
        flash("Start a new game first!", "warning")
        return redirect(url_for("game.index"))
    
    current_id = int(session.get("current_id", 0))
    if current_id >= len(flag_ids_queue):
        return redirect(url_for("game.show_results"))

    correct_flag = countries[flag_ids_queue[current_id]]

    correct_flag_name = correct_flag["name"]
    correct_flag_url = correct_flag["flag_url"]
    session["correct_flag_name"] = correct_flag_name
    session["correct_flag_url"] = correct_flag_url

    current_region = session.get("current_region", "World")
    
    game_mode = session.get("game_mode", "4-alternatives")
    pretty_mode = session.get("pretty_mode", "4 Alternatives")
    
    
    if game_mode == "write-in":
        candidates = [
            country["name"] for country in countries
        ]
        
        return render_template("play.html",
                               game_mode=game_mode,
                               pretty_mode=pretty_mode,
                               region=current_region,
                               candidates=candidates,
                               img_url=correct_flag_url,
                               score=session.get("score",0),
                               current_id=session.get("current_id", 0))
    else:
        alts = int(game_mode.split("-")[0])
        if alts not in [2, 4, 6]:
            alts = 4

        choices = []
        while len(choices) < alts - 1:
            flag = countries[random.choice(flag_ids_queue)]

            if flag != correct_flag and flag not in choices:
                choices.append(flag)
            
        choices.append(correct_flag)
        random.shuffle(choices)
    
        return render_template("play.html",
                               game_mode=game_mode,
                               pretty_mode=pretty_mode,
                               region=current_region,
                               img_url=correct_flag_url,
                               choices=choices,
                               score=session.get("score",0),
                               current_id=session.get("current_id", 0))


# check guess
@game.route("/check", methods=["POST"])
def check_guess():
    guess = request.form.get("guess", "")
    correct_flag_name = session.get("correct_flag_name")
    correct_flag_url = session.get("correct_flag_url")

    if not correct_flag_name:
        flash("Start a new game first!", "warning")
        return redirect(url_for("game.index"))

    if guess.lower() == correct_flag_name.lower():
        flash("Correct! 🥳", "success")
        session["score"] += 1
    else:
        flash(f"Wrong! 😥 The previous flag was from {correct_flag_name}", "danger")

    session["history"].append({
        "url": correct_flag_url,
        "name": correct_flag_name,
        "user_guess": guess,
        "is_correct": guess == correct_flag_name
    })
        
    session["current_id"] += 1
    session.modified = True

    return redirect(url_for("game.play"))


# results
@game.route("/results")
def show_results():
    total = session.get("current_id", 0)
    if total == 0:
        flash("You need to start guessing flags first...", "warning")
        return redirect(url_for("game.index"))
        
    flag_ids_queue = session.get("flag_ids_queue", [])

    is_finished = total == len(flag_ids_queue)

    if is_finished and "user_id" not in session:
        session["next_url"] = request.path
    
    history = session.get("history", [])
    score = session.get("score", 0)
    current_region = session.get("current_region", "World")
    pretty_mode = session.get("pretty_mode", "4 Alternatives")
    
    return render_template("results.html",
                           pretty_mode=pretty_mode,
                           history=history,
                           score=score,
                           total=total,
                           current_region=current_region,
                           is_finished=is_finished)


@game.route("/save", methods=["POST"])
def save():
    if "user_id" not in session:
        flash("You must be logged in", "warning")
        return redirect(url_for("game.show_results"))

    total = session.get("current_id", 0)
    flag_ids_queue = session.get("flag_ids_queue", [])

    if not flag_ids_queue or total < len(flag_ids_queue):
        flash("You cannot save an unfinished game!", "danger")
        return redirect(url_for("game.show_results"))
    
    current_region = session.get("current_region", "World")

    pretty_mode = session.get("pretty_mode", "4 Alternatives")

    corrects = session.get("score", 0)

    new_history = History(
        user_id = session["user_id"],
        region=current_region,
        mode=pretty_mode,
        corrects=corrects
    )

    db.session.add(new_history)
    db.session.commit()

    # clear history from session
    session.pop("current_id", None)
    session.pop("flag_ids_queue", None)
    session.pop("score", None)
    session.pop("history", None)
    
    
    flash("Game has been saved!", "success")
    return redirect(url_for("game.history"))


@game.route("/history")
def history():
    if "user_id" not in session:
        flash("You must be logged in.", "warning")
        session["next_url"] = request.path
        return redirect(url_for("auth.login"))
    
    user_history = db.session.execute(
        select(History)
        .where(History.user_id == session["user_id"])
        .order_by(History.played_at.desc())
    ).scalars().all()
    
    return render_template("history.html", user_history=user_history)


@game.route("/leaderboard")
def leaderboard():
    region_key = request.args.get("region", "world")
    if region_key not in REGIONS:
        region_key = "world"
    
    game_modes = [
        "2-alternatives", "4-alternatives", "6-alternatives", "write-in"
    ]

    region = REGIONS[region_key]["label"]

    tops_by_mode = {}
    for mode in game_modes:
        pretty_mode = prettify_mode(mode)
        tops = db.session.execute(
            select(History)
            .options(joinedload(History.user))
            .where(History.region == region)
            .where(History.mode == pretty_mode)
            .order_by(desc(History.corrects), History.played_at)
            .limit(10)
        ).scalars().all()

        tops_by_mode[pretty_mode] = tops

    print(tops_by_mode)
    return render_template("leaderboard.html",
                           regions=REGIONS,
                           game_modes=game_modes,
                           current_region=region_key,
                           tops=tops_by_mode)
