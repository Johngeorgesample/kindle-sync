import email
import email.policy
import html
import imaplib
import os
import re
import smtplib
from email.message import EmailMessage

import trafilatura

USER = os.environ["GMAIL_USER"]
PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
KINDLE = os.environ["KINDLE_EMAIL"]
ALIAS = USER.replace("@", "+kindle@")
SENT, FAILED = "kindle-sent", "kindle-failed"


def queued(imap):
    # ponytail: English-locale mailbox name; other Gmail locales name All Mail differently
    imap.select('"[Gmail]/All Mail"')
    query = f"to:{ALIAS} -label:{SENT} -label:{FAILED}"
    _, data = imap.search(None, "X-GM-RAW", f'"{query}"')
    return data[0].split()


def urls_in(imap, num):
    # PEEK so the email isn't marked read just because we processed it
    _, data = imap.fetch(num, "(BODY.PEEK[])")
    body = email.message_from_bytes(data[0][1], policy=email.policy.default).get_body(("plain", "html"))
    urls = re.findall(r"https?://[^\s<>\"']+", body.get_content())
    return list(dict.fromkeys(u.rstrip(").,") for u in urls))


def article(url):
    page = trafilatura.fetch_url(url)
    body = page and trafilatura.extract(page, output_format="html", url=url)
    if not body:
        return None
    body = re.sub(r"</?(html|body)>", "", body)
    meta = trafilatura.extract_metadata(page)
    return (meta and meta.title) or url, body


def kindle_email(title, body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = USER, KINDLE, title
    page = f"<html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head><body><h1>{html.escape(title)}</h1>{body}</body></html>"
    # Kindle shows the attachment's filename as the document title
    filename = re.sub(r"[^\w\- ]", "", title)[:80].strip() or "article"
    msg.add_attachment(page.encode(), maintype="text", subtype="html", filename=f"{filename}.html")
    return msg


def deliver(smtp, url):
    found = article(url)
    if found:
        smtp.send_message(kindle_email(*found))
    return bool(found)


def main():
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap, smtplib.SMTP_SSL("smtp.gmail.com") as smtp:
        imap.login(USER, PASSWORD)
        smtp.login(USER, PASSWORD)
        for num in queued(imap):
            delivered = [deliver(smtp, url) for url in urls_in(imap, num)]
            imap.store(num, "+X-GM-LABELS", SENT if all(delivered) else FAILED)


if __name__ == "__main__":
    main()
