import os, csv, sqlite3, json, redis
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, send_file, session, flash, abort
from flask_session import Session
from flask_mail import Mail, Message
from smtplib import SMTPException
from tempfile import TemporaryDirectory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, InternalServerError, default_exceptions

#Defines file extensions that can be uploaded
ALLOWED_EXTENSIONS = {"txt", "csv", "tsv"}
#Folder to store the file for download
DOWNLOAD_FOLDER = "downloads"

app = Flask(__name__)

#File upload size configuration
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
#app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_REDIS"] = redis.from_url(os.environ.get("REDIS_URL"))
Session(app)

#App functions - Check upload file extension (ATTRIBUTION)
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

#Index simply renders page template
@app.route("/")
def index():
    return render_template("index.html") 

#Build simply renders page template
@app.route("/build")
def build():

    #HTML data-form options (input language / translation & output options)
    languages = ["JP", "CMN"]
    translation = ["none", "english"]
    data = ["sentence", "translation", "transcription"]

    return render_template("build.html", languages=languages, translation=translation, data=data)

#Process input data using selected options
@app.route("/process", methods=["POST"])
def process():

    #Store user selected settings in session
    settings = request.form
    session["settings"] = settings
    #Set maxmium number of matched sentences to return (Future: Allow users to set this value)
    match_no = 5
    
    #Stores all matched sentences
    sentences = {}
    #Stores currently selected sentences (intially first sentence of query)
    selected = {}
    
    #Return user to page if no file uploaded
    if "file" not in request.files:
        return redirect(request.url)
    #Check uploaded file
    file = request.files["file"]
    if file.filename == "":
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        #Open user uploaded file and read to memory (Future: support wider range of data formats in file)
        with TemporaryDirectory() as tmpdir:
            file.save(os.path.join(tmpdir, filename))
            with open(os.path.join(tmpdir, filename), "r", encoding="utf-8") as input:
                reader=csv.DictReader(input, delimiter="\n", fieldnames=("w"))  

                #Open database
                con = sqlite3.connect("language.db")
                con.row_factory = sqlite3.Row
                db = con.cursor()
                
                #Get language option selected to complete query
                lang = settings["lang"].upper()
                
                #Iterate accross user vocabulary
                for row in reader:
                    word = row["w"].strip()

                    #Search for sentences without translations
                    if settings["trans"] == "none":
                        db.execute(f"SELECT sentence, transcription FROM sentences{lang} \
                            WHERE tokens LIKE ? AND grade <= (SELECT grade FROM level{lang} WHERE dict_id = (SELECT id FROM dictionary{lang} \
                            WHERE word = ? OR transcription = ?)) \
                            ORDER BY grade DESC, frequency LIMIT 5;", ("%[" + word + "]%", word, word))
                        results = db.fetchall()
                    #Search for sentences with translations and matched to grade
                    elif settings["trans"] == "en":
                        db.execute(f"SELECT sentences{lang}.sentence, sentences{lang}.transcription, sentencesEN.sentence AS translation \
                                FROM trans{lang}_EN JOIN sentences{lang} ON trans{lang}_EN.{settings['lang']}_id = sentences{lang}.id \
                                JOIN sentencesEN ON trans{lang}_EN.en_id = sentencesEN.id \
                                WHERE sentences{lang}.tokens LIKE ? AND sentences{lang}.grade <= (SELECT grade FROM level{lang} \
                                WHERE dict_id = (SELECT id FROM dictionary{lang} WHERE word = ? OR transcription = ?)) \
                                ORDER BY grade DESC, frequency LIMIT 5;", ("%[" + word + "]%", word, word))
                        results = db.fetchall()
                        #Search for sententences with translations without matching to grade (wider search)
                        if not results:
                            db.execute(f"SELECT sentences{lang}.sentence, sentences{lang}.transcription, sentencesEN.sentence AS translation \
                                FROM trans{lang}_EN JOIN sentences{lang} ON trans{lang}_EN.{settings['lang']}_id = sentences{lang}.id \
                                JOIN sentencesEN ON trans{lang}_EN.en_id = sentencesEN.id \
                                WHERE sentences{lang}.tokens LIKE ? \
                                ORDER BY grade, frequency LIMIT 5;", ("%[" + word + "]%",))
                            results = db.fetchall()
                    #Search for any sentences containing word (widest search)
                    if not results:
                        db.execute(f"SELECT sentence, transcription FROM sentences{lang} \
                            WHERE tokens LIKE ? ORDER BY frequency LIMIT 5;", ("%[" + word + "]%",))
                        results = db.fetchall()

                    #Store list for each word. Included the index of the currently selected sentence (first query return)
                    sentences[word] = []
                    sentences[word].append(1)
                    #Iterate over returned sentences and store as a list of dictionaries
                    for result in results:
                        sentences[word].append(dict(result))

                #Iterate over returned sentences and store first returned sentence (if available)
                for key in sentences:
                    #Check if any sentences found
                    if len(sentences[key]) > 1:
                        #Check if user selected to show translations
                        if settings["trans"] == "en":
                            length = len(sentences[key][1])
                            #If sentence with translation not found.
                            if length < 3:
                                selected[key] = sentences[key][1]
                                selected[key]["translation"] = "No translation found."
                            else:
                                selected[key] = sentences[key][1]
                        #If user did not select to show translations
                        else:
                            selected[key] = sentences[key][1]
                    #No sentences found
                    else:
                        #User selected sentences with translations
                        if settings["trans"] == "en":
                            selected[key] = {"sentence":"No sentences found.", "transcription":"No sentences found.", "translation":"No translation found."}
                        else:
                            selected[key] = {"sentence":"No sentences found.", "transcription":"No sentences found."}
            
                #Save data in session
                session["sentences"] = sentences
                session["selected"] = selected
                
                #Dump data to JSON for AJAX reply
                data = json.dumps(selected)

        return data

