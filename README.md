# botv2-tele
I created a Telegram button bot feature in 2020 
Berikut adalah kode lengkap yang sudah direvisi total. Semua bug fatal terkait variabel global telah diperbaiki, konflik pengirim pesan teks (MessageHandler) sudah disatukan ke dalam fungsi handle_all_text_messages, dan format Markdown telah dikunci menggunakan ParseMode.MARKDOWN agar pesan teks cantik Anda tidak menyebabkan error sistem.
Anda cukup menyalin seluruh kode di bawah ini dan mengganti isi file lama Anda:

import jsonimport osimport reimport asyncioimport traceback
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Updatefrom telegram.constants import ParseModefrom telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import ADMIN_IDS, BOT_TOKEN, DATA_FILE

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data_loaded = json.load(f)
                if isinstance(data_loaded, dict):
                    return data_loaded
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in data file: {e}")
            print("[INFO] Creating new data file...")
        except Exception as e:
            print(f"[ERROR] Gagal load data: {e}")
    return {
        "active": {},
        "perak_mode": {},
        "bets": {},
        "aliases": {},
        "geseran": {},
    }

# Deklarasi awal variabel global datadata = load_data()

def save_data():
    global data  # Memastikan Python merujuk ke variabel global 'data'
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"[ERROR] Gagal save data: {e}")

def is_admin(user_id):
    try:
        return int(user_id) in ADMIN_IDS
    except (TypeError, ValueError):
        return False

def is_active(chat_id):
    return data["active"].get(str(chat_id), False)

def is_perak(chat_id):
    return data["perak_mode"].get(str(chat_id), True)

def get_bets(chat_id):
    cid = str(chat_id)
    if cid not in data["bets"]:
        data["bets"][cid] = {}
    return data["bets"][cid]

def parse_bet(text):
    text = text.strip().upper().replace(",", ".")
    m = re.match(r"^([KB])\s*(\d+(?:\.\d+)?)$", text)
    if m:
        return m.group(1), float(m.group(2))
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([KB])$", text)
    if m:
        return m.group(2), float(m.group(1))
    return None, None

def calc_amount(raw, perak_mode):
    if perak_mode:
        return int(raw * 1000)
    if raw == int(raw):
        return int(raw)
    return raw

def format_amount(amount):
    if isinstance(amount, int):
        return f"{amount:,}".replace(",", ".")
    return str(amount)

async def get_display_name(user):
    if not user:
        return "Unknown"
    name = getattr(user, "first_name", "") or ""
    last_name = getattr(user, "last_name", "") or ""
    if last_name:
        name = f"{name} {last_name}".strip()
    return name.strip() or f"User_{getattr(user, 'id', 'unknown')}"

def create_main_menu():
    buttons = [
        [
            InlineKeyboardButton("✅ ON Bot", callback_data="cmd_on"),
            InlineKeyboardButton("❌ OFF Bot", callback_data="cmd_off"),
        ],
        [
            InlineKeyboardButton("📋 LIST", callback_data="cmd_list"),
            InlineKeyboardButton("🗑 RESET", callback_data="cmd_rs"),
        ],
        [
            InlineKeyboardButton("📊 REKAP", callback_data="cmd_rk"),
            InlineKeyboardButton("💰 PERAK", callback_data="cmd_perak"),
        ],
        [InlineKeyboardButton("💵 NON-PERAK", callback_data="cmd_nonperak")],
        [InlineKeyboardButton("📖 BANTUAN", callback_data="cmd_help")],
    ]
    return InlineKeyboardMarkup(buttons)

def create_list_menu():
    buttons = [
        [
            InlineKeyboardButton("🔄 REFRESH", callback_data="cmd_list"),
            InlineKeyboardButton("📊 REKAP", callback_data="cmd_rk"),
        ],
        [InlineKeyboardButton("🗑 RESET LIST", callback_data="cmd_rs")],
        [InlineKeyboardButton("⬅️ KEMBALI", callback_data="cmd_menu")],
    ]
    return InlineKeyboardMarkup(buttons)

def create_help_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ KEMBALI", callback_data="cmd_menu")]])

async def answer_admin_error(update: Update):
    if update.callback_query:
        await update.callback_query.answer("❌ Anda bukan admin!", show_alert=True)
        return
    if update.effective_message:
        await update.effective_message.reply_text("❌ Anda bukan admin!")

async def require_admin(update: Update):
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None or not is_admin(user_id):
        await answer_admin_error(update)
        return False
    return True

async def send_or_edit(update: Update, text: str, buttons=None):
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)
        await update.callback_query.answer()
        return
    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    msg = """╔════════════════════════════════════╗
║  🤖 UBOT LIST - MENU UTAMA 🤖      ║
║                                    ║
║  Selamat datang di UBOT LIST!     ║
║  Gunakan tombol di bawah untuk    ║
║  mengelola taruhan K/B 💰         ║
╚════════════════════════════════════╝

Pilih aksi yang ingin dilakukan:"""
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=create_main_menu())
        await update.callback_query.answer()
    else:
        await update.message.reply_text(msg, reply_markup=create_main_menu())

async def handle_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    data["active"][cid] = True
    if cid not in data["perak_mode"]:
        data["perak_mode"][cid] = True
    save_data()
    msg = """╔════════════════════════════════════╗
║  ✅ UBOT LIST AKTIF ✅              ║
╚════════════════════════════════════╝

🎯 Bot mulai mencatat bet!
🔄 Mode: PERAK (B1 = 1000)

Silakan mulai pasang bet di grup.
📝 Format: K5, B10, atau 5K, 10B

Ketik /cmd untuk bantuan lengkap."""
    await send_or_edit(update, msg, create_main_menu())

async def handle_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    data["active"][cid] = False
    save_data()
    msg = """╔════════════════════════════════════╗
║  ❌ UBOT LIST DIMATIKAN ❌          ║
╚════════════════════════════════════╝

🛑 Bot berhenti mencatat bet.

Untuk mengaktifkan kembali,
klik tombol ✅ ON Bot"""
    await send_or_edit(update, msg, create_main_menu())

async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bets = get_bets(update.effective_chat.id)
    if not bets:
        msg = """╔════════════════════════════════════╗
║  📋 LIST RONDE INI 📋              ║
╚════════════════════════════════════╝

❌ List masih kosong!
Belum ada yang pasang bet.

Tunggu atau minta member untuk
pasang bet terlebih dahulu. 💰"""
    else:
        k_list, b_list = [], []
        for uid, info in bets.items():
            line = f"• {info['name']} {format_amount(info['amount'])}"
            if info["username"]:
                line += f" {info['username']}"
            if info["type"] == "K":
                k_list.append(line)
            else:
                b_list.append(line)

        k_total = sum(i["amount"] for i in bets.values() if i["type"] == "K")
        b_total = sum(i["amount"] for i in bets.values() if i["type"] == "B")

        msg = "╔════════════════════════════════════╗\n"
        msg += "║  📋 LIST RONDE INI 📋              ║\n"
        msg += "╚════════════════════════════════════╝\n\n"

        if k_list:
            msg += "🔻 *KECIL (K)*\n"
            msg += "\n".join(k_list) + "\n\n"
        else:
            msg += "🔻 KECIL: - (kosong)\n\n"

        if b_list:
            msg += "🔺 *BESAR (B)*\n"
            msg += "\n".join(b_list) + "\n\n"
        else:
            msg += "🔺 BESAR: - (kosong)\n\n"

        msg += "═══════════════════════════════════\n"
        msg += f"💰 Total K: *{format_amount(k_total)}*\n"
        msg += f"💰 Total B: *{format_amount(b_total)}*\n"
        msg += f"👥 Pemain: *{len(bets)}* orang\n"
        msg += "═══════════════════════════════════"

    await send_or_edit(update, msg, create_list_menu())

async def handle_rs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    data["bets"][cid] = {}
    save_data()
    msg = """╔════════════════════════════════════╗
║  🗑 RESET LIST - RONDE BARU 🗑      ║
╚════════════════════════════════════╝

✅ List berhasil dikosongkan!

🎯 Ronde baru dimulai.
Silakan mulai pasang bet lagi! 💰

📝 Format: K5, B10, atau 5K, 10B"""
    await send_or_edit(update, msg, create_main_menu())

