# Ankimate
Faster Anki card creation

#### Video Demo: https://youtu.be/cAAORTWtiMc

## Document Description
### Templates
* Layout: Defines the header and footer to be applied to each page.
* Index: Welcomes user and gives brief explanation of tool.
* Build: The main page where users input data, select options and download data.
* About: Gives more detail on tool as well as referring to resources used in the creation of it.
* Contant: Allows users to send a message via email once specified the subject of the email.
* error: template to return when exception is thrown.

### Static
* ankimate.svg: An SVG file for tool logo.
* favicon.svg / favicon.ico: An SVG and ico of tool favicon.
* scripts.js: JavaScript scripts for highlighting current page in navbar, submitting forms via AJAX, making elements collapsible, generate HTML table to hold database returns.
* styles.css: Containing all styles for tool. Including responsive design and custom loading style that displays elipsis to suggest loading during database query.

### Empty Directories
* Downloads: Where the download file is saved before being downloaded to users browser. The file is named using current data and time to.

### Other assorted files
* .env: File to hold sensitive information like email addresses and passwords.
* .gitignore: File to specify which files to ignore (configuration file)
* requirements.txt: File containing all required modules for the tool.

### Database (Language.db)
A SQLite database containing all examples sentences, dictionaries and translations.
Tables:
   * sentencesJP / sentencesCN / sentencesEN: Tables holding examples sentences, tokenized sentence, frequency rating and level rating.
   * dictionaryJP / dictionaryCN: Tables holding basic dicitonary entries (primarily for future features)
   * levelJP / levelCN: Tables holding vocabulary lists for standardised language tests (JLPT and HSK)
   * transJP_EN / transCN_EN / transJP_CN: Tables linking example sentences to each to show which is a translation of which. Currently only JP / CN to EN is supported.

### The App (ankimate.py)
The main app backend.
* /process: Defines what to do with user input data. Queries database for sentences and returns 5 matches. The matches are saved to the session and one sentence for each is returned to populate the results table.
* /reload: Receives sentences user has requested to reload. Returns the next matching sentence in stored matches list.
* Functions
   * errorhandler: Generic error handler to catch all exceptions and display error.html page. If exception is in alert sends an email with error information to app admin email.
   * cleanup: Scheduled function to intermitently clear the files from downloads directory. Simpler implementation, rather than trying to delete file asyncronously after file has been sent for download.
* Other: There are various configuration settings for email, session and to handle file uploads. The chosen session is redis, as it was easier to handle in memory session, rather than file system, when there is no login or logout route. Session is cleared just before file is downloaded.

## The problem
Anki is a great SRS (Space Repetition System) for learning languages. However, making good quality study cards is time consuming. Ankimate aims to reduce the time it takes.

## The Solution
Simply, Ankimate takes a vocbulary list and returns one example sentence for each word in the list.

### Currently Supported Languages
* Japanese
* Mandarin Chinese

### User guide
1. Users must:
   1. upload a vocabulary list as a text file
   2. select the language (Japanese or Mandarin Chinese) 
   3. choose whether to include English translations (if available)  
   4. Select how to arrange the data in the download file
2. Users can then review the sentences that Ankimate returns, reloading any that are unsatisfactory (while more sentences are available).
3. Users then download the data as a file in a tab separated format.
4. Users can import the download file into Anki to automatically generate one note for each line in the downloaded file.

## Future Features
Ankimate is very much under active development and a range of further features are anticipated. These include...
* Frontend: Giving users greater control over the parameters used for selecting matching sentences.
* Backend: Automatic language identification for uploaded files.

## Credits
While the creation of Ankimate itself has been my own work it relies on the work of others. I am very grateful for those who have made their work available for others.
1. For the data 
   * Tatoeba (example sentences) 
   * JMDict (dictionary data)
   * Leeds University (frequency data)
2. For Natural Language Processing
   * Fugashi (Japanese tokenizer)
   * Jieba (Mandarin tokenizer)
