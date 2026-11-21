import email
import email.policy
import html
import io
import imaplib
import os
import re
import smtplib
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from email.message import EmailMessage

import trafilatura
from ebooklib import epub

USER = os.environ["GMAIL_USER"]
PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
KINDLE = os.environ["KINDLE_EMAIL"]
ALIAS = USER.replace("@", "+kindle@")
SENT, FAILED = "kindle-sent", "kindle-failed"
# Kindle EPUB covers; webp/avif get dropped rather than risk a failed conversion
COVER_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif"}


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
    return list(dict.fromkeys(unwrap(u.rstrip(").,")) for u in urls))


def unwrap(url):
    # Gmail (incl. its API connector) rewrites links as google.com/url?q=<real url>
    parts = urlsplit(url)
    if parts.netloc.endswith("google.com") and parts.path == "/url":
        return parse_qs(parts.query).get("q", [url])[0]
    return url


def article(url):
    page = trafilatura.fetch_url(url)
    body = page and trafilatura.extract(page, output_format="html", url=url)
    if not body:
        return None
    body = re.sub(r"</?(html|body)>", "", body)
    meta = trafilatura.extract_metadata(page)
    return (meta and meta.title) or url, body, meta and meta.image


def cover(url):
    try:
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
            ext = COVER_TYPES.get(r.headers.get_content_type())
            return ext and (f"cover.{ext}", r.read())
    except (OSError, ValueError):
        return None


def to_epub(title, body, image):
    book = epub.EpubBook()
    book.set_identifier(title)
    book.set_title(title)
    book.set_language("en")
    hero = f'<img src="{image[0]}" alt=""/>' if image else ""
    page = epub.EpubHtml(title=title, file_name="article.xhtml", content=f"{hero}<h1>{html.escape(title)}</h1>{body}")
    book.add_item(page)
    book.add_item(epub.EpubNav())
    # ebooklib's generated cover page and an empty toc both crash its writer
    book.toc, book.spine = [page], [page]
    if image:
        book.set_cover(*image, create_page=False)
    out = io.BytesIO()
    # write_epub swallows errors and returns a truncated book, so use the writer directly
    writer = epub.EpubWriter(out, book, {})
    writer.process()
    writer.write()
    return out.getvalue()


def kindle_email(title, book):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = USER, KINDLE, title
    filename = re.sub(r"[^\w\- ]", "", title)[:80].strip() or "article"
    msg.add_attachment(book, maintype="application", subtype="epub+zip", filename=f"{filename}.epub")
    return msg


def deliver(smtp, url):
    found = article(url)
    if found:
        title, body, image_url = found
        smtp.send_message(kindle_email(title, to_epub(title, body, image_url and cover(image_url))))
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
