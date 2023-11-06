def escape_markdown_message(msg):
    return msg.replace(".", "\\.").replace("-", "\\-").replace("(", "\\(").replace(")", "\\)")