# Native Speech Generation untuk NVDA

**Penulis:** Muhammad Gagah [muha.aku@gmail.com](mailto:muha.aku@gmail.com)

Native Speech Generation adalah add-on NVDA yang mengintegrasikan **Google Gemini AI** untuk menghasilkan ucapan berkualitas tinggi dengan suara yang terdengar alami langsung di NVDA.
Add-on ini menyediakan antarmuka yang bersih dan sepenuhnya dapat diakses untuk mengubah teks menjadi audio, serta mendukung **narasi pembicara tunggal** maupun **dialog multi-pembicara yang dinamis**.

Add-on ini dirancang untuk alur kerja yang lancar, interaksi yang mengutamakan aksesibilitas, dan kontrol suara yang fleksibel, sehingga cocok untuk narasi, dialog, serta produksi konten audio.

---

## Fitur

### Pembuatan Ucapan Berkualitas Tinggi

* Pilih antara:
  * **Gemini Flash**: kualitas standar, pembuatan cepat, dan latensi rendah.
  * **Gemini Pro**: kualitas premium dengan suara yang lebih realistis (model berbayar).

### Mode Pembicara Tunggal dan Multi-Pembicara

* **Narasi pembicara tunggal** untuk text-to-speech standar.
* **Mode multi-pembicara (2 pembicara)** untuk dialog dengan suara yang berbeda.

### Kontrol Suara Lanjutan

* **Penamaan pembicara**
  Tetapkan nama khusus, misalnya *Budi* atau *Siti*, dalam mode multi-pembicara.
  AI akan memetakan suara secara otomatis berdasarkan nama pembicara di naskah.
* **Instruksi gaya**
  Berikan petunjuk seperti *"Bicaralah dengan nada ceria"* atau *"Narasi dengan tenang"* untuk mengarahkan cara penyampaian.
* **Kontrol temperatur**
  Sesuaikan variasi dan kreativitas hasil:
  * Nilai lebih rendah -> ucapan lebih stabil dan mudah diprediksi.
  * Nilai lebih tinggi -> ucapan lebih ekspresif dan bervariasi.

### Antarmuka yang Bersih dan Dapat Diakses

* Sepenuhnya dapat diakses dengan pembaca layar.
* Opsi lanjutan ditempatkan di panel yang dapat diciutkan agar dialog utama tetap sederhana dan fokus.

### Alur Kerja yang Lancar

* Audio diputar secara otomatis setelah pembuatan selesai.
* Audio yang dihasilkan dapat diputar ulang atau disimpan sebagai file `.wav` berkualitas tinggi.
* Dirancang untuk meminimalkan hambatan selama pembuatan dan pemutaran berulang.

### Pemuatan Suara Cerdas dan Cache

* Suara yang tersedia diambil secara dinamis dari API Gemini.
* Data suara disimpan dalam cache selama **24 jam** untuk mengurangi panggilan API dan mempercepat proses awal.

### Bicara dengan AI (Percakapan Langsung)

* **Obrolan suara real-time**: lakukan percakapan lisan yang alami dan berlatensi rendah dengan Gemini.
* **Grounding dengan Google Search**: memungkinkan AI mengakses informasi real-time dari web selama percakapan.
* **Dapat diinterupsi**: Anda dapat memotong pembicaraan AI kapan saja dengan berbicara atau menekan "Hentikan percakapan".
* **Dapat disesuaikan**: menggunakan suara dan instruksi gaya yang Anda pilih.
* **Kontrol tingkat penalaran**: pilih `Tanpa Penalaran`, `Rendah`, `Sedang`, atau `Tinggi` sesuai kedalaman penalaran yang Anda inginkan.
* **Kontinuitas setelah koneksi ulang**: konteks percakapan terbaru dipulihkan secara otomatis setelah tersambung kembali, tanpa toggle memori terpisah.
* **Streaming lebih stabil**: perilaku reconnect yang lebih baik (backoff + retry) dan buffering audio adaptif agar lebih tangguh pada jaringan yang tidak stabil.

---

## Persyaratan

* NVDA (disarankan menggunakan versi terbaru).
* Koneksi internet aktif.
* **Kunci API Google Gemini** yang valid.

---

## Instalasi