#User requests alternative sentence
@app.route("/reload", methods=["POST"])
def reload ():

    #Get sentences to reload
    words = request.form.getlist("reload")
    sentences = session["sentences"]
    selected = session["selected"]

    #Store new sentences to be returned
    new = {}
    #Iterate across words with sentence change requested
    for word in words:
        #Current index of selected sentence
        index = sentences[word][0]
        #Store total number of sentences found
        length = len(sentences[word]) - 1
        #Update sentence if another sentence is available
        if index < length:
            #Update selected sentence index
            new_index = index + 1
            sentences[word][0] = new_index
            #Store new selected sentences and update currently selected sentence
            new[word] = sentences[word][new_index]
            selected[word] = new[word]
        else:
            #ADD FEEDBACK TO SHOW NO MORE SENTENCES AVAILABLE
            continue
            
        #Future: Add new route for user to rollback the sentences

    #Dump to JSON for AJAX response
    new = json.dumps(new)
    return new

#Download selected sentences following user chosen structure
@app.route("/download", methods=["POST"])
def download():

    #Get user selected data structure
    download_struct = request.form

    #Get sentences from session and data output options
    single = session["selected"]
    
    #Create file
    filename = f"downloads/{datetime.now().strftime('%Y%m%d%H%M')}.txt"
    file = open(filename, "w", encoding="utf-8")
    
    #Iterate across selected sentences
    for entry in single:
        count = 1
        #Iterate across all user selected data fields (front, back...) (Future: Add function so users can add more card fields)
        for field in download_struct:
            field_val = download_struct[field]

            #Do not enter data for blank fields
            if field_val == "none":
                file.write("")
                if count == len(download_struct):
                    file.write("\n")
                    continue
                else:
                    continue
            else:
                #Do not enter lines where no sentence found
                if single[entry][field_val] == "No sentences found.":
                    if count == len(download_struct) and field_val != "none":
                        file.write(f"\n")
                    continue
                #Front added first
                if field == "front":
                    file.write(f"{single[entry][field_val]}")
                #Last field added with newline break
                elif count == len(download_struct) and field_val != "none":
                    file.write(f"\t{single[entry][field_val]}\n")
                #Middle field value
                else:
                    file.write(f"\t{single[entry][field_val]}")
                count += 1
    file.close()

    return send_file(filename, as_attachment=True)

#Renders page template only
@app.route("/about")
def about():
    return render_template("about.html")

#Renders page template and sends email
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