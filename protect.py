import re
import time
import sqlite3
from collections import defaultdict
from telethon import events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

# ================= DATABASE =================
conn = sqlite3.connect("protect.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS groups (chat_id TEXT PRIMARY KEY, antibc INT, antispam INT, sangmata INT)")
cursor.execute("CREATE TABLE IF NOT EXISTS whitelist (chat_id TEXT, user_id TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS blockwords (chat_id TEXT, word TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS mute (chat_id TEXT, user_id TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS names (user_id TEXT, name TEXT)")
conn.commit()

# ================= MEMORY =================
spam_tracker = defaultdict(list)
media_tracker = defaultdict(int)
warnings = defaultdict(int)

# ================= WORD LIST =================
SOFT = ["promo","vcs","tmo","jajantele","tmyyt","fwbh","vvip","tmnin bobo"]
HARD = ["yuk crot","18+","bokep","ngentot","coli","memek","kontol"]

# ================= HELPERS =================
def is_spam(uid):
    now = time.time()
    spam_tracker[uid].append(now)
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t < 8]
    return len(spam_tracker[uid]) > 5

def is_gibberish(text):
    if len(text) < 20:
        return False
    return (len(set(text)) / len(text)) < 0.35

def has_link(text):
    return bool(re.search(r"(https?://|t\.me/|@\w+)", text))

def unicode_bypass(text):
    return bool(re.search(r"[^\x00-\x7F]+", text))

def emoji_spam(text):
    return len(re.findall(r"[😀-🙏🔥💀😂🤣😍🥵😈👀]", text)) > 8

def toxic_score(text):
    score = 0
    for w in SOFT:
        if w in text:
            score += 1
    for w in HARD:
        if w in text:
            score += 3
    return score

def is_scam(text):
    return any(x in text for x in [
        "admin sini","pm admin","klik link","free saldo",
        "join cepat","wd cepat","deposit"
    ])

def is_whitelist(chat_id, user_id):
    cursor.execute("SELECT 1 FROM whitelist WHERE chat_id=? AND user_id=?", (str(chat_id), str(user_id)))
    return cursor.fetchone()

def is_muted(chat_id, user_id):
    cursor.execute("SELECT 1 FROM mute WHERE chat_id=? AND user_id=?", (str(chat_id), str(user_id)))
    return cursor.fetchone()

def get_group(chat_id):
    cursor.execute("SELECT * FROM groups WHERE chat_id=?", (str(chat_id),))
    return cursor.fetchone()

def warn(uid):
    warnings[uid] += 1
    return warnings[uid]

