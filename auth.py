from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
import json
import os

auth = Blueprint("auth", __name__)
bcrypt = Bcrypt()

USER_FILE = "users.json"

# 🔐 Load users
def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as f:
        return json.load(f)

# 💾 Save users
def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)


# -------------------------
# SIGN UP
# -------------------------
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()
        password = request.form.get("password")

        users = load_users()

        if username in users:
            return "❌ User already exists"

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        users[username] = {
            "password": hashed_pw
        }

        save_users(users)
        return redirect("/login")

    return render_template("signup.html")


# -------------------------
# LOGIN
# -------------------------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()
        password = request.form.get("password")

        users = load_users()

        if username not in users:
            return "❌ User not found"

        if bcrypt.check_password_hash(users[username]["password"], password):
            session["user"] = username
            return redirect("/")
        else:
            return "❌ Wrong password"

    return render_template("login.html")


# -------------------------
# LOGOUT
# -------------------------
@auth.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")