import csv
import json
import os 
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from config import SECRET_KEY
from flask import Flask, send_from_directory
from flask import flash
from flask import redirect
from flask import render_template 
from flask import request 
from flask import send_file
from flask import session
from flask_mail import Mail
from flask_mail import Message
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from tempfile import TemporaryDirectory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import default_exceptions
from functions import allowed_extensions
from database import db
from database import dictionaryCN, dictionaryJP
from database import levelCN, levelJP
from database import sentencesCN, sentencesEN, sentencesJP 
from database import transCN_EN, transJP_EN
from io import BytesIO

app = Flask(__name__)

app.config.from_pyfile('config.py')

db.init_app(app)

mail = Mail(app)

app.secret_key = SECRET_KEY
Session(app)

# Folder to store the file for download
DOWNLOAD_FOLDER = "downloads"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/build/<string:language_selected>", methods=["GET", "POST"])
def build(language_selected):

    session["language"] = language_selected
    data = ["sentence", "translation", "transcription", "word"]

    return render_template("build.html", language=language_selected, data=data)

# Process input data using selected options
@app.route("/fetch", methods=["POST", "GET"])
def fetch():

    # Store user selected settings in session
    session["settings"] = request.form

    # Check file
    if "file" not in request.files:
        return ("error", "No file")
    
    file = request.files["file"]
    if file.filename == "":
        return ("error", "No file")

    if file and allowed_extensions(file.filename):
        filename = secure_filename(file.filename)
    else:
        return ("error", "File type not allowed")

    # Stores all matched sentences
    all_query_results = {}
    # Stores currently selected sentences (intially first sentence of query)
    selected_query_results = {}
        
    # Open user uploaded file and read to memory (Future: support wider range of data formats in file)
    with TemporaryDirectory() as tmpdir:
        file.save(os.path.join(tmpdir, filename))
        
        with open(os.path.join(tmpdir, filename), "r", encoding="utf-8") as input:
            reader=csv.DictReader(input, delimiter="\n", fieldnames=("word",))  

            # Select query tables
            if session["language"] == "japanese":
                dictionary_tbl = dictionaryJP
                level_tbl = levelJP
                sentence_tbl = sentencesJP
                translation_tbl = transJP_EN
            
            elif session["language"] == "mandarin":
                dictionary_tbl = dictionaryCN
                level_tbl = levelCN
                sentence_tbl = sentencesCN
                translation_tbl = transCN_EN
            
            # Iterate accross user vocabulary
            for row in reader:
                word = row["word"].strip()

                #dictionary_entry = db.session.query(dictionaryJP.id).filter(dictionaryJP.word == query_word).first()
                
                #word_level = db.session.query(levelJP.grade).filter(levelJP.dict_id == dictionary_entry).first()[0]

                # Query translation / no translation via user selection. List of SQLAlchemy rows
                if session["settings"]["trans"] == "none":

                    query_results = sentence_tbl\
                            .query.with_entities(sentence_tbl.sentence, sentence_tbl.transcription)\
                            .filter(sentence_tbl.tokens.contains(word), sentence_tbl.grade <= 5)\
                            .order_by(sentence_tbl.grade.desc(), sentence_tbl.frequency)\
                            .limit(5)\
                            .all()

                elif session["settings"]["trans"] == "en":

                    query_results = db.session\
                            .query(sentence_tbl.sentence, sentence_tbl.transcription, sentencesEN.sentence.label("translation"))\
                            .join(translation_tbl, sentence_tbl.id==translation_tbl.jp_id)\
                            .join(sentencesEN, translation_tbl.en_id==sentencesEN.id)\
                            .filter(sentence_tbl.tokens.contains(word))\
                            .limit(5)\
                            .all()
                
                # Store results as list of dictionaries
                query_results =  [r._asdict() for r in query_results]

                # Store all query results
                if bool(query_results):
                    # Current selected sentence
                    all_query_results[word] = [1]

                    for query_result in query_results:
                        all_query_results[word].append(query_result)
                else:
                    # No result
                    if session["settings"]["trans"] == "none":
                        all_query_results[word] = [1, {'sentence': 'No sentence found', 'transcription': 'No transcription found'}]
                    elif session["settings"]["trans"] == "en":
                        all_query_results[word] = [1, {'sentence': 'No sentence found', 'transcription': 'No transcription found', "translation": "No translation found"}]
            
            # Select first return for all words
            for key in all_query_results:
                selected_query_results[key] = all_query_results[key][1]               
            
            # Store query results in session
            session["all_query_results"] = all_query_results
            session["selected_query_results"] = selected_query_results
            
            data = json.dumps(selected_query_results)

        return data

