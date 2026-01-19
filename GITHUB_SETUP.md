# GitHub Actions ile Otomatik Video Yükleme Kurulumu (Movie Recap)

Bilgisayarınız kapalıyken bile videolarınızın otomatik üretilip yüklenmesi için bu projeyi GitHub Actions üzerinde çalıştırabilirsiniz.

## Adım 1: Kodları GitHub'a Gönderin

Aşağıdaki komutları terminalde çalıştırın (authentication hatası alırsanız Token girmeniz gerekebilir):

```bash
git add .
git commit -m "Migrate to Movie Recap"
git branch -M main
git remote set-url origin https://github.com/movie-recap-shorts/shorts.git
git push -u origin main
```

## Adım 2: Token Oluşturun (Önemli!)

Yeni kanalınız (`movies_en`) için bir Token oluşturmanız gerekiyor. Terminalde şunu çalıştırın:

```bash
python3 setup_youtube_auth.py --channel movies_en
```
Tarayıcı açıldığında Google hesabınıza girip izin verin. Bu işlem `credentials/movies_en_token.json` dosyasını oluşturacak.

## Adım 3: Secret'ları Ekleyin

1. Reponuzda (`movie-recap-shorts/shorts`) **Settings** > **Secrets and variables** > **Actions** menüsüne gidin.
2. **New repository secret** butonuna tıklayın ve aşağıdakileri ekleyin:

| Secret Adı | Değer (Dosya İçeriği) |
|------------|---------------------------|
| `PEXELS_API_KEY` | `config.toml` içindeki anahtarınız |
| `CLIENT_SECRET_JSON` | `credentials/movies_en.json` dosyasının tamamı |
| `TOKEN_JSON` | `credentials/movies_en_token.json` dosyasının tamamı |

## Adım 4: Test Edin

**Actions** sekmesinden workflow'u manuel tetikleyerek test edebilirsiniz.
