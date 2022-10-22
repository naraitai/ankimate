ALLOWED_EXTENSIONS = {"txt", "csv", "tsv"}

# Check file extension again allowed extensions
def allowed_extensions(filename):
    if "." in filename:
        extension = filename.rsplit(".", 1)[1].lower()
        return extension in ALLOWED_EXTENSIONS
    else:
        return False
