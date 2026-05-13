import json
from dotenv import load_dotenv
import os
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
import random
import redis
import requests

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
            
app = Flask(__name__)

# this get the local secret key if a .env exists with SECRET_KEY
load_dotenv()

# if not on production and local secret don't exist as well load fallback str
app.secret_key = os.environ.get("SECRET_KEY", "42069")

# get production redis-url
redis_url = os.environ.get('REDIS_URL')

# set session to redis or filesystem if running local
if redis_url:
    app.config["SESSION_TYPE"] = "redis"
    app.config['SESSION_REDIS'] = redis.from_url(redis_url)
    app.config['SESSION_KEY_PREFIX'] = "flagra:"
else:
    app.config["SESSION_TYPE"] = "filesystem"

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

Session(app)

# menu
@app.route("/")
def index():
    current_region = session.get("current_region", "World")
    current_num = int(session.get("num_choices", 4))

    return render_template("index.html", current_region=current_region, current_num=current_num)


# game setup
@app.route("/setup", methods=["POST"])
def setup():
    session.pop("_flashes", None)
    
    current_region = request.form.get("region", "World")
    num_choices = int(request.form.get("num_choices", 4))

    session["current_region"] = current_region
    session["num_choices"] = num_choices

    if current_region == "World":
        flag_ids_queue = list(range(len(flags)))
    elif current_region == "North & Central America":
        flag_ids_queue = [
            idx for idx, flag in enumerate(flags)
            if flag.get("subregion") in
            ["North America", "Central America", "Caribbean"]
        ]
    else:
        flag_ids_queue = [
            idx for idx, flag in enumerate(flags)
            if flag.get("region") == current_region
            or flag.get("subregion") == current_region
        ]

    random.shuffle(flag_ids_queue)
    
    session["flag_ids_queue"] = flag_ids_queue
    session["current_id"] = 0
    session["score"] = 0
    session["history"] = []
        
    return redirect(url_for("play"))


# game    
@app.route("/play")
def play():
    flag_ids_queue = session.get("flag_ids_queue", [])
    if not flag_ids_queue:
        flash("Start a new game first!", "warning")
        return redirect(url_for("index"))
    
    current_id = int(session.get("current_id", 0))

    if current_id >= len(flag_ids_queue):
        return redirect(url_for("show_results"))

    correct_flag = flags[flag_ids_queue[current_id]]
    num_choices = int(session.get("num_choices", 4))
    if num_choices not in [2, 4, 6]:
        num_choices = 4

    choices = []
    while len(choices) < num_choices - 1:
        flag = flags[random.choice(flag_ids_queue)]

        if flag != correct_flag and flag not in choices:
            choices.append(flag)
    choices.append(correct_flag)
    random.shuffle(choices)
    
    correct_flag_name = correct_flag["name"]["common"]
    correct_flag_url = correct_flag["flags"]["svg"]

    session["correct_flag_name"] = correct_flag_name
    session["correct_flag_url"] = correct_flag_url
    
    return render_template("play.html", img_url=correct_flag_url, choices=choices, score=session.get("score",0), current_id=session.get("current_id", 0))


# check guess
@app.route("/check", methods=["POST"])
def check_guess():
    guess = request.form.get("guess")
    correct_flag_name = session.get("correct_flag_name")
    correct_flag_url = session.get("correct_flag_url")

    if not correct_flag_name:
        flash("Start a new game first!", "warning")
        return redirect(url_for("index"))
    
    if guess == correct_flag_name:
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

    return redirect(url_for("play"))


# results
@app.route("/results")
def show_results():
    flag_ids_queue = session.get("flag_ids_queue", [])
    history = session.get("history", [])
    score = session.get("score", 0)
    total = session.get("current_id", 0)

    current_region = session.get("current_region", "World")
    current_num = int(session.get("num_choices", 4))
    
    return render_template("results.html",
                           flag_ids_queue=flag_ids_queue,
                           history=history,
                           score=score,
                           total=total,
                           current_region=current_region,
                           current_num=current_num)


if __name__ == "__main__":
    app.run(debug=True)
