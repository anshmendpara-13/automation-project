from flask import Flask, render_template, request, send_file, session, redirect, url_for
import os
from datetime import datetime

from auth import auth
from processor import (
    train_from_excel,
    extract_from_pdf,
    match_and_group,
    generate_pdf
)

app = Flask(__name__)

# 🔐 SECRET KEY
app.secret_key = "supersecretkey123"

# 🔗 REGISTER AUTH ROUTES
app.register_blueprint(auth)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
ACCOUNTS_FOLDER = "accounts"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(ACCOUNTS_FOLDER, exist_ok=True)


# -------------------------
# 🔥 GET USER ACCOUNTS
# -------------------------
def get_accounts(username):
    user_path = os.path.join(ACCOUNTS_FOLDER, username)

    if not os.path.exists(user_path):
        return []

    return [
        name for name in os.listdir(user_path)
        if os.path.isdir(os.path.join(user_path, name))
    ]


# -------------------------
# 🔐 MAIN ROUTE (PROTECTED)
# -------------------------
@app.route("/", methods=["GET", "POST"])
def index():

    # 🔒 LOGIN REQUIRED
    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    # 📁 Ensure user folder exists
    user_path = os.path.join(ACCOUNTS_FOLDER, username)
    os.makedirs(user_path, exist_ok=True)

    accounts = get_accounts(username)

    if request.method == "POST":

        # ✅ ACCOUNT HANDLING
        selected_account = request.form.get("account_select") or ""
        new_account = request.form.get("new_account") or ""

        if new_account.strip():
            account_name = new_account.strip().lower()
        elif selected_account.strip():
            account_name = selected_account.strip().lower()
        else:
            return "❌ Please select or create account"

        # 📂 FILES
        manifest_file = request.files.get("manifest")
        train_file = request.files.get("train")

        if not manifest_file or manifest_file.filename == "":
            return "❌ Please upload manifest file"

        # 📁 ACCOUNT FOLDER (USER-WISE)
        account_path = os.path.join(user_path, account_name)
        os.makedirs(account_path, exist_ok=True)

        # 📄 SAVE MANIFEST
        manifest_path = os.path.join(UPLOAD_FOLDER, manifest_file.filename)
        manifest_file.save(manifest_path)

        # 📊 TRAIN FILE PATH
        train_path = os.path.join(account_path, "train.xlsx")

        # 👉 SAVE TRAIN IF UPLOADED
        if train_file and train_file.filename != "":
            train_file.save(train_path)

        # ❌ TRAIN NOT FOUND
        if not os.path.exists(train_path):
            return "❌ No training file found for this account. Please upload one."

        # =========================
        # ⚙️ PROCESS
        # =========================
        mapping = train_from_excel(train_path)

        manifest_data = extract_from_pdf(manifest_path)
        result = match_and_group(mapping, manifest_data)

        # =========================
        # 📄 GENERATE PDF
        # =========================
        today = datetime.now().strftime("%d-%m-%Y")
        output_pdf = os.path.join(
            OUTPUT_FOLDER,
            f"{today} - {username} - {account_name}.pdf"
        )

        generate_pdf(result, output_pdf)

        return send_file(output_pdf, as_attachment=True)

    return render_template("index.html", accounts=accounts, user=username)


# -------------------------
# 🚀 RUN APP
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)