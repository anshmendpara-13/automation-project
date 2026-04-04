from flask import Flask, render_template, request, send_file, session, redirect
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

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
ACCOUNTS_FOLDER = "accounts"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ACCOUNTS_FOLDER, exist_ok=True)


# -------------------------
# 🔥 CLEAN NAME (SAFE)
# -------------------------
def clean_name(name):
    name = str(name).strip().lower()
    name = re.sub(r'[^a-z0-9]', '_', name)
    return name


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

        # =========================
        # ✅ ACCOUNT HANDLING
        # =========================
        selected_account = request.form.get("account_select") or ""
        new_account = request.form.get("new_account") or ""

        if new_account.strip():
            account_name = clean_name(new_account)
        elif selected_account.strip():
            account_name = clean_name(selected_account)
        else:
            return "❌ Please select or create account"

        # =========================
        # 📂 FILES
        # =========================
        manifest_file = request.files.get("manifest")
        train_file = request.files.get("train")

        if not manifest_file or manifest_file.filename == "":
            return "❌ Please upload manifest file"

        # 📁 ACCOUNT FOLDER
        account_path = os.path.join(user_path, account_name)
        os.makedirs(account_path, exist_ok=True)

        # =========================
        # 📄 SAVE MANIFEST (SAFE NAME)
        # =========================
        safe_manifest_name = secure_filename(manifest_file.filename)
        manifest_path = os.path.join(UPLOAD_FOLDER, safe_manifest_name)
        manifest_file.save(manifest_path)

        # =========================
        # 📊 TRAIN FILE
        # =========================
        train_path = os.path.join(account_path, "train.xlsx")

        if train_file and train_file.filename != "":
            train_file.save(train_path)

        if not os.path.exists(train_path):
            return "❌ No training file found for this account. Please upload one."

        # =========================
        # ⚙️ PROCESS
        # =========================
        mapping = train_from_excel(train_path)
        manifest_data = extract_from_pdf(manifest_path)
        result = match_and_group(mapping, manifest_data)

        # =========================
        # 📄 GENERATE PDF NAME
        # =========================
        today = datetime.now().strftime("%Y-%m-%d")

        base_filename = f"{account_name}_{today}.pdf"
        output_pdf = os.path.join(account_path, base_filename)

        # 🔥 Avoid overwrite
        if os.path.exists(output_pdf):
            time_str = datetime.now().strftime("%H%M%S")
            base_filename = f"{account_name}_{today}_{time_str}.pdf"
            output_pdf = os.path.join(account_path, base_filename)

        # =========================
        # 📄 GENERATE PDF
        # =========================
        generate_pdf(result, output_pdf)

        # =========================
        # 🧪 DEBUG (optional)
        # =========================
        if not os.path.exists(output_pdf):
            return "❌ PDF not generated. Check generate_pdf function."

        # =========================
        # 📤 SEND FILE
        # =========================
        return send_file(
            output_pdf,
            as_attachment=True,
            download_name=base_filename
        )

    return render_template("index.html", accounts=accounts, user=username)


# -------------------------
# 🚀 RUN APP
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)