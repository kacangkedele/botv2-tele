# 🤖 UBOT LIST - Telegram Bot Lengkap

Saya akan buatkan bot Telegram lengkap dengan semua fitur menggunakan perintah `/` (slash command). Berikut struktur file lengkapnya:

## 📁 Struktur Project

```
ubotlist/
├── config.py
├── ubotlist.py
├── requirements.txt
├── data.json
└── README.md
```

---                        
---

## 5. `README.md`

```markdown
# 🤖 UBOT LIST - Bot Taruhan K/B Telegram

Bot Telegram untuk mencatat taruhan **Kecil (K)** / **Besar (B)** dengan mode PERAK (x1000) atau NON-PERAK.

## ✨ Fitur

- ✅ Aktif/Matikan bot per grup
- 📋 List taruhan otomatis (K/B dipisah)
- 🗑 Reset ronde + simpan ke history
- 📊 Rekap ronde + selisih otomatis
- 📈 Total seluruh ronde (history)
- 💰 Mode PERAK (B1 = 1.000) / NON-PERAK
- ⚙️ Status bot lengkap
- 🗑 `/del` hapus bet user (admin)
- ❌ `/cancel` hapus bet sendiri (member)
- 🔖 `/alias` ganti nama tampil
- 💾 Auto-save setiap 30 detik
- 📱 Inline keyboard di semua menu

## 🚀 Cara Install

```bash
# 1. Clone / download file
# 2. Install dependency
pip install -r requirements.txt

# 3. Edit config.py — isi BOT_TOKEN & ADMIN_IDS
# 4. Jalankan
python ubotlist.py
```

## 📋 Daftar Perintah (Slash `/`)

| Command | Fungsi | Akses |
|---------|--------|-------|
| `/start` `/menu` | Buka menu utama | Admin |
| `/on` | Aktifkan bot | Admin |
| `/off` | Matikan bot | Admin |
| `/list` | Lihat daftar bet | All |
| `/rs` | Reset ronde | Admin |
| `/rk` | Rekap ronde ini | All |
| `/total` | Total semua ronde | All |
| `/perak` | Mode PERAK | Admin |
| `/nonperak` | Mode NON-PERAK | Admin |
| `/status` | Cek status bot | Admin |
| `/del @user` | Hapus bet user | Admin |
| `/del` (reply) | Hapus bet (reply) | Admin |
| `/cancel` | Batalkan bet sendiri | Member |
| `/alias <nama>` | Set nama alias | Member |
| `/alias -` | Hapus alias | Member |
| `/cmd` `/help` | Bantuan | All |

## 📝 Format Pasang Bet

```
K5    → Kecil 5
B10   → Besar 10
5K    → Kecil 5 (dibalik)
10B   → Besar 10 (dibalik)
```

Mode PERAK: angka × 1000 (jadi `B5 = 5.000`)
Mode NON-PERAK: angka apa adanya (`B5 = 5`)

## ⚙️ Konfigurasi

Edit `config.py`:

```python
BOT_TOKEN = "token_dari_botfather"
ADMIN_IDS = [123456789]
DATA_FILE = "data.json"
```

## 🐛 Troubleshooting

- **Bot tidak respon:** pastikan `BOT_TOKEN` benar & bot sudah di-start di grup
- **Bukan admin:** cek `ADMIN_IDS` di `config.py` (gunakan ID numerik)
- **Data hilang:** cek file `data.json`, backup berkala
```

---

## 🎯 Ringkasan Fitur Lengkap

### ✅ Command Slash (semua `/`)

| Command | Deskripsi |
|---------|-----------|
| `/start` atau `/menu` | Menu utama dengan tombol |
| `/on` | Aktifkan bot |
| `/off` | Matikan bot |
| `/list` | Lihat list bet ronde ini |
| `/rs` | Reset list (ronde baru) |
| `/rk` | Rekap + selisih K/B |
| `/total` | Total seluruh ronde (history) |
| `/perak` | Mode PERAK (×1000) |
| `/nonperak` | Mode NON-PERAK |
| `/status` | Status bot |
| `/del @user` | Hapus bet user (admin) |
| `/cancel` | Batalkan bet sendiri |
| `/alias <nama>` | Set alias nama |
| `/cmd` atau `/help` | Bantuan lengkap |

### 🆕 Fitur Baru vs Versi Lama

1. **`/total`** — total seluruh ronde yang sudah direset
2. **`/status`** — cek status lengkap bot
3. **`/del`** — hapus bet user (admin)
4. **`/cancel`** — member bisa batal bet sendiri
5. **`/alias`** — set nama tampil custom
6. **Auto-save** — backup tiap 30 detik
7. **History** — ronde selesai disimpan otomatis
8. **Tombol `📈 TOTAL`** di menu inline
9. **Tombol `⚙️ STATUS`** di menu inline

Tinggal isi `BOT_TOKEN` dan `ADMIN_IDS` di `config.py`, lalu jalankan `python ubotlist.py` — bot langsung siap pakai! 🚀
