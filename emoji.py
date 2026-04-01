# ================= EMOJI PREMIUM CONFIG =================

from telethon.tl.types import MessageEntityCustomEmoji

# 🔥 LIST EMOJI PREMIUM (GANTI / TAMBAH SESUAI MAU LU)
EMOJI_IDS = [
    6089144627833611433,
    6088918540755148137,
    6089144627833611433
]

# 🔥 BUILD ENTITY (AUTO)
def build_emoji_entities():
    entities = []

    for i, eid in enumerate(EMOJI_IDS):
        entities.append(
            MessageEntityCustomEmoji(
                offset=i,
                length=1,
                document_id=eid
            )
        )

    return entities


# 🔥 BUILD TEXT (PLACEHOLDER)
def build_emoji_text():
    return "🔥" * len(EMOJI_IDS) + " "
