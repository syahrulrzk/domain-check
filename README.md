# Domain-check
## Langkah-langkah Menjalankan Bot di Background dengan screen

### Kloning Repositori Git
Pertama, kita akan mengunduh kode bot dari repositori Git.

```
git clone https://github.com/syahrulrzk/domain-check.git
```
```
cd domain-check
```
### Buat dan Aktifkan Lingkungan Virtual (venv)
Ini adalah praktik terbaik untuk mengisolasi dependensi proyekmu.

```
python3 -m venv venv
```
Catatan: Gunakan python3 jika python default kamu masih Python 2. Jika tidak, cukup gunakan python -m venv venv.

Aktifkan venv:

```
source venv/bin/activate
```
Untuk Windows (jika kamu melakukan ini di WSL/Git Bash):


Setelah diaktifkan, kamu akan melihat (venv) di awal prompt terminalmu, menandakan bahwa kamu berada di lingkungan virtual.

### Instal Dependensi dari requirements.txt
Sekarang, instal semua library yang dibutuhkan bot dari file requirements.txt.

```
pip install -r requirements.txt
```
Jalankan Bot Menggunakan screen

screen memungkinkan bot tetap berjalan bahkan setelah kamu menutup terminal atau koneksi SSH.

```
screen -S bot_domain-check
```

Jalankan Bot di dalam Sesi screen:
Setelah perintah di atas, kamu akan masuk ke dalam sesi screen yang baru (terminal akan terlihat "bersih"). Sekarang, jalankan bot kamu:

```
python bot.py
```
Lepaskan (Detach) Sesi screen:
Setelah bot mulai berjalan (kamu mungkin melihat output bot di terminal), kamu bisa melepaskan sesi screen ini tanpa menghentikan bot. Tekan:

<b>Ctrl+A lalu D</b> (tekan Ctrl+A bersamaan, lalu lepaskan, lalu tekan D).

Kamu akan kembali ke terminal utama dan melihat pesan seperti [detached from ...bot_session]. Ini berarti bot kamu sekarang berjalan di background.

Perintah Berguna untuk screen:
Melihat Daftar Sesi screen yang Aktif:
```
screen -ls
```
Melampirkan Kembali (Reattach) ke Sesi screen:
Jika kamu ingin kembali melihat output bot atau menghentikannya:
```
screen -r bot_domain_check
```