# User requests alternative sentence
@app.route("/reload", methods=["POST"])
def reload ():

    # Get sentences to reload
    words = request.form.getlist("reload")
        
    sentences = session["all_query_results"]
    selected = session["selected_query_results"]

    # Store new sentences to be returned
    new = {}
    # Iterate across words with sentence change requested
    for word in words:
        # Current index of selected sentence
        index = sentences[word][0]
        # Store total number of sentences found
        length = len(sentences[word]) - 1
        # Update sentence if another sentence is available
        if index < length:
            # Update selected sentence index
            new_index = index + 1
            sentences[word][0] = new_index
            # Store new selected sentences and update currently selected sentence
            new[word] = sentences[word][new_index]
            selected[word] = new[word]
        else:
            # ADD FEEDBACK TO SHOW NO MORE SENTENCES AVAILABLE / LOOP ROUND TO BEGINNING
            continue
            
        # Future: Add new route for user to rollback the sentences

    new = json.dumps(new)
    return new

# Download selected sentences following user chosen structure
@app.route("/download", methods=["POST"])
def download():

    # Get user selected data structure and store values as a list
    download_struct = request.form.to_dict().values()
    fields = []
    for item in download_struct:
        fields.append(item)

    print(fields)

    # Get sentences from session and data output options
    selected_query_results = session["selected_query_results"]

    print(selected_query_results)
    
    # Create file
    
    filename = f"{datetime.now().strftime('%Y%m%d%H%M')}.txt"

    with open(f"downloads/{filename}", "x", encoding="utf-8") as output:
    
# Iterate across selected sentences
        for entry in selected_query_results:
            # Iterate accross all form fields and add data to download file (tab separated)
            length = len(download_struct) - 1
            count = 0
            while count < length:
                if fields[count] == "word":
                    output.write(f"{entry}\t")
                else:
                    output.write(f"{selected_query_results[entry][fields[count]]}\t")
                count += 1
            # Add final field and escape to new line.
            if fields[count] == "word":
                    output.write(f"{entry}\n")
            else:
                output.write(f"{selected_query_results[entry][fields[count]]}\n")
        
    return send_file(f"downloads\{filename}", as_attachment=True, attachment_filename=filename)

# Renders page template only
@app.route("/about")
def about():
    return render_template("about.html")

# Renders page template and sends email
@app.route("/contact", methods=["GET", "POST"])
def contact():

    # HTML contact form options
    requests = ["Feature", "Data", "Other"]
    
    # Send email (LONG RUNTIME USE @async)
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


# Scheduled cleanup of downloads directory
def cleanup():
    files = os.listdir(DOWNLOAD_FOLDER)
    for f in files:
        os.remove(os.path.join(DOWNLOAD_FOLDER, f))

schedule = BackgroundScheduler(daemon=True)
schedule.add_job(cleanup, "interval", minutes=15)
schedule.start()


# Check errors
def errorhandler(e):
    # Email re. exceptions in alert
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    alert = [500]
    if e.code in alert:
        subject = f"{e.code}: {e.name}"
        text = f"Error text:{e.description}.\nRoute: {request.url}"
        msg = Message(subject, recipients=["contact.ankimate@gmail.com"])
        msg.body = text
        mail.send(msg)
    # Display error page
    return render_template("error.html", error=e.code, message=e.name, description=e.description), e.code

class FileError(HTTPException):
    code = 507
    description = 'File error'

app.register_error_handler(FileError, 507)

def handle_exception(e):
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.desciprtion,
    })
    return response

# ATTRIBUTE (CS50)
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)