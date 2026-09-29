"""
UBOT LIST - Bot Telegram untuk mencatat taruhan K/B (Kecil/Besar)
Semua perintah menggunakan slash command (/) — bukan titik (.)
"""

import json
import os
import re
import asyncio
import traceback
from datetime import datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from config import ADMIN_IDS, BOT_TOKEN, DATA_FILE, AUTOSAVE_INTERVAL


# ============================================================
# UTILITAS DATA (LOAD / SAVE)
# ============================================================

def load_data():
    """Memuat data dari file JSON, jika gagal buat struktur baru."""
    default_data = {
        "active": {},          # status aktif per chat
        "perak_mode": {},      # mode perak per chat
        "bets": {},            # taruhan aktif per chat
        "aliases": {},         # alias user per chat
        "history": {},         # riwayat ronde selesai per chat
        "settings": {},        # pengaturan tambahan
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Pastikan semua key ada
                    for key, value in default_data.items():
                        data.setdefault(key, value)
                    return data
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON rusak: {e}")
        except Exception as e:
            print(f"[ERROR] Gagal load: {e}")
    return default_data


def save_data():
    """Menyimpan data ke file JSON."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Gagal save: {e}")


data = load_data()


# ============================================================
# FUNGSI BANTU (HELPERS)
# ============================================================

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


def get_aliases(chat_id):
    cid = str(chat_id)
    if cid not in data["aliases"]:
        data["aliases"][cid] = {}
    return data["aliases"][cid]


def get_history(chat_id):
    cid = str(chat_id)
    if cid not in data["history"]:
        data["history"][cid] = []
    return data["history"][cid]


def parse_bet(text):
    """
    Format yang didukung:
    - K5 / B10  → (K/B, angka)
    - 5K / 10B  → (K/B, angka) - terbalik
    - K5.5 / B2.5 - desimal
    """
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


def md(text):
    """Escape markdown special chars."""
    return escape_markdown(str(text), version=2)


async def get_display_name(user, chat_id=None):
    if not user:
        return "Unknown"
    uid = str(user.id)
    name = getattr(user, "first_name", "") or ""
    last = getattr(user, "last_name", "") or ""
    if last:
        name = f"{name} {last}".strip()
    # Cek alias custom
    if chat_id:
        aliases = get_aliases(chat_id)
        if uid in aliases and aliases[uid]:
            return aliases[uid]
    return name.strip() or f"User_{uid[-4:]}"


# ============================================================
# KEYBOARD INLINE
# ============================================================

def create_main_menu():
    return InlineKeyboardMarkup([
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
            InlineKeyboardButton("📈 TOTAL", callback_data="cmd_total"),
        ],
        [
            InlineKeyboardButton("💰 PERAK", callback_data="cmd_perak"),
            InlineKeyboardButton("💵 NON-PERAK", callback_data="cmd_nonperak"),
        ],
        [
            InlineKeyboardButton("⚙️ STATUS", callback_data="cmd_status"),
            InlineKeyboardButton("📖 BANTUAN", callback_data="cmd_help"),
        ],
    ])


def create_list_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 REFRESH", callback_data="cmd_list"),
            InlineKeyboardButton("📊 REKAP", callback_data="cmd_rk"),
        ],
        [
            InlineKeyboardButton("🗑 RESET LIST", callback_data="cmd_rs"),
            InlineKeyboardButton("📈 TOTAL", callback_data="cmd_total"),
        ],
        [InlineKeyboardButton("⬅️ KEMBALI", callback_data="cmd_menu")],
    ])


def create_help_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ KEMBALI MENU", callback_data="cmd_menu")]
    ])


# ============================================================
# AUTENTIKASI & RESPONSE
# ============================================================

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
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=buttons, parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception:
            # Fallback tanpa markdown
            try:
                await update.callback_query.edit_message_text(text, reply_markup=buttons)
            except Exception as e:
                print(f"[WARN] edit gagal: {e}")
        await update.callback_query.answer()
        return
    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=buttons)


# ============================================================
# HANDLER COMMANDS
# ============================================================

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    active = "✅ AKTIF" if is_active(cid) else "❌ MATI"
    mode = "💰 PERAK" if is_perak(cid) else "💵 NON-PERAK"
    msg = (
        "╔════════════════════════════════╗\n"
        "║  🤖 UBOT LIST - MENU UTAMA   ║\n"
        "╚════════════════════════════════╝\n\n"
        f"📊 Status Bot : {active}\n"
        f"🎯 Mode       : {mode}\n"
        f"💬 Chat ID    : `{cid}`\n\n"
        "Pilih aksi di bawah untuk mengelola taruhan:"
    )
    await send_or_edit(update, msg, create_main_menu())


async def handle_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    data["active"][cid] = True
    data["perak_mode"].setdefault(cid, True)
    save_data()
    msg = (
        "╔════════════════════════════════╗\n"
        "║  ✅ UBOT LIST AKTIF ✅        ║\n"
        "╚════════════════════════════════╝\n\n"
        "🎯 Bot mulai mencatat bet!\n"
        "🔄 Mode: PERAK (B1 = 1\\.000)\n\n"
        "📝 Format pasang bet:\n"
        "• `K5` / `B10` \\(Kecil/Besar\\)\n"
        "• `5K` / `10B` \\(terbalik\\)\n\n"
        "Ketik `/cmd` untuk bantuan lengkap\\."
    )
    await send_or_edit(update, msg, create_main_menu())


async def handle_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    data["active"][cid] = False
    save_data()
    msg = (
        "╔════════════════════════════════╗\n"
        "║  ❌ UBOT LIST DIMATIKAN ❌    ║\n"
        "╚════════════════════════════════╝\n\n"
        "🛑 Bot berhenti mencatat bet\\.\n\n"
        "Untuk mengaktifkan kembali, klik ✅ ON Bot\\."
    )
    await send_or_edit(update, msg, create_main_menu())


async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bets = get_bets(update.effective_chat.id)
    if not bets:
        msg = (
            "╔════════════════════════════════╗\n"
            "║  📋 LIST RONDE INI 📋         ║\n"
            "╚════════════════════════════════╝\n\n"
            "❌ List masih kosong\\!\n"
            "Belum ada yang pasang bet\\.\n\n"
            "Tunggu atau minta member untuk pasang bet 💰"
        )
    else:
        k_list, b_list = [], []
        for uid, info in bets.items():
            line = f"• {md(info['name'])} `{format_amount(info['amount'])}`"
            if info.get("username"):
                line += f" {md(info['username'])}"
            if info["type"] == "K":
                k_list.append(line)
            else:
                b_list.append(line)

        k_total = sum(i["amount"] for i in bets.values() if i["type"] == "K")
        b_total = sum(i["amount"] for i in bets.values() if i["type"] == "B")

        msg = (
            "╔════════════════════════════════╗\n"
            "║  📋 LIST RONDE INI 📋         ║\n"
            "╚════════════════════════════════╝\n\n"
        )
        if k_list:
            msg += "🔻 KECIL \\(K\\)\n" + "\n".join(k_list) + "\n\n"
        else:
            msg += "🔻 KECIL: \\- \\(kosong\\)\n\n"
        if b_list:
            msg += "🔺 BESAR \\(B\\)\n" + "\n".join(b_list) + "\n\n"
        else:
            msg += "🔺 BESAR: \\- \\(kosong\\)\n\n"

        msg += (
            "═════════════════════════════════\n"
            f"💰 Total K: `{format_amount(k_total)}`\n"
            f"💰 Total B: `{format_amount(b_total)}`\n"
            f"👥 Pemain  : `{len(bets)}` orang\n"
            "═════════════════════════════════"
        )

    await send_or_edit(update, msg, create_list_menu())


async def handle_rs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    bets = get_bets(cid)
    if bets:
        # Simpan ke history sebelum reset
        history = get_history(cid)
        history.append({
            "timestamp": datetime.now().isoformat(),
            "bets": bets.copy(),
        })
        # Batasi history 50 entry terakhir
        if len(history) > 50:
            data["history"][cid] = history[-50:]
    data["bets"][cid] = {}
    save_data()
    msg = (
        "╔════════════════════════════════╗\n"
        "║  🗑 RESET LIST - RONDE BARU 🗑║\n"
        "╚════════════════════════════════╝\n\n"
        "✅ List berhasil dikosongkan\\!\n"
        "🎯 Ronde baru dimulai\\.\n\n"
        "📝 Format: `K5`, `B10`, atau `5K`, `10B`"
    )
    await send_or_edit(update, msg, create_main_menu())


async def handle_rk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bets = get_bets(update.effective_chat.id)
    if not bets:
        msg = (
            "╔════════════════════════════════╗\n"
            "║  📊 REKAP TOTAL 📊            ║\n"
            "╚════════════════════════════════╝\n\n"
            "❌ List kosong\\! Tidak ada yang bisa direkap\\."
        )
    else:
        k_total = sum(i["amount"] for i in bets.values() if i["type"] == "K")
        b_total = sum(i["amount"] for i in bets.values() if i["type"] == "B")
        selisih = abs(k_total - b_total)
        k_count = sum(1 for i in bets.values() if i["type"] == "K")
        b_count = sum(1 for i in bets.values() if i["type"] == "B")

        msg = (
            "╔════════════════════════════════╗\n"
            "║  📊 REKAP TOTAL 📊            ║\n"
            "╚════════════════════════════════╝\n\n"
            f"🔻 KECIL: {k_count} pemain → `{format_amount(k_total)}`\n"
            f"🔺 BESAR: {b_count} pemain → `{format_amount(b_total)}`\n"
            "═════════════════════════════════\n\n"
        )
        if k_total > b_total:
            msg += (
                "⚠️ BESAR KURANG\n"
                f"💰 B perlu \\+`{format_amount(selisih)}`\n\n"
                "📌 Tambahkan bet di pihak B\\!"
            )
        elif b_total > k_total:
            msg += (
                "⚠️ KECIL KURANG\n"
                f"💰 K perlu \\+`{format_amount(selisih)}`\n\n"
                "📌 Tambahkan bet di pihak K\\!"
            )
        else:
            msg += "✅ SEIMBANG\\! K dan B sudah seimbang sempurna\\!"

    await send_or_edit(update, msg, create_list_menu())


async def handle_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan total seluruh ronde yang sudah direset."""
    cid = str(update.effective_chat.id)
    history = get_history(cid)
    bets = get_bets(cid)

    # Total ronde selesai + ronde berjalan
    k_total_all = sum(
        i["amount"] for h in history for i in h["bets"].values() if i["type"] == "K"
    ) + sum(i["amount"] for i in bets.values() if i["type"] == "K")
    b_total_all = sum(
        i["amount"] for h in history for i in h["bets"].values() if i["type"] == "B"
    ) + sum(i["amount"] for i in bets.values() if i["type"] == "B")
    total_ronde = len(history) + (1 if bets else 0)

    msg = (
        "╔════════════════════════════════╗\n"
        "║  📈 TOTAL KESELURUHAN 📈       ║\n"
        "╚════════════════════════════════╝\n\n"
        f"🎯 Total Ronde : `{total_ronde}`\n"
        f"🔻 Total K     : `{format_amount(k_total_all)}`\n"
        f"🔺 Total B     : `{format_amount(b_total_all)}`\n"
        f"💵 Grand Total : `{format_amount(k_total_all + b_total_all)}`\n\n"
        "═════════════════════════════════"
    )
    await send_or_edit(update, msg, create_list_menu())


async def handle_perak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    data["perak_mode"][str(update.effective_chat.id)] = True
    save_data()
    msg = (
        "╔════════════════════════════════╗\n"
        "║  💰 MODE PERAK AKTIF 💰        ║\n"
        "╚════════════════════════════════╝\n\n"
        "🎯 Konversi taruhan:\n"
        "B1  = 1\\.000\n"
        "B10 = 10\\.000\n"
        "B50 = 50\\.000\n\n"
        "✅ Setiap bet akan dikali 1000\\."
    )
    await send_or_edit(update, msg, create_main_menu())


async def handle_nonperak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    data["perak_mode"][str(update.effective_chat.id)] = False
    save_data()
    msg = (
        "╔════════════════════════════════╗\n"
        "║  💵 MODE NON-PERAK AKTIF 💵   ║\n"
        "╚════════════════════════════════╝\n\n"
        "🎯 Taruhan nilai asli:\n"
        "B1  = 1\n"
        "B10 = 10\n"
        "B50 = 50\n\n"
        "✅ Bet dihitung nilai aslinya\\."
    )
    await send_or_edit(update, msg, create_main_menu())


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    bets = get_bets(cid)
    history = get_history(cid)
    msg = (
        "╔════════════════════════════════╗\n"
        "║  ⚙️ STATUS BOT ⚙️            ║\n"
        "╚════════════════════════════════╝\n\n"
        f"📊 Aktif       : {'✅ YA' if is_active(cid) else '❌ TIDAK'}\n"
        f"💰 Mode        : {'PERAK' if is_perak(cid) else 'NON-PERAK'}\n"
        f"📋 Bet ronde   : `{len(bets)}` pemain\n"
        f"📈 Total ronde : `{len(history)}` selesai\n"
        f"👥 Admin        : `{len(ADMIN_IDS)}` orang\n"
        f"🆔 Chat ID      : `{cid}`"
    )
    await send_or_edit(update, msg, create_main_menu())


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "╔════════════════════════════════╗\n"
        "║  📖 PANDUAN LENGKAP 📖        ║\n"
        "╚════════════════════════════════╝\n\n"
        "🔘 TOMBOL UTAMA\n"
        "✅ ON Bot → Aktifkan bot\n"
        "❌ OFF Bot → Matikan bot\n"
        "📋 LIST → Lihat daftar bet\n"
        "🗑 RESET → Kosongkan list\n"
        "📊 REKAP → Lihat perhitungan\n"
        "📈 TOTAL → Total semua ronde\n"
        "💰 PERAK → Mode x1000\n"
        "💵 NON-PERAK → Mode normal\n"
        "⚙️ STATUS → Cek status bot\n\n"
        "📝 FORMAT BET\n"
        "`K5`  = Kecil 5\n"
        "`B10` = Besar 10\n"
        "`5K`  = Kecil 5 \\(dibalik\\)\n"
        "`10B` = Besar 10 \\(dibalik\\)\n\n"
        "⚙️ COMMAND \\(SLASH\\)\n"
        "/menu → Buka menu utama\n"
        "/on → Aktifkan bot\n"
        "/off → Matikan bot\n"
        "/list → Daftar bet\n"
        "/rs → Reset ronde\n"
        "/rk → Rekap ronde\n"
        "/total → Total keseluruhan\n"
        "/perak → Mode perak\n"
        "/nonperak → Mode non-perak\n"
        "/status → Status bot\n"
        "/del \\@user → Hapus bet user\n"
        "/del \\-reply → Hapus bet \\(reply\\)\n"
        "/cancel → Batalkan bet sendiri\n"
        "/alias \\<nama\\> → Set nama alias\n"
        "/alias \\- → Hapus alias\n"
        "/cmd → Bantuan \\(ini\\)\n"
        "/help → Bantuan \\(sama\\)\n\n"
        "👨💼 Hanya admin yang bisa gunakan command kelola\\!"
    )
    await send_or_edit(update, msg, create_help_menu())


# ============================================================
# COMMAND TAMBAHAN: /del, /cancel, /alias
# ============================================================

async def handle_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hapus bet user tertentu. Admin only.
    Cara pakai:
      /del @username    → hapus berdasarkan username
      /del <reply>      → hapus user yang di-reply
    """
    if not await require_admin(update):
        return
    cid = str(update.effective_chat.id)
    bets = get_bets(cid)

    # Jika reply ke pesan user
    if update.effective_message.reply_to_message:
        target_user = update.effective_message.reply_to_message.from_user
        if target_user is None:
            await update.effective_message.reply_text("❌ Tidak bisa ambil info user\\.")
            return
        target_id = str(target_user.id)
    else:
        # Ambil argumen pertama (username atau ID)
        if not context.args:
            await update.effective_message.reply_text(
                "📌 Cara pakai:\n"
                "• `/del @username`\n"
                "• Reply pesan user lalu `/del`"
            )
            return
        arg = context.args[0].lstrip("@")
        # Cari berdasarkan username
        found_id = None
        for uid, info in bets.items():
            uname = (info.get("username") or "").lstrip("@").lower()
            if uname == arg.lower():
                found_id = uid
                break
        if not found_id:
            await update.effective_message.reply_text(f"❌ User `{arg}` tidak ditemukan di list\\.")
            return
        target_id = found_id

    if target_id not in bets:
        await update.effective_message.reply_text("❌ User ini tidak ada di list\\.")
        return

    deleted = bets.pop(target_id)
    save_data()
    await update.effective_message.reply_text(
        f"✅ Bet {md(deleted['name'])} \\({deleted['type']}{deleted['amount']}\\) dihapus\\!"
    )


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Member batalkan bet sendiri. Bukan admin juga bisa."""
    cid = str(update.effective_chat.id)
    if not is_active(cid):
        await update.effective_message.reply_text("❌ Bot sedang mati\\.")
        return
    bets = get_bets(cid)
    uid = str(update.effective_user.id)
    if uid not in bets:
        await update.effective_message.reply_text("❌ Kamu belum pasang bet\\.")
        return
    deleted = bets.pop(uid)
    save_data()
    await update.effective_message.reply_text(
        f"✅ Bet kamu \\({deleted['type']}{format_amount(deleted['amount'])}\\) dibatalkan\\."
    )


