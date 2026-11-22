# kindle-sync

Email a link to yourself, read it on your Kindle.

## Flow

1. Send an email to `<you>+kindle@gmail.com` with one or more URLs in the body. The subject doesn't matter. The `/kindle` skill in `skill/` does this from Claude Code.
2. Every hour, or when you run `gh workflow run kindle-sync`, GitHub Actions runs `sync.py`.
3. `sync.py` logs into Gmail over IMAP and finds every email to the `+kindle` alias that doesn't have a `kindle-sent` or `kindle-failed` label yet.
4. For each URL in each email:
   - Gmail's `google.com/url?q=` redirects are unwrapped.
   - X/Twitter links are fetched through the fxtwitter JSON API, since x.com doesn't render without JS.
   - Every other link goes through trafilatura, which pulls out the article body, the title, and the preview image.
5. The article is built into an EPUB, using the preview image as the cover, and sent over SMTP to your Kindle address.
6. The email gets labeled `kindle-sent` if every link went through, or `kindle-failed` if any link didn't. Labeled emails aren't picked up again, so a failed link won't be retried automatically.

## Setup

Add these repo secrets:

- `GMAIL_USER`: your Gmail address
- `GMAIL_APP_PASSWORD`: a Gmail [app password](https://myaccount.google.com/apppasswords) (IMAP has to be enabled)
- `KINDLE_EMAIL`: your Send-to-Kindle address

Add `GMAIL_USER` to the approved senders list in Amazon's Personal Document Settings. Kindle drops mail from any other sender.

To run it locally, export the same three variables, then:

```
pip install -r requirements.txt
python sync.py
```
