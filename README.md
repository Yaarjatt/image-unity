# 🎨 Image Unity — Free AI Image Generator & API Server

**🌐 Live:** [https://image-unity.onrender.com](https://image-unity.onrender.com)  
**📦 Repo:** https://github.com/Yaarjatt/image-unity

---

## ✅ Zero API Keys Required

This server generates AI images using **completely free resources**:
- **No API keys** needed to start
- **No signup** required
- **No login** for your users
- **Unlimited** generations (within fair use)

## How It Works (Fallback Chain)

```
1️⃣ HuggingFace Free Inference API → FLUX.1-schnell (no token needed!)
2️⃣ Built-in abstract art generator (always works)
```

Each request tries providers in order until one succeeds.

## Quick Test

```bash
curl -X POST https://image-unity.onrender.com/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a beautiful fantasy landscape","style":"fantasy-art"}'
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Provider status |
| `GET` | `/api/models` | Available models |
| `POST` | `/api/generate` | Generate image |
| `GET` | `/api/image/:id` | View image |

## Deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Yaarjatt/image-unity)

---

**Inspired by:** imagefree.org · freegen.app · aifreeforever.com · draw.freeforai.com · perchance.org