async def handle_alias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set alias nama. Pakai: /alias <nama> atau /alias - untuk hapus."""
    cid = str(update.effective_chat.id)
    uid = str(update.effective_user.id)
    aliases = get_aliases(cid)

    if not context.args:
        await update.effective_message.reply_text(
            "📌 Cara pakai:\n"
            "• `/alias Budi` → set nama jadi Budi\n"
            "• `/alias -` → hapus alias \\(kembali ke nama asli\\)"
        )
        return

    arg = " ".join(context.args).strip()
    if arg == "-":
        if uid in aliases:
            del aliases[uid]
            save_data()
            await update.effective_message.reply_text("✅ Alias kamu dihapus\\.")
        else:
            await update.effective_message.reply_text("ℹ️ Kamu belum punya alias\\.")
        return

    # Batasi panjang alias
    if len(arg) > 30:
        await update.effective_message.reply_text("❌ Alias maksimal 30 karakter\\.")
        return

    aliases[uid] = arg
    save_data()
    await update.effective_message.reply_text(f"✅ Alias kamu: {md(arg)}")


# ============================================================
# CALLBACK QUERY (untuk tombol inline)
# ============================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return
    query = update.callback_query.data

    handler_map = {
        "cmd_menu": handle_menu,
        "cmd_on": handle_on,
        "cmd_off": handle_off,
        "cmd_list": handle_list,
        "cmd_rs": handle_rs,
        "cmd_rk": handle_rk,
        "cmd_total": handle_total,
        "cmd_perak": handle_perak,
        "cmd_nonperak": handle_nonperak,
        "cmd_status": handle_status,
        "cmd_help": handle_help,
    }
    handler = handler_map.get(query)
    if handler:
        await handler(update, context)


# ============================================================
# HANDLER TEXT BET (K5, B10, 5K, 10B)
# ============================================================

async def handle_bet_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_message.text:
        return
    if not is_active(update.effective_chat.id):
        return

    text = update.effective_message.text.strip()
    # Abaikan jika diawali / atau .
    if text.startswith("/") or text.startswith("."):
        return

    bet_type, raw = parse_bet(text)
    if bet_type is None:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    name = await get_display_name(user, chat_id)
    uname = f"@{user.username}" if user and getattr(user, "username", None) else ""

    get_bets(chat_id)[str(user.id)] = {
        "name": name,
        "username": uname,
        "type": bet_type,
        "amount": calc_amount(raw, is_perak(chat_id)),
    }
    save_data()
    display_raw = int(raw) if raw == int(raw) else raw
    emoji = "🔻" if bet_type == "K" else "🔺"
    msg = f"{emoji} {md(name)} → `{bet_type}{display_raw}`"
    await update.effective_message.reply_text(msg)


# ============================================================
# AUTO-SAVE BACKGROUND TASK
# ============================================================

async def autosave_loop():
    """Backup otomatis setiap interval."""
    while True:
        await asyncio.sleep(AUTOSAVE_INTERVAL)
        save_data()


# ============================================================
# MAIN: JALANKAN BOT
# ============================================================

async def post_init(application):
    """Print info saat bot siap."""
    me = await application.bot.get_me()
    print("=" * 55)
    print(f"  🤖 UBOT LIST - STARTED")
    print(f"  👤 Bot   : @{me.username}")
    print(f"  🆔 Bot ID: {me.id}")
    print(f"  👑 Admin : {ADMIN_IDS}")
    print("=" * 55)
    print("  📌 Perintah tersedia:")
    print("     /menu /on /off /list /rs /rk /total")
    print("     /perak /nonperak /status /del /cancel")
    print("     /alias /cmd /help")
    print("=" * 55)


async def run_bot():
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Daftar semua command slash
    application.add_handler(CommandHandler("menu", handle_menu))
    application.add_handler(CommandHandler("start", handle_menu))
    application.add_handler(CommandHandler("on", handle_on))
    application.add_handler(CommandHandler("off", handle_off))
    application.add_handler(CommandHandler("list", handle_list))
    application.add_handler(CommandHandler("rs", handle_rs))
    application.add_handler(CommandHandler("rk", handle_rk))
    application.add_handler(CommandHandler("total", handle_total))
    application.add_handler(CommandHandler("perak", handle_perak))
    application.add_handler(CommandHandler("nonperak", handle_nonperak))
    application.add_handler(CommandHandler("status", handle_status))
    application.add_handler(CommandHandler("cmd", handle_help))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("del", handle_del))
    application.add_handler(CommandHandler("cancel", handle_cancel))
    application.add_handler(CommandHandler("alias", handle_alias))

    # Callback tombol inline
    application.add_handler(CallbackQueryHandler(handle_callback, pattern=r"^cmd_"))

    # Pesan teks biasa → cek apakah format bet
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bet_text)
    )

    # Jalankan autosave
    application.job_queue.run_repeating(
        lambda _ctx: None,  # dummy, autosave di handle_bet_text juga
        interval=AUTOSAVE_INTERVAL,
        first=AUTOSAVE_INTERVAL,
    )

    print("=" * 55)
    print("  🚀 UBOT LIST - STARTING...")
    print("=" * 55)

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Background autosave
    asyncio.create_task(autosave_loop())

    await application.updater.wait_until_stopped()
    await application.stop()
    await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        save_data()
        print("\n\n👋 Bot dihentikan. Data tersimpan. Sampai jumpa!")
    except Exception as e:
        traceback.print_exc()
        print(f"\n❌ Error: {e}")
