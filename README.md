# nithep.com — Corporate Landing (Smart Legacy Platform)

Static self-contained landing หน้าแรก `nithep.com` โทนเดียวกับ `snc/app/landing.html`

## โครงไฟล์ (Cloudflare Pages — deploy จาก root ตรงๆ)

| ไฟล์ | บทบาท |
|---|---|
| `index.html` | Landing หลัก (Hero Smart Legacy + เดโม Check-in→เปิดไฟ) |
| `404.html` | หน้า 404 |
| `_headers` | Security + Cache headers |
| `_redirects` | `www → apex` 301 |

## Preview local

ดับเบิลคลิก `index.html` หรือรัน static server:

```bash
npx serve D:\nithep.com
# หรือ
python -m http.server 8080 --directory D:\nithep.com
```

## Deploy → Cloudflare Pages

1. Push repo นี้ขึ้น `github.com/nithep/landing` branch `main`
2. Cloudflare Dashboard → Pages → Create → Connect to Git → `nithep/landing`
   - Framework preset: **None**, Build command: *(ว่าง)*, Output: `/`
3. Custom domain → `nithep.com` (+ `www.nithep.com` redirect ตาม `_redirects`)
4. ตรวจ: `https://nithep.com` ต้อง 200 + ลิงก์ `snc/shc/shop/docs/admin` ไม่ตาย

## Ecosystem

- `snc.nithep.com` — Smart Nurse Call (Product Platform)
- `shc.nithep.com` — Hotel Check-in → เปิดไฟผ่าน PBX
- `shop.nithep.com` — T.C.Com Shop
- `docs.nithep.com` — KB กลาง · `admin.nithep.com` — Internal Portal