async def handle_rk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bets = get_bets(update.effective_chat.id)
    if not bets:
        msg = """╔════════════════════════════════════╗
║  📊 REKAP TOTAL 📊                  ║
╚════════════════════════════════════╝

❌ List kosong!
Tidak ada yang bisa direkap."""
    else:
        k_total = sum(i["amount"] for i in bets.values() if i["type"] == "K")
        b_total = sum(i["amount"] for i in bets.values() if i["type"] == "B")
        selisih = abs(k_total - b_total)
        k_count = sum(1 for i in bets.values() if i["type"] == "K")
        b_count = sum(1 for i in bets.values() if i["type"] == "B")

        msg = "╔════════════════════════════════════╗\n"
        msg += "║  📊 REKAP TOTAL 📊                  ║\n"
        msg += "╚════════════════════════════════════╝\n\n"
        msg += f"🔻 KECIL: {k_count} pemain → *{format_amount(k_total)}*\n"
        msg += f"🔺 BESAR: {b_count} pemain → *{format_amount(b_total)}*\n"

msg += "═══════════════════════════════════\n\n"
if k_total > b_total:
msg += "⚠️ BESAR KURANG\n"
msg += f"💰 B perlu +{format_amount(selisih)}\n\n"
msg += "📌 Tambahkan bet di pihak B!"
elif b_total > k_total:
msg += "⚠️ KECIL KURANG\n"
msg += f"💰 K perlu +{format_amount(selisih)}\n\n"
msg += "📌 Tambahkan bet di pihak K!"
else:
msg += "✅ SEIMBANG!\n"
msg += "🎯 K dan B sudah seimbang sempurna!"
await send_or_edit(update, msg, create_list_menu())
async def handle_perak(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not await require_admin(update):
return
data["perak_mode"][str(update.effective_chat.id)] = True
save_data()
msg = """╔════════════════════════════════════╗
║ 💰 MODE PERAK AKTIF 💰 ║
╚════════════════════════════════════╝
🎯 Konversi taruhan:
B1 = 1.000
B10 = 10.000
B50 = 50.000
✅ Setiap bet akan dikali 1000"""
await send_or_edit(update, msg, create_main_menu())
async def handle_nonperak(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not await require_admin(update):
return
data["perak_mode"][str(update.effective_chat.id)] = False
save_data()
msg = """╔════════════════════════════════════╗
║ 💵 MODE NON-PERAK AKTIF 💵 ║
╚════════════════════════════════════╝
🎯 Taruhan nilai asli:
B1 = 1
B10 = 10
B50 = 50
✅ Bet akan dihitung nilai aslinya"""
await send_or_edit(update, msg, create_main_menu())
async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
msg = """╔════════════════════════════════════╗
║ 📖 PANDUAN LENGKAP 📖 ║
╚════════════════════════════════════╝
🔘 TOMBOL UTAMA
✅ ON Bot → Aktifkan bot
❌ OFF Bot → Matikan bot
📋 LIST → Lihat daftar bet
🗑 RESET → Kosongkan list
📊 REKAP → Lihat perhitungan
💰 PERAK → Mode x1000
💵 NON-PERAK → Mode normal
📝 FORMAT BET
K5 = Kecil 5
B10 = Besar 10
5K = Kecil 5 (dibalik)
10B = Besar 10 (dibalik)
⚙️ COMMAND TEXT
/on /off = Aktif/Matikan
/list = Daftar bet
/rs = Reset
/rk = Rekap
/perak /nonperak = Mode
/cmd = Bantuan
Legacy alias .on/.off/.list/.rs/.rk/.perak/.nonperak/.cmd masih didukung.
👨‍💼 Hanya admin yang bisa
gunakan command!"""
await send_or_edit(update, msg, create_help_menu())
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not update.callback_query:
return
data_query = update.callback_query.data
if data_query == "cmd_menu":
await handle_menu(update, context)
elif data_query == "cmd_on":
await handle_on(update, context)
elif data_query == "cmd_off":
await handle_off(update, context)
elif data_query == "cmd_list":
await handle_list(update, context)
elif data_query == "cmd_rs":
await handle_rs(update, context)
elif data_query == "cmd_rk":
await handle_rk(update, context)
elif data_query == "cmd_perak":
await handle_perak(update, context)
elif data_query == "cmd_nonperak":
await handle_nonperak(update, context)
elif data_query == "cmd_help":
await handle_help(update, context)
async def handle_legacy_commands(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
aliases = {
".menu": handle_menu,
".on": handle_on,
".off": handle_off,
".list": handle_list,
".rs": handle_rs,
".rk": handle_rk,
".perak": handle_perak,
".nonperak": handle_nonperak,
".cmd": handle_help,
}
handler = aliases.get(text.lower())
if handler:
await handler(update, context)
async def handle_bet_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
if not is_active(update.effective_chat.id):
return
bet_type, raw = parse_bet(text)
if bet_type is None:
return
user = update.effective_user
name = await get_display_name(user)
uname = f"@{user.username}" if user and getattr(user, "username", None) else ""
get_bets(update.effective_chat.id)[str(user.id)] = {
"name": name,
"username": uname,
"type": bet_type,
"amount": calc_amount(raw, is_perak(update.effective_chat.id)),
}
save_data()
display_raw = int(raw) if raw == int(raw) else raw
emoji_type = "🔻" if bet_type == "K" else "🔺"
msg = f"{emoji_type} {name} → {bet_type}{display_raw}"
await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
## FUNGSI SENTRAL: Pengarah pesan agar tidak terjadi tumpang tindih Handler teks biasa
async def handle_all_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not update.effective_message or not update.effective_message.text:
return
text = update.effective_message.text.strip()
# Abaikan jika pesan berupa command bawaan Telegram standar (diawali '/')
if text.startswith("/"):
return
# 1. Cek apabila teks berupa command tipe legacy (diawali '.')
if text.startswith("."):
await handle_legacy_commands(update, context, text)
return
# 2. Jika bukan command titik, diproses otomatis sebagai teks taruhan
await handle_bet_text(update, context, text)
async def run_bot():
application = Application.builder().token(BOT_TOKEN).build()
# Handler Command Utama (menggunakan prefix '/')
application.add_handler(CommandHandler("menu", handle_menu))
application.add_handler(CommandHandler("on", handle_on))
application.add_handler(CommandHandler("off", handle_off))
application.add_handler(CommandHandler("list", handle_list))
application.add_handler(CommandHandler("rs", handle_rs))
application.add_handler(CommandHandler("rk", handle_rk))
application.add_handler(CommandHandler("perak", handle_perak))
application.add_handler(CommandHandler("nonperak", handle_nonperak))
application.add_handler(CommandHandler("cmd", handle_help))
application.add_handler(CommandHandler("help", handle_help))
# Handler Klik Tombol Menu (Callback Query)
application.add_handler(CallbackQueryHandler(handle_callback, pattern=r"^cmd_"))
# SATU HANDLER UTAMA TEKS: Mengurus legacy command '.' dan pesan taruhan sekaligus
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text_messages))
print("=" * 50)
print(" 🚀 UBOT LIST - STARTING...")
print("=" * 50)
print(" ✅ Bot token siap dipakai.")
print(" 📌 Gunakan /menu atau /help di grup untuk membuka menu.")
print("=" * 50)
await application.initialize()
await application.start()
await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
await application.updater.wait_until_stopped()
await application.stop()
await application.shutdown()
if name == "main":
try:
asyncio.run(run_bot())
except KeyboardInterrupt:
print("\n\n👋 Bot dihentikan. Sampai jumpa!")
except Exception as e:
traceback.print_exc()
print(f"\n❌ Error: {e}")


<FollowUp>
Silakan jalankan bot Anda dengan kode baru ini. Apabila Anda mengalami kendala saat melakukan pengujian seperti **error pada file database `DATA_FILE`** atau ingin menambahkan **fitur pembatasan minimal/maksimal angka taruhan**, beri tahu saya ya!
</FollowUp>