1. Unduh paket add-on terbaru dari
   **halaman Rilis:**
   [https://github.com/MuhammadGagah/native-speech-generation/releases](https://github.com/MuhammadGagah/native-speech-generation/releases)
2. Instal seperti add-on NVDA standar lainnya.
3. Mulai ulang NVDA saat diminta.

---

## Pengaturan Kunci API (Wajib)

1. Buat kunci API dari **Google AI Studio**:
   [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Buka NVDA lalu masuk ke:
   **Menu NVDA -> Alat -> Native Speech Generation**
3. Klik **"Pengaturan Kunci API"**.
4. Ini akan membuka Pengaturan NVDA langsung di kategori *Native Speech Generation*.
5. Tempelkan **kunci API Gemini** Anda ke dalam kolom *GEMINI API Key*.
6. Klik **OK** untuk menyimpan.

Kunci yang disimpan diamankan menggunakan **Windows DPAPI**, sehingga nilai terenkripsi tidak dapat didekripsi di komputer Windows lain atau akun pengguna lain.

Untuk deployment tingkat lanjut, Anda juga dapat menyediakan kunci melalui variabel lingkungan **`GEMINI_API_KEY`**. Add-on akan menggunakannya secara otomatis saat tidak ada kunci tersimpan.

---

## Cara Menggunakan

Buka dialog dengan:

* **NVDA+Control+Shift+G**, atau
* **Menu NVDA -> Alat -> Native Speech Generation**

### Elemen Antarmuka Utama

* **Teks untuk dikonversi**
  Masukkan atau tempel teks yang ingin Anda ubah menjadi ucapan.
* **Instruksi gaya (opsional)**
  Berikan panduan untuk nada, emosi, atau cara penyampaian.
* **Pilih model**
  * Flash (kualitas standar)
  * Pro (kualitas tinggi)
* **Mode pembicara**
  * Pembicara tunggal
  * Multi-pembicara (2)

---

## Menghasilkan Ucapan

### Mode Pembicara Tunggal

1. Pilih **Pembicara tunggal**.
2. Pilih suara dari daftar *Pilih Suara*.
3. Masukkan teks Anda.
4. Tambahkan instruksi gaya bila diperlukan.
5. Klik **Hasilkan Ucapan**.
6. Audio akan diputar otomatis setelah proses selesai.

---

### Mode Multi-Pembicara

1. Pilih **Multi-pembicara (2)**.
2. Untuk setiap pembicara:
   * Masukkan **Nama Pembicara** yang unik.
   * Pilih **Suara** yang berbeda.
3. Format teks sehingga setiap baris diawali nama pembicara, lalu diikuti tanda titik dua.

**Contoh:**

```
Alice: Hai Bob, apa kabar hari ini?
Bob: Aku baik-baik saja, Alice! Cuacanya luar biasa.
```

4. Klik **Hasilkan Ucapan**.
   Suara akan dipetakan secara otomatis berdasarkan nama pembicara.

---

## Bicara dengan AI (Mode Langsung)

Rasakan percakapan suara dua arah yang alami dengan Gemini.

1. Atur **Suara** dan **Instruksi Gaya** yang diinginkan di dialog utama.
   *(Catatan: Bicara dengan AI saat ini hanya mendukung mode Pembicara Tunggal.)*
2. Klik **Bicara dengan AI**.
3. Di jendela baru:
   * **Mulai percakapan**: memulai sesi. Bicaralah ke mikrofon Anda.
   * **Hentikan percakapan**: mengakhiri sesi.
   * **Grounding dengan Google Search**: centang opsi ini untuk mengizinkan Gemini menelusuri web guna mencari jawaban, misalnya berita atau cuaca terkini.
     * *Catatan: opsi ini disembunyikan saat percakapan sedang aktif. Hentikan percakapan untuk mengubahnya.*
   * **Tingkat penalaran**: pilih `Tanpa Penalaran`, `Rendah`, `Sedang`, atau `Tinggi`.
   * **Tombol mikrofon**: membisukan atau mengaktifkan mikrofon Anda.
   * **Volume**: menyesuaikan volume pemutaran AI.

---

## Pengaturan Lanjutan

* Aktifkan **Pengaturan Lanjutan (Temperatur)** untuk menampilkan slider.
* **Rentang temperatur**:
  * `0.0` -> hasil paling deterministik dan stabil.
  * `1.0` -> keseimbangan default.
  * `2.0` -> hasil paling kreatif dan bervariasi.

---

## Ringkasan Tombol

* **Hasilkan Ucapan** - Memulai pembuatan ucapan.
* **Putar** - Memutar ulang audio terakhir yang dibuat.
* **Bicara dengan AI** - Membuka antarmuka percakapan suara real-time.
* **Simpan Audio** - Menyimpan audio terakhir sebagai file `.wav`.
* **Pengaturan Kunci API** - Membuka konfigurasi add-on di Pengaturan NVDA.
* **Lihat suara di AI Studio** - Membuka Google AI Studio di browser.
* **Tutup** - Menutup dialog, atau tekan `Escape`.

---

## Gestur Input

Dapat disesuaikan melalui:
**Menu NVDA -> Preferensi -> Gestur Input -> Native Speech Generation**

Gestur default:

* **NVDA+Control+Shift+G** - Membuka dialog Native Speech Generation.

---

## Panduan Pengembangan dan Kontribusi

Jika Anda ingin mengembangkan atau memodifikasi add-on ini, ikuti langkah-langkah berikut.

### Pengaturan Lingkungan

* **Python yang sesuai dengan runtime NVDA target**
  * Gunakan **Python 3.13 64-bit** untuk NVDA 2026.1 dan yang lebih baru.
  * Gunakan **Python 3.11 32-bit** hanya untuk paket dependensi NVDA lama yang masih didukung.
* **uv** untuk toolchain build dan lint yang dipin.

  ```
  uv sync
  uv run pre-commit run --all-files
  uv run scons
  uv run scons pot
  ```

  SCons 4.10.1, Markdown 3.10, Ruff 0.14.10, Pyright 1.1.407, dan tool build lainnya diinstal dari `uv.lock`.
* **GNU Gettext Tools** (opsional, disarankan untuk lokalisasi)
  * Biasanya sudah terpasang di Linux/Cygwin.
  * Windows: [https://gnuwin32.sourceforge.net/downlinks/gettext.php](https://gnuwin32.sourceforge.net/downlinks/gettext.php)
### Dependensi Tambahan

Untuk pengembangan lokal saja, instal dependensi audio untuk Talk With AI langsung ke jalur pustaka add-on menggunakan versi dan arsitektur Python yang sesuai dengan runtime NVDA yang diuji:

```
python.exe -m pip install google-genai pyaudio --target "D:/myAdd-on/Native-Speech-Generation/addon/globalPlugins/NativeSpeechGeneration/lib"
```

Sesuaikan jalur tersebut dengan direktori sumber add-on di komputer Anda.

Untuk implementasi Talk With AI versi audio saat ini, Anda tidak memerlukan `opencv-python`, `pillow`, atau `mss`.

Untuk paket rilis, add-on mengunduh arsip dependensi terverifikasi terbaru berdasarkan versi NVDA yang berjalan:

* `lib.zip` untuk NVDA 2025.3.3 dan build lama yang masih didukung.
* `lib64.zip` untuk NVDA 2026.1 dan yang lebih baru.

Add-on membaca data SHA-256 dari rilis dependensi GitHub terbaru, menggunakan digest asset rilis atau file checksum. Checksum bawaan yang disetujui hanya disimpan sebagai fallback untuk instalasi pertama ketika lookup rilis terbaru gagal. Reinstall library manual mewajibkan rilis terbaru yang terverifikasi. Folder hasil ekstraksi selalu diinstal sebagai `addon/globalPlugins/NativeSpeechGeneration/lib`.

Lalu salin file berikut dari instalasi Python Anda ke:

```
addon/globalPlugins/NativeSpeechGeneration/lib
```

* Folder `zoneinfo`
* File `secrets.py`

---

## Berkontribusi

Kontribusi, saran, dan laporan bug sangat kami harapkan.

* Buka **Issue** untuk bug atau permintaan fitur.
* Kirim **Pull Request** untuk kontribusi kode.

**Kontak**

* Email: `muha.aku@gmail.com`
* GitHub: [https://github.com/MuhammadGagah](https://github.com/MuhammadGagah)
