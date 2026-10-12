
import os
from io import BytesIO
from urllib.parse import urlparse

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, send_file, flash

from scanner import scan_website

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "accessicheck-local-key")



def get_db_connection():
    db_host = os.getenv("DB_HOST", "localhost")

    connection_config = {
        "host": db_host,
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "accessicheck"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }

    if db_host != "localhost":
        connection_config["ssl_ca"] = os.getenv("DB_SSL_CA", "ca.pem")
        connection_config["ssl_verify_cert"] = True
        connection_config["ssl_verify_identity"] = True

    return mysql.connector.connect(**connection_config)

def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            url VARCHAR(2048) NOT NULL,
            score INT NOT NULL,
            total_issues INT NOT NULL,
            critical_issues INT DEFAULT 0,
            serious_issues INT DEFAULT 0,
            moderate_issues INT DEFAULT 0,
            minor_issues INT DEFAULT 0,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    cursor.close()
    connection.close()


def validate_url(url):
    try:
        parsed = urlparse(url.strip())

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
    except Exception:
        return False


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()

        if not validate_url(url):
            flash("Please enter a valid website URL starting with http:// or https://.", "error")
            return redirect(url_for("index"))

        try:
            results = scan_website(url)

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO scan_history
                (url, score, total_issues, critical_issues,
                 serious_issues, moderate_issues, minor_issues)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                url,
                results["score"],
                results["total_issues"],
                results["critical_issues"],
                results["serious_issues"],
                results["moderate_issues"],
                results["minor_issues"]
            ))

            connection.commit()
            scan_id = cursor.lastrowid

            cursor.close()
            connection.close()

            return render_template(
                "report.html",
                results=results,
                scan_id=scan_id
            )

        except Exception as error:
            app.logger.exception("Website scan failed")
            flash(f"Scan failed: {error}", "error")
            return redirect(url_for("index"))

    return render_template("index.html")


@app.route("/history")
def history():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, url, score, total_issues, scanned_at
        FROM scan_history
        ORDER BY id DESC
    """)

    scans = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("history.html", scans=scans)


@app.route("/report/<int:scan_id>")
def saved_report(scan_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM scan_history WHERE id = %s",
        (scan_id,)
    )

    scan = cursor.fetchone()

    cursor.close()
    connection.close()

    if not scan:
        flash("Scan report not found.", "error")
        return redirect(url_for("history"))

    results = {
        "url": scan["url"],
        "score": scan["score"],
        "total_issues": scan["total_issues"],
        "critical_issues": scan["critical_issues"],
        "serious_issues": scan["serious_issues"],
        "moderate_issues": scan["moderate_issues"],
        "minor_issues": scan["minor_issues"],
        "violations": []
    }

    return render_template(
        "report.html",
        results=results,
        scan_id=scan_id
    )


@app.route("/download/<int:scan_id>")
def download_report(scan_id):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM scan_history WHERE id = %s",
        (scan_id,)
    )

    scan = cursor.fetchone()

    cursor.close()
    connection.close()

    if not scan:
        flash("Report not found.", "error")
        return redirect(url_for("history"))

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AccessiCheck - Accessibility Report", styles["Title"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph(f"Website: {scan['url']}", styles["Normal"]))
    story.append(Paragraph(f"Accessibility Score: {scan['score']}/100", styles["Normal"]))
    story.append(Paragraph(f"Total Issues: {scan['total_issues']}", styles["Normal"]))
    story.append(Paragraph(f"Critical Issues: {scan['critical_issues']}", styles["Normal"]))
    story.append(Paragraph(f"Serious Issues: {scan['serious_issues']}", styles["Normal"]))
    story.append(Paragraph(f"Moderate Issues: {scan['moderate_issues']}", styles["Normal"]))
    story.append(Paragraph(f"Minor Issues: {scan['minor_issues']}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This report is an automated accessibility check, not a complete certification.",
        styles["Italic"]
    ))

    document.build(story)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"accessibility_report_{scan_id}.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    try:
        init_db()
        print("AccessiCheck database connected successfully.")
        app.run(debug=True)
    except mysql.connector.Error as error:
        print("MySQL connection failed:", error)
        print("Check your MySQL service and .env database credentials.")