# ================= MAIN HOOK =================
def setup_protector(bot):

    async def restrict(chat_id, user_id):
        await bot(EditBannedRequest(
            chat_id,
            user_id,
            ChatBannedRights(until_date=None, send_messages=True)
        ))

    # ================= COMMAND =================

    @bot.on(events.NewMessage(pattern='/ping'))
    async def ping(e):
        s = time.time()
        msg = await e.reply("...")
        await msg.edit(f"🏓 Pong {round((time.time()-s)*1000)} ms")

    @bot.on(events.NewMessage(pattern='/antibc'))
    async def antibc(e):
        state = 1 if "on" in e.text.lower() else 0
        cursor.execute(
            "INSERT OR REPLACE INTO groups VALUES (?,?,COALESCE((SELECT antispam FROM groups WHERE chat_id=?),0),COALESCE((SELECT sangmata FROM groups WHERE chat_id=?),0))",
            (str(e.chat_id), state, str(e.chat_id), str(e.chat_id))
        )
        conn.commit()
        await e.reply(f"🔥 Antibc {'ON' if state else 'OFF'}")

    @bot.on(events.NewMessage(pattern='/antispam'))
    async def antispam(e):
        state = 1 if "on" in e.text.lower() else 0
        cursor.execute("UPDATE groups SET antispam=? WHERE chat_id=?", (state, str(e.chat_id)))
        conn.commit()
        await e.reply(f"⚡ Antispam {'ON' if state else 'OFF'}")

    @bot.on(events.NewMessage(pattern='/bl '))
    async def add_bl(e):
        word = e.text.split(None,1)[1].lower()
        cursor.execute("INSERT INTO blockwords VALUES (?,?)",(str(e.chat_id), word))
        conn.commit()
        await e.reply(f"🚫 Blocked: {word}")

    @bot.on(events.NewMessage(pattern='/unbl '))
    async def del_bl(e):
        word = e.text.split(None,1)[1].lower()
        cursor.execute("DELETE FROM blockwords WHERE chat_id=? AND word=?", (str(e.chat_id), word))
        conn.commit()
        await e.reply(f"✅ Unblocked: {word}")

    @bot.on(events.NewMessage(pattern='/addwhite'))
    async def addwhite(e):
        if not e.reply_to_msg_id:
            return await e.reply("Reply user")

        msg = await e.get_reply_message()
        cursor.execute("INSERT INTO whitelist VALUES (?,?)", (str(e.chat_id), str(msg.sender_id)))
        conn.commit()
        await e.reply("✅ Masuk whitelist")

    @bot.on(events.NewMessage(pattern='/delwhite'))
    async def delwhite(e):
        if not e.reply_to_msg_id:
            return await e.reply("Reply user")

        msg = await e.get_reply_message()
        cursor.execute("DELETE FROM whitelist WHERE chat_id=? AND user_id=?", (str(e.chat_id), str(msg.sender_id)))
        conn.commit()
        await e.reply("❌ Keluar whitelist")

    @bot.on(events.NewMessage(pattern='/mute'))
    async def mute(e):
        if not e.reply_to_msg_id:
            return

        msg = await e.get_reply_message()
        await restrict(e.chat_id, msg.sender_id)

        cursor.execute("INSERT INTO mute VALUES (?,?)", (str(e.chat_id), str(msg.sender_id)))
        conn.commit()
        await e.reply("🔇 User di mute")

    @bot.on(events.NewMessage(pattern='/unmute'))
    async def unmute(e):
        if not e.reply_to_msg_id:
            return

        msg = await e.get_reply_message()

        await bot(EditBannedRequest(
            e.chat_id,
            msg.sender_id,
            ChatBannedRights(send_messages=False)
        ))

        cursor.execute("DELETE FROM mute WHERE chat_id=? AND user_id=?", (str(e.chat_id), str(msg.sender_id)))
        conn.commit()
        await e.reply("🔊 User dilepas")

    @bot.on(events.NewMessage(pattern='/reload'))
    async def reload_cache(e):
        spam_tracker.clear()
        media_tracker.clear()
        warnings.clear()
        await e.reply("♻️ Cache dibersihkan")

    # ================= AUTO FILTER =================

    @bot.on(events.NewMessage)
    async def auto(e):
        if not e.is_group or not e.sender_id:
            return

        chat_id = e.chat_id
        user_id = e.sender_id
        text = (e.raw_text or "").lower()

        group = get_group(chat_id)
        if not group:
            cursor.execute("INSERT OR IGNORE INTO groups VALUES (?,?,?,?)", (str(chat_id),0,0,0))
            conn.commit()
            return

        antibc, antispam, sangmata = group[1], group[2], group[3]

        if is_whitelist(chat_id, user_id):
            return

        if is_muted(chat_id, user_id):
            await e.delete()
            return

        sender = await e.get_sender()
        if sender.bot:
            return

        # 🔥 SPAM
        if text and antispam and is_spam(user_id):
            await e.delete()
            if warn(user_id) >= 3:
                await restrict(chat_id, user_id)
            return

        # 🔥 EMOJI SPAM
        if emoji_spam(text):
            await e.delete()
            return

        # 🔥 GIBBERISH / HURUF ACAK
        if is_gibberish(text):
            await e.delete()
            return

        # 🔥 UNICODE BYPASS / FONT ANEH
        if unicode_bypass(text):
            await e.delete()
            return

        # 🔥 BLOCKWORDS (FIX REGEX)
        cursor.execute("SELECT word FROM blockwords WHERE chat_id=?", (str(chat_id),))
        for w in cursor.fetchall():
            if re.search(rf"\b{re.escape(w[0])}\b", text):
                await e.delete()
                return

        # 🔥 LINK NON ADMIN
        if has_link(text):
            try:
                perm = await bot.get_permissions(chat_id, user_id)
                if not perm.is_admin:
                    await e.delete()
                    return
            except:
                pass

        # 🔥 SCAM
        if is_scam(text):
            await e.delete()
            return

        # 🔥 TOXIC
        if toxic_score(text) >= 3:
            await e.delete()
            return
