import imaplib
import email
from email.header import decode_header
import os
import sys
from datetime import datetime

# ==========================================
# CONFIGURAZIONE
# ==========================================
IMAP_SERVER = "imap.gmail.com"
TUTOR_EMAIL = "claudiacatanzaro90@gmail.com"
OUTPUT_DIR = "/Users/marco/Desktop/UNI/Comunicazioni_Tutor"

def clean_filename(s):
    return "".join(c if c.isalnum() or c in " .-_" else "_" for c in s).strip()

def decode_mime_words(s):
    if not s:
        return ""
    decoded_fragments = decode_header(s)
    result = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            result.append(fragment.decode(encoding or "utf-8", errors="replace"))
        else:
            result.append(str(fragment))
    return "".join(result)

def sync_tutor_emails(username, password):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_file = os.path.join(OUTPUT_DIR, "tutor_emails_archive.md")
    
    print(f"[*] Connessione sicura a {IMAP_SERVER}...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    try:
        mail.login(username, password)
    except Exception as e:
        print(f"[!] Errore di login: {e}")
        return False

    print(f"[*] Ricerca comunicazioni da: {TUTOR_EMAIL}...")
    mail.select("INBOX", readonly=True)
    
    # Cerca sia nel mittente (FROM) che nel destinatario/CC
    status, messages = mail.search(None, f'(FROM "{TUTOR_EMAIL}")')
    if status != "OK" or not messages[0]:
        print("[i] Nessuna email trovata da questo indirizzo.")
        mail.logout()
        return True

    mail_ids = messages[0].split()
    print(f"[+] Trovate {len(mail_ids)} email.")

    archive_entries = []

    for mid in reversed(mail_ids):
        res, msg_data = mail.fetch(mid, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_mime_words(msg.get("Subject", "(Senza Oggetto)"))
                date_str = msg.get("Date", "")
                from_str = decode_mime_words(msg.get("From", ""))
                
                body = ""
                attachments = []
                
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition", ""))
                        
                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                filename = decode_mime_words(filename)
                                clean_name = clean_filename(filename)
                                att_path = os.path.join(OUTPUT_DIR, clean_name)
                                with open(att_path, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                attachments.append(clean_name)
                        elif content_type == "text/plain" and "attachment" not in content_disposition:
                            charset = part.get_content_charset() or "utf-8"
                            body += part.get_payload(decode=True).decode(charset, errors="replace")
                else:
                    charset = msg.get_content_charset() or "utf-8"
                    body = msg.get_payload(decode=True).decode(charset, errors="replace")

                entry = f"## 📩 {subject}\n"
                entry += f"- **Data:** {date_str}\n"
                entry += f"- **Da:** {from_str}\n"
                if attachments:
                    entry += f"- **Allegati salvati:** {', '.join(attachments)}\n"
                entry += f"\n### Testo Messaggio:\n```text\n{body.strip()}\n```\n\n---\n"
                archive_entries.append(entry)

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"# Archivio Comunicazioni Tutor Claudia Catanzaro\n")
        f.write(f"*Ultimo aggiornamento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write("\n".join(archive_entries))

    print(f"[✓] Tutte le email e gli allegati sono stati salvati in: {log_file}")
    mail.logout()
    return True

if __name__ == "__main__":
    env_file = os.path.expanduser("~/.uni_gmail.env")
    if not os.path.exists(env_file):
        print(f"[!] File credenziali {env_file} non trovato.")
        sys.exit(1)
        
    config = {}
    with open(env_file, "r") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                config[k] = v

    user = config.get("GMAIL_USER")
    pwd = config.get("GMAIL_APP_PASSWORD")
    if not user or not pwd:
        print("[!] GMAIL_USER o GMAIL_APP_PASSWORD mancanti in ~/.uni_gmail.env")
        sys.exit(1)
        
    sync_tutor_emails(user, pwd)
