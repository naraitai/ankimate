import os
from flask import Flask, render_template, request, redirect, send_file, session, flash
from flask_session import Session
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, InternalServerError, default_exceptions
import csv
import sqlite3
import json
import redis
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from smtplib import SMTPException
from tempfile import TemporaryDirectory

ALLOWED_EXTENSIONS = {"txt", "csv", "tsv"}
DOWNLOAD_FOLDER = "downloads"

app = Flask(__name__)

#File upload configuration
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000

#Mail configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER")
#Mail testing configuration
app.config["TESTING"] = False
app.config["MAIL_SURPRESS_SEND"] = False

mail = Mail(app)

#Session configuration (redis)
app.secret_key = "k2CTM-kJnW5JUI16gtMh_Q"
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_REDIS"] = redis.from_url(os.environ.get("REDIS_URL"))
Session(app)

#AWS
app.config["ACCESS_KEY_ID"] = os.environ.get("AWS_ACCESS_KEY_ID")
app.config["SECRET_ACCESS_KEY"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
app.config["S3_BUCKET"] = os.environ.get("S3_BUCKET")

#App functions - Check upload file extension (ATTRIBUTION)
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html") 

@app.route("/build", methods=["GET", "POST"])
def build():

    #HTML data-form options (input language / translation & output options)
    languages = ["JP", "CMN"]
    translation = ["none", "english"]
    data = ["sentence", "translation", "transcription"]

    if request.method == "GET":
        return render_template("build.html", languages=languages, translation=translation, data=data)

#Process input data using selected options
@app.route("/process", methods=["POST"])
def process():

    #Get user input parameters
    fields = ["front", "back", "extra-1"]

    option = {}
    out_opt = {}
    form = request.form
    for opt in form:
        if opt in fields:
            out_opt[opt.lower()] = form[opt.lower()]
        else:
            option[opt.lower()] = form[opt.lower()]
    session["option"] = option
    session["out_opt"] = out_opt
    
    #Store matched sentences
    sentences = {}
    single = {}
    
    #Save user uploaded file
    #Check file uploaded (REVIEW)
    if "file" not in request.files:
        return redirect(request.url)
    file = request.files["file"]
    if file.filename == "":
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        #Open user uploaded file and read to memory (CHECK FOR UPLOADED FILE DATA STRUCTURE)
        with TemporaryDirectory() as tmpdir:
            file.save(os.path.join(tmpdir, filename))
            with open(os.path.join(tmpdir, filename), "r", encoding="utf-8") as input:
                reader=csv.DictReader(input, delimiter="\n", fieldnames=("w"))  

                #Open database
                con = sqlite3.connect("language.db")
                db = con.cursor()

                #Iterate accross user vocabulary
                for row in reader:
                    word = row["w"].strip()

                    #Search Japanese data
                    if option["lang"] == "jp":
                        #Get matches without translation
                        if option["trans"] == "none":
                            db.execute("SELECT sentence, furigana FROM sentencesJP \
                                WHERE tokens LIKE ? AND jlpt <= (SELECT jlpt FROM levelJP WHERE dict_id = \
                                (SELECT id FROM dictionaryJP WHERE word = ? OR furigana = ?)) \
                                ORDER BY jlpt DESC, frequency LIMIT 5;", ("%[" + word + "]%", word, word))
                            results = db.fetchall()
                        #Get matches with translation
                        else:
                            db.execute("SELECT sentencesJP.sentence, sentencesJP.furigana, sentencesEN.sentence \
                                FROM transJP_EN JOIN sentencesJP ON transJP_EN.jp_id = sentencesJP.id \
                                JOIN sentencesEN ON transJP_EN.en_id = sentencesEN.id \
                                WHERE sentencesJP.tokens LIKE ? AND sentencesJP.jlpt <= (SELECT jlpt FROM levelJP \
                                WHERE dict_id = (SELECT id FROM dictionaryJP WHERE word = ? OR furigana = ?)) \
                                ORDER BY jlpt DESC, frequency LIMIT 5;", ("%[" + word + "]%", word, word))
                            results = db.fetchall()
                            #No sentence matching level available
                            if not results:
                                db.execute("SELECT sentencesJP.sentence, sentencesJP.furigana, sentencesEN.sentence \
                                FROM transJP_EN JOIN sentencesJP ON transJP_EN.jp_id = sentencesJP.id \
                                JOIN sentencesEN ON transJP_EN.en_id = sentencesEN.id \
                                WHERE sentencesJP.tokens LIKE ? \
                                ORDER BY jlpt, frequency LIMIT 5;", ("%[" + word + "]%",))
                                results = db.fetchall()
                        #Get any matches
                        if not results:
                            db.execute("SELECT sentence, furigana FROM sentencesJP WHERE tokens LIKE ? ORDER BY \
                                frequency LIMIT 5;", ("%[" + word + "]%",))
                            results = db.fetchall()
                            #Set translation to not found
                            if results and option["trans"] != "none" and len(results[0]) != 3:
                                results[0] = (results[0][0], results[0][1], "No translation found")
                        #No matches
                        if not results:
                            sentences[word] = ("No sentence found.", "No sentences found.", "No translation found.")
                        #Store matched sentences (sentences = all, single = AJAX return data)
                        else:
                            sentences[word] = results
                            single[word] = sentences[word][0]
                            del sentences[word][0]
                    
                    #REPETITIVE - ALTERNATIVE STRUCTURE?
                    #Search Mandarin Chinese data
                    if option["lang"] == "cn":
                        #Check if translation requested
                        if option["trans"] == "none":
                            db.execute("SELECT sentence, pinyin FROM sentencesCN WHERE tokens LIKE ? AND hsk <= (SELECT hsk FROM levelCN WHERE dict_id = (SELECT id FROM dictionaryCN WHERE word = ?)) ORDER BY hsk DESC, frequency LIMIT 5;", ("%[" + word + "]%", word))
                            results = db.fetchall()
                        else:
                            db.execute("SELECT sentencesCN.sentence, sentencesCN.pinyin, sentencesEN.sentence \
                                FROM transCN_EN JOIN sentencesCN ON transCN_EN.cn_id = sentencesCN.id \
                                JOIN sentencesEN ON transCN_EN.en_id = sentencesEN.id \
                                WHERE sentencesCN.tokens LIKE ? AND sentencesCN.hsk <= \
                                (SELECT hsk FROM levelCN WHERE dict_id = (SELECT id FROM dictionaryCN WHERE word = ?)) \
                                ORDER BY hsk DESC, frequency LIMIT 5;", ("%[" + word + "]%", word))
                            results = db.fetchall()
                            #No sentence matching level available
                            if not results:
                                db.execute("SELECT sentencesCN.sentence, sentencesCN.pinyin, sentencesEN.sentence \
                                    FROM transCN_EN JOIN sentencesCN ON transCN_EN.cn_id = sentencesCN.id \
                                    JOIN sentencesEN ON transCN_EN.en_id = sentencesEN.id \
                                    WHERE sentencesCN.tokens LIKE ? \
                                    ORDER BY hsk, frequency LIMIT 5;", ("%[" + word + "]%",))
                                results = db.fetchall()
                        #No matching sentences
                        if not results:
                            db.execute("SELECT sentence, pinyin FROM sentencesCN WHERE tokens LIKE ? \
                                    ORDER BY frequency;", ("%[" + word + "]%",))
                            results = db.fetchall()
                            #Set translation to not found
                            if results and option["trans"] != "none" and len(results[0]) == 2:
                                results[0] = (results[0][0], results[0][1], "No translation found")
                        #No matching sentences
                        if not results:
                            single[word] = ("No sentences found.", "No sentences found.", "No translation found.")
                        else:
                            #Save sentences (sentences = all, single = AJAX data)
                            sentences[word] = results
                            single[word] = sentences[word][0]
                            del sentences[word][0]

                #Save data in session
                session["sentences"] = sentences
                session["single"] = single
                
                #Dump data to JSON for AJAX reply
                data = json.dumps(single)

        return data

#User requests alternative sentence
@app.route("/reload", methods=["POST"])
def reload ():

    #Get sentences to reload
    words = request.form.getlist("reload")
    sentences = session["sentences"]
    single = session["single"]

    #Store new sentences
    new = {}
    #Iterate across requested changes
    for word in words:
        if  len(sentences[word]) == 1:
            #GIVE USER FEEDBACK SHOWING NO MORE SENTENCES
            print("GIVE USER FEEDBACK SHOWING NO MORE SENTENCES")
        else:
            new[word] = sentences[word][0]
            single[word] = sentences[word][0]
            del sentences[word][0]
    #Dump to JSON for AJAX response
    new = json.dumps(new)
    return new

@app.route("/download", methods=["POST"])
def download():
    
    #Create file
    filename = f"downloads/{datetime.now().strftime('%Y%m%d%H%M')}.txt"
    file = open(filename, "w", encoding="utf-8")
    
    #Get sentences from session and data output options
    single = session["single"]
    option = session["option"]
    out_opt = session["out_opt"]

    #CODE INTO DATA
    structure = {
        "sentence": 0,
        "transcription" : 1,
        "translation": 2,
    }
    #Iterate across selected sentences
    for entry in single:
        #Default output
        count = 1
        for option in out_opt:
            field = out_opt[option]

            if field == "none":
                file.write("")
                if count == len(out_opt):
                    file.write("\n")
            if option == "front":
                file.write(f"{single[entry][structure[field]]}")
            elif count == len(out_opt) and field != "none":
                file.write(f"\t{single[entry][structure[field]]}\n")
            elif field != "none":
                file.write(f"\t{single[entry][structure[field]]}")
            count += 1
            
    file.close()
    session.clear()
    return send_file(filename, as_attachment=True)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():

    #HTML contact form options
    requests = ["Feature", "Data", "Other"]
    
    #Send email (LONG RUNTIME USE @async)
    if request.method == "POST":
        text = request.form.get("message")
        subject = request.form.get("subject")
        msg = Message(subject, recipients=["contact.ankimate@gmail.com"])
        msg.body = text
        mail.send(msg)

        flash("Message sent", "success")
        return redirect("/contact")
    
    if request.method == "GET":
        return render_template("contact.html", requests=requests)
        
    return redirect("/contact")


#Scheduled cleanup of downloads directory
def cleanup():
    files = os.listdir(DOWNLOAD_FOLDER)
    for f in files:
        os.remove(os.path.join(DOWNLOAD_FOLDER, f))

schedule = BackgroundScheduler(daemon=True)
schedule.add_job(cleanup, "interval", minutes=15)
schedule.start()


#Check errors
def errorhandler(e):
    #Email re. exceptions in alert
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    alert = [500]
    if e.code in alert:
        subject = f"{e.code}: {e.name}"
        text = f"Error text:{e.description}.\nRoute: {request.url}"
        msg = Message(subject, recipients=["contact.ankimate@gmail.com"])
        msg.body = text
        mail.send(msg)
    #Display error page
    return render_template("error.html", error=e.code, message=e.name, description=e.description), e.code

#ATTRIBUTE (CS50)
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)