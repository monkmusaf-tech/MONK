# 🦌 HuntGame Bot - Telegram Hunting Game

Bot game berburu Telegram lengkap dengan 40+ hewan, sistem survival, market P2P, museum trofi, dan admin panel lengkap.

---

## 🚀 CARA DEPLOY KE RAILWAY (Tanpa Terminal!)

### Step 1: Siapkan Bot Token
1. Buka Telegram, cari **@BotFather**
2. Ketik `/newbot` dan ikuti instruksinya
3. Simpan **BOT TOKEN** yang diberikan

### Step 2: Cari ID Admin
1. Cari **@userinfobot** di Telegram
2. Kirim pesan apapun
3. Catat **ID** yang ditampilkan

### Step 3: Upload ke GitHub
1. Buat repository baru di [github.com](https://github.com)
2. Klik **"uploading an existing file"**
3. Upload **SEMUA FILE** dari folder ini
4. Klik **"Commit changes"**

### Step 4: Deploy ke Railway
1. Buka [railway.app](https://railway.app)
2. Login dengan GitHub
3. Klik **"New Project"** → **"Deploy from GitHub repo"**
4. Pilih repository yang baru dibuat
5. Tunggu build selesai

### Step 5: Set Environment Variables di Railway
Klik tab **"Variables"** di Railway, tambahkan:

| Variable | Value | Keterangan |
|----------|-------|------------|
| `BOT_TOKEN` | `1234567890:ABCdef...` | Token dari BotFather |
| `ADMIN_IDS` | `123456789` | ID Telegram kamu |
| `CHANNEL_ID` | `-1001234567890` | ID Channel jual beli (opsional) |
| `GROUP_ID` | `-1001234567891` | ID Group official (opsional) |
| `GROUP_LINK` | `https://t.me/xxx` | Link group (opsional) |

### Step 6: Redeploy
Setelah set variables, klik **"Deploy"** di Railway.

**Bot siap dimainkan! Kirim `/start` ke bot kamu.**

---

## 📊 DATABASE & DATA PLAYER

✅ **Data player TIDAK AKAN RESET** saat update GitHub karena:
- Database SQLite disimpan di volume Railway (`data/huntgame.db`)
- File database tidak ada di GitHub (sudah di `.gitignore`)
- Setiap update kode = data tetap aman

---

## 🎮 FITUR LENGKAP

### Untuk Player:
- 🦌 **40+ Hewan** dari Common sampai Boss
- 🗺️ **6 Map** dengan level requirement
- 🔫 **10 Senjata** dari Ketapel sampai Ultima Blade
- 🏪 **Market** - Jual, cek harga dinamis, P2P Trading
- 🏠 **Sistem Survival** - Hunger/Thirst/Stamina/Rest
- 🍳 **Crafting** - Masak dari hasil buruan
- 🏛️ **Museum** - Koleksi trofi 40+ hewan
- 🎯 **10 Achievement** dengan reward koin
- 🏆 **Leaderboard** - Terkaya, level, kill, penghasilan
- 💎 **Top-Up** dengan sistem verifikasi manual

### Untuk Admin:
- 📊 **Dashboard** - Statistik realtime
- 🦌 **Kelola Hewan** - Tambah/edit/hapus + upload foto
- 🔫 **Kelola Senjata** - Full CRUD
- 🗺️ **Toggle Map** - On/off per map
- 💰 **Atur Ekonomi** - Harga, multiplier, event 2x EXP/coin
- 👤 **Manajemen Player** - Beri koin, ban, set level, broadcast
- 👹 **Spawn Boss** - Manual spawn dengan HP & reward custom
- 💳 **Verifikasi Topup** - Approve/reject dengan notif otomatis
- 📤 **Export CSV** - Riwayat transaksi
- 📸 **Upload Foto** - Foto per menu dan per hewan
- 📋 **Log & Monitoring** - Deteksi cheat otomatis
- 🛡️ **Sub-Admin** - 5 role (Super Admin, Konten, Keuangan, Moderator, CS)

---

## 📁 STRUKTUR FILE

```
hunting-bot/
├── main.py              ← Entry point (jalankan ini)
├── bot.py               ← Entry point alternatif
├── requirements.txt     ← Library Python
├── Procfile             ← Config Railway
├── railway.json         ← Config Railway
├── .env.example         ← Template environment variables
├── .gitignore           ← File yang tidak di-upload
│
├── config/
│   └── settings.py      ← Konfigurasi bot
│
├── database/
│   ├── db.py            ← Inisialisasi & seed data
│   └── queries.py       ← Semua fungsi database
│
├── handlers/            ← Handler untuk player
│   ├── start.py         ← Menu utama & registrasi
│   ├── hunt.py          ← Sistem berburu
│   ├── market.py        ← Market & P2P
│   ├── home.py          ← Survival & crafting
│   ├── museum.py        ← Museum & achievement
│   ├── weapons.py       ← Senjata
│   ├── inventory.py     ← Inventori
│   ├── profile.py       ← Profil player
│   ├── leaderboard.py   ← Leaderboard
│   └── conversations.py ← Input handler universal
│
├── admin/               ← Handler untuk admin
│   ├── dashboard.py     ← Dashboard & statistik
│   ├── manage_content.py← Kelola konten
│   ├── economy.py       ← Harga & ekonomi
│   ├── players.py       ← Manajemen player
│   ├── events.py        ← Event & boss
│   ├── transactions.py  ← Transaksi & topup
│   ├── bot_settings.py  ← Pengaturan bot
│   ├── logs.py          ← Log & monitoring
│   └── roles.py         ← Admin & role
│
└── utils/
    └── helpers.py       ← Fungsi utilitas
```

---

## 🔧 PERINTAH ADMIN

Setelah deploy, ketik `/admin` di chat bot untuk akses panel admin.

---

## ❓ FAQ

**Q: Data player reset kalau update kode?**
A: TIDAK. Database disimpan terpisah di Railway volume, tidak terpengaruh update kode.

**Q: Bisa tambah hewan baru tanpa coding?**
A: Ya! Gunakan menu Admin → Kelola Konten → Hewan → Tambah Hewan Baru.

**Q: Bisa ganti foto setiap menu?**
A: Ya! Admin → Pengaturan Bot → Pengaturan Foto. Upload foto langsung di chat.

**Q: Cara verifikasi topup player?**
A: Admin → Transaksi → Verifikasi Top-Up. Klik Approve/Reject.

---

*HuntGame Bot v1.0.0 | Made with ❤️*
