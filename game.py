from flask import Blueprint, flash, redirect, render_template, request, session, url_for
import json
import random
import requests
from sqlalchemy import desc, select
from sqlalchemy.orm import joinedload
from database import db
from models import History, User

try:
    # get json from request
    api_url = "https://restcountries.com/v3.1/all?fields=name,flags,region,subregion,independent"
    response = requests.get(api_url)
    
    response.raise_for_status()  # raise error if http error
    
    all_flags = response.json()

    with open("restcountries.json", "w") as json_file:
        json.dump(all_flags, json_file)
except:
    # load backup json
    with open("restcountries.json") as json_file:
        all_flags = json.load(json_file)

# get all independent countries        
flags = [country for country in all_flags if country.get("independent")]

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
        flag_ids_queue = list(range(len(flags)))
    elif region_key == "north-central-america":
        flag_ids_queue = [
            idx for idx, flag in enumerate(flags)
            if flag.get("subregion") in
            ["North America", "Central America", "Caribbean"]
        ]
    else:
        flag_ids_queue = [
            idx for idx, flag in enumerate(flags)
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

    correct_flag = flags[flag_ids_queue[current_id]]

    correct_flag_name = correct_flag["name"]["common"]
    correct_flag_url = correct_flag["flags"]["svg"]
    session["correct_flag_name"] = correct_flag_name
    session["correct_flag_url"] = correct_flag_url

    current_region = session.get("current_region", "World")
    
    game_mode = session.get("game_mode", "4-alternatives")
    pretty_mode = session.get("pretty_mode", "4 Alternatives")
    
    
    if game_mode == "write-in":
        candidates = [
            country["name"]["common"] for country in flags
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
            flag = flags[random.choice(flag_ids_queue)]

            if flag != correct_flag and flag not in choices:
                choices.append(flag)
            
        choices.append(correct_flag)
        random.shuffle(choices)
    
        return render_template("play.html",
                               game_mode=game_mode,
                               pretty_mode=pretty_mode,
                               region=current_region,                                                       img_url=correct_flag_url,
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
