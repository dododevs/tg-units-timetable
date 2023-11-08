from telegram.helpers import escape_markdown

def escape_markdown_message(msg):
    return escape_markdown(msg, version=2)