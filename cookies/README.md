# YouTube Cookies (Private Render Secret File)

AlexaMusic reads YouTube cookies from a private file at runtime. Do not commit cookies to this repository and do not upload them to public paste websites.

## Configure Render

1. Export a YouTube cookie file in **Netscape HTTP Cookie File** format. It should start with:
   `# Netscape HTTP Cookie File`
2. In the Render Dashboard, open your AlexaMusic service and select **Environment**.
3. Under **Secret Files**, choose **Add Secret File**.
4. Set the filename to `cookies.txt`.
5. Paste the complete Netscape cookie file into the contents field and save.
6. Under **Environment Variables**, add:
   `COOKIE_FILE=/etc/secrets/cookies.txt`
7. Remove the old `COOKIES` variable. Save changes and let Render deploy the service.

Render makes secret files available at `/etc/secrets/<filename>` at runtime. The application validates the file and creates a restricted-permission working copy in `/tmp`.

## Security

- Never paste cookie contents into chat, logs, GitHub, or public paste services.
- If cookies were previously committed to a public repository, treat them as exposed and revoke that Google session before generating a replacement.
- Cookie files can expire. If YouTube still rejects a validly formatted file, generate a fresh export and replace the Render Secret File.
- A correctly formatted cookie file does not guarantee YouTube will allow every request.
