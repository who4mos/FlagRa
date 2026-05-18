from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import select
from database import db
from models import User

auth = Blueprint("auth", __name__)

@auth.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        flash("You're already signed in!", "info")
        return redirect(url_for("game.index"))
    
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            flash("Username is required.", "danger")
            return redirect(url_for("auth.register"))
            
        password = request.form.get("password")
        if not password:
            flash("Password is required.", "danger")
            return redirect(url_for("auth.register"))

        confirmation = request.form.get("confirmation")
        if not confirmation or password != confirmation :
            flash("Password and confirmation must match.", "danger")
            return redirect(url_for("auth.register"))
        
        # check if username already exists
        existing_user = db.session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if existing_user:
            flash("Username already exists 😢", "danger")
            return redirect(url_for("auth.register"))

        # hash password
        hashed_password = generate_password_hash(password)

        # insert user in database
        new_user = User(
            username=username,
            password_hash=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()

        # logs user in
        flash(f"Welcome {username}!", "success")
        session["user_id"] = new_user.id
        session["user_username"] = new_user.username
        
        next_url = session.pop("next_url", None)
        if next_url:
            return redirect(next_url)
        
        return redirect(url_for("game.index"))
    else:
        return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        flash("You're already signed in!", "info")
        return redirect(url_for("game.index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # check if username and password were filled in
        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.login"))

        # check if username exists
        user = db.session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        # if user not exists or password is wrong
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password.", "danger")
            return(redirect(url_for("auth.login")))

        # else, login
        session["user_id"] = user.id
        session["user_username"] = user.username
        flash(f"Welcome back {user.username}", "success")

        next_url = session.pop("next_url", None)
        if next_url:
            return redirect(next_url)
        
        return redirect(url_for("game.index"))
        
    else:
        return render_template("login.html")


@auth.route("/logout", methods=["GET", "POST"])
def logout():
    if "user_id" in session:
        session.pop("user_id", None)
        session.pop("user_username", None)
        flash("You have been logged out.", "info")
    
    return redirect(url_for("game.index"))
