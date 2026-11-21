---
name: kindle
description: Send one or more article links to the user's Kindle. Use when the user says "kindle", "send to kindle", or pastes links they want to read later on Kindle.
argument-hint: <url> [url ...]
---

Links: $ARGUMENTS

1. Pull every http(s) URL out of the links above (any separator: spaces, newlines, commas). If none, ask for them.
2. Send ONE email with the Gmail connector's `send_message` tool:
   - to: `johngeorgesample+kindle@gmail.com`
   - subject: `kindle`
   - body: the URLs, one per line
3. Kick off delivery now instead of waiting for the hourly cron:
   `gh workflow run kindle-sync -R Johngeorgesample/kindle-sync`
4. Reply with one line: how many links were queued.

The `kindle-sync` repo's sync.py does the actual extraction and Kindle delivery; this skill only queues links. If an article never arrives, look for the email under the `kindle-failed` Gmail label.
