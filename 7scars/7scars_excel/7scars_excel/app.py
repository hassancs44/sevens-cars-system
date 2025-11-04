from flask import Flask, render_template, request, jsonify
from datetime import datetime
import pandas as pd
import os, re

app = Flask(__name__)

# ====== المسارات ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXCEL_PATH = os.path.join(DATA_DIR, "سيارات تاجير.xlsx")
SHEET_NAME = "records"

# ====== الأعمدة ======
COLUMNS = [
    "plate", "color", "oil_date", "odometer", "oil_mileage", "make", "model",
    "n_plate", "n_all", "created_at", "updated_at"
]

# ====== أدوات مساعدة ======
def normalize_arabic(text: str) -> str:
    if text is None:
        return ""
    t = str(text).strip()
    t = re.sub(r"[إأآا]", "ا", t)
    t = re.sub(r"\s+", "", t)
    t = t.replace("ة", "ه").replace("ئ", "ي")
    t = re.sub(r"[^\w\u0600-\u06FF]", "", t)
    return t

def ensure_excel():
    """يتأكد من وجود ملف Excel في المجلد data"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(EXCEL_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_excel(EXCEL_PATH, sheet_name=SHEET_NAME, index=False)

def read_df():
    ensure_excel()
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, dtype=str)
    except Exception:
        df = pd.DataFrame(columns=COLUMNS)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df

def write_df(df: pd.DataFrame):
    ensure_excel()
    df = df.reindex(columns=COLUMNS)
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

# ====== الصفحات ======
@app.before_request
def setup():
    ensure_excel()

@app.route("/")
def root():
    # الصفحة الرئيسية = مكتب التأجير
    return render_template("rental.html", title="مكتب التأجير")

@app.route("/maintenance")
def maintenance_page():
    return render_template("maintenance.html", title="الورشة (الصيانة)")

@app.route("/rental")
def rental_page():
    return render_template("rental.html", title="مكتب التأجير")

# ====== API ======
@app.route("/api/records", methods=["GET"])
def api_records_list():
    q = (request.args.get("q", "") or "").strip()
    limit = (request.args.get("limit", "all") or "all").strip()

    df = read_df()

    # 🔍 البحث
    if q:
        nq = normalize_arabic(q)
        df["n_plate"] = df["plate"].apply(normalize_arabic)
        df["n_all"] = (
            df["plate"].fillna("") +
            df["color"].fillna("") +
            df["make"].fillna("") +
            df["model"].fillna("")
        ).apply(normalize_arabic)
        mask = df["n_plate"].str.contains(nq, na=False) | df["n_all"].str.contains(nq, na=False)
        df = df[mask]

    # 🔽 ترتيب
    if "created_at" in df.columns:
        df = df.sort_values(by="created_at", ascending=False)

    # 🔢 تحديد عدد السجلات
    if limit.isdigit():
        df = df.head(int(limit))

    out = df.fillna("")
    return jsonify({
        "success": True,
        "rows": out[["plate", "color", "oil_date", "odometer", "oil_mileage", "make", "model", "created_at"]].to_dict(orient="records")
    })

@app.route("/api/records", methods=["POST"])
def api_records_add():
    data = request.get_json(force=True) or {}
    required = ["plate", "color", "oil_date", "odometer", "oil_mileage", "make", "model"]
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"success": False, "message": f"حقول ناقصة: {', '.join(missing)}"}), 400

    # تحقق من التاريخ
    try:
        datetime.fromisoformat(str(data["oil_date"]).strip())
    except Exception:
        return jsonify({"success": False, "message": "صيغة التاريخ غير صحيحة (YYYY-MM-DD)"}), 400

    # تحقق من الأرقام
    try:
        _ = int(float(data["odometer"]))
        _ = int(float(data["oil_mileage"]))
    except Exception:
        return jsonify({"success": False, "message": "عداد/ممشى الزيت يجب أن يكون رقمًا"}), 400

    now_iso = datetime.now().isoformat(timespec="seconds")
    n_plate = normalize_arabic(data["plate"])
    n_all = normalize_arabic(f"{data['plate']} {data['color']} {data['make']} {data['model']}")

    df = read_df()
    new_row = {
        "plate": str(data["plate"]).strip(),
        "color": str(data["color"]).strip(),
        "oil_date": str(data["oil_date"]).strip(),
        "odometer": str(data["odometer"]).strip(),
        "oil_mileage": str(data["oil_mileage"]).strip(),
        "make": str(data["make"]).strip(),
        "model": str(data["model"]).strip(),
        "n_plate": n_plate,
        "n_all": n_all,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    write_df(df)

    return jsonify({"success": True, "message": "✅ تم حفظ السجل بنجاح"})

# ====== الإعداد للنشر ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Render / Heroku تحتاج إلى 0.0.0.0
    app.run(host="0.0.0.0", port=port, debug=False)
