# ♟️ Yapay Zeka Destekli Satranç Motoru (MTU-II Projesi)
Bu proje, **Erciyes Üniversitesi Mekatronik Mühendisliği** bölümü **Mekatronik Tasarım Uygulamaları-II** dersi kapsamında geliştirilmiş, grafik arayüze sahip yapay zeka destekli bir satranç analiz motorudur.

## 👨‍💻 Proje Bilgileri

* **Ders:** Mekatronik Tasarım Uygulamaları-II
* **Hazırlayan:** Ahmet Buğra KURTBOĞAN (1031110872)
* **Danışman:** Burak ULU
* **Dönem:** 2025 Güz

## 🚀 Özellikler

Proje, FIDE satranç kurallarını eksiksiz uygulayan ve kullanıcı dostu bir arayüz sunan kapsamlı bir masaüstü uygulamasıdır.

* **Gelişmiş Yapay Zeka:** Minimax algoritması ve Alpha-Beta Budama (Pruning) optimizasyonu kullanılarak geliştirilmiştir.
* **Akıllı Arama:** Yinelemeli Derinleşme (Iterative Deepening) sayesinde zamanı verimli kullanır ve süre bitiminde en iyi hamleyi oynar.
* **Tam Kural Seti:** Rok (Castling), Geçerken Alma (En Passant) ve Piyon Terfisi (Promotion) dahil tüm kurallar geçerlidir.
* **Kullanıcı Arayüzü (GUI):** PyQt6 ile geliştirilen modern arayüz; hamle ipuçları, tehdit uyarıları ve son hamle vurgusu içerir.
* **Analiz Araçları:**
    * Sağ tık ile ok çizme özelliği.
    * Anlık materyal ve pozisyon değerlendirmesi.
    * Oyun sonunda PGN (Portable Game Notation) çıktısı üretme.
* **Oyun Modları:** Bot'a Karşı (PvE) ve Arkadaşla Oyna (PvP/Analiz).
* **Zaman Kontrolü:** Bullet, Blitz, Rapid ve Klasik süre modları.
## 🛠️ Kurulum ve Çalıştırma

Projeyi yerel bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

1.  **Repoyu klonlayın:**
    ```bash
    ```

2.  **Gereksinimleri yükleyin:**
    Proje `PyQt6` kütüphanesine ihtiyaç duyar.
    ```bash
    pip install PyQt6
    ```

3.  **Uygulamayı başlatın:**
    ```bash
    python final_oyun.py
    ```

## 🧠 Algoritma Mimarisi

Bu satranç motoru, karar verme sürecinde aşağıdaki teknikleri kullanır:
* **Minimax Algoritması:** Oyun ağacını tarayarak en iyi hamleyi seçer.
* **Alpha-Beta Budama:** Gereksiz dalları eleyerek arama derinliğini ve hızını artırır.
* **Matris Temsili:** Satranç tahtası `8x8` boyutunda bir liste yapısı (Mailbox) üzerinde simüle edilir.
* **Değerlendirme Fonksiyonu:** Taş puanları ve konum tabloları (Piece-Square Tables) kullanılarak pozisyonel avantaj hesaplanır.

---
© 2025 Ahmet Buğra Kurtboğan
