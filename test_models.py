#!/usr/bin/env python3
"""
Comprehensive Model & Provider Tester for G4F Instance
Tests text (chat completions) and image generation across providers and models.

Usage examples:
  python test_models.py --help
  python test_models.py --text --limit 20
  python test_models.py --image
  python test_models.py --text --image --providers "DeepInfra,Gemini"
  python test_models.py --all --delay 1.5
"""

import requests
import json
import time
import argparse
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

BASE_URL = "https://coupons-executive-aquarium-plug.trycloudflare.com"
MODELS_URL = f"{BASE_URL}/v1/models"
CHAT_URL = f"{BASE_URL}/v1/chat/completions"
IMAGE_URL = f"{BASE_URL}/v1/images/generations"

# Common test prompts
TEXT_PROMPT = "Reply with exactly one word: SUCCESS"
IMAGE_PROMPT = "a simple red circle on a white background"

# Popular models to test across providers
POPULAR_TEXT_MODELS = [
    "gpt-4o-mini", "gpt-4o", "llama-3.1-8b", "llama-3.1-70b", "deepseek-v3",
    "qwen-2.5-7b", "gemini-2.0-flash", "default"
]

POPULAR_IMAGE_MODELS = [
    "flux", "dall-e-3", "gpt-image", "flux-dev", 
    "black-forest-labs/FLUX-2-klein-4b",
    "black-forest-labs/FLUX-2-klein-9b"
]

def fetch_models():
    """Fetch and parse the full models list."""
    print("Fetching models list...")
    resp = requests.get(MODELS_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    models = data.get("data", [])
    print(f"  Total entries: {len(models)}")
    return models

def get_providers(models):
    providers = sorted([m["id"] for m in models if m.get("provider") == True])
    return providers

def get_image_providers(models):
    return sorted([m["id"] for m in models if m.get("image") == True and m.get("provider") == True])

def get_regular_models(models):
    return sorted([m["id"] for m in models if m.get("provider") == False])

def test_text(provider=None, model=None, timeout=25):
    """Test text/chat completion."""
    payload = {
        "messages": [{"role": "user", "content": TEXT_PROMPT}],
        "max_tokens": 10,
        "temperature": 0.1
    }
    if model:
        payload["model"] = model
    if provider:
        payload["provider"] = provider

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(CHAT_URL, json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
                if content and "SUCCESS" in content.upper():
                    return True, content.strip()[:100]
                return True, f"Response received (content: {content[:60] if content else 'empty'}...)"
            return False, f"No choices: {str(data)[:150]}"
        else:
            err = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
            return False, err
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)[:150]

def test_image(provider=None, model=None, timeout=60):
    """Test image generation."""
    payload = {
        "prompt": IMAGE_PROMPT,
        "n": 1,
        "response_format": "url"
    }
    if model:
        payload["model"] = model
    if provider:
        payload["provider"] = provider

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(IMAGE_URL, json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                url = data["data"][0].get("url", "")
                if url and url.startswith("http"):
                    return True, url
                return False, f"No valid URL: {str(data)[:150]}"
            return False, f"No data: {str(data)[:150]}"
        else:
            err = resp.text[:250] if resp.text else f"HTTP {resp.status_code}"
            return False, err
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)[:150]

def run_tests(test_cases, test_type, delay=1.0, max_workers=3):
    """Run a list of (provider, model) tests."""
    results = []
    print(f"\n=== Testing {test_type.upper()} ({len(test_cases)} combinations) ===")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_case = {}
        for provider, model in test_cases:
            if test_type == "text":
                future = executor.submit(test_text, provider, model)
            else:
                future = executor.submit(test_image, provider, model)
            future_to_case[future] = (provider, model)
            time.sleep(0.1)  # small stagger

        completed = 0
        for future in as_completed(future_to_case):
            provider, model = future_to_case[future]
            success, detail = future.result()
            results.append({
                "provider": provider,
                "model": model,
                "success": success,
                "detail": detail,
                "type": test_type
            })
            completed += 1
            status = "✅" if success else "❌"
            model_str = model if model else "(default)"
            print(f"  [{completed}/{len(test_cases)}] {status} {provider} | {model_str}  → {detail[:70]}")
            time.sleep(delay)  # be respectful to the server

    return results

def main():
    parser = argparse.ArgumentParser(description="Test all models across all providers on G4F")
    parser.add_argument("--text", action="store_true", help="Test text/chat models")
    parser.add_argument("--image", action="store_true", help="Test image generation")
    parser.add_argument("--all", action="store_true", help="Test both text and image")
    parser.add_argument("--providers", type=str, default="", help="Comma-separated list of providers to test (e.g. DeepInfra,Gemini)")
    parser.add_argument("--delay", type=float, default=1.2, help="Delay between requests (seconds)")
    parser.add_argument("--max-workers", type=int, default=2, help="Concurrent requests (use low values)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of tests per category (for quick runs)")
    parser.add_argument("--output", type=str, default="model_test_results.json", help="Output JSON file")
    args = parser.parse_args()

    if not (args.text or args.image or args.all):
        args.all = True  # default to both

    if args.all:
        args.text = True
        args.image = True

    print(f"Starting tests at {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")

    models = fetch_models()
    all_providers = get_providers(models)
    image_providers = get_image_providers(models)
    regular_models = get_regular_models(models)

    # Filter providers if specified
    target_providers = all_providers
    if args.providers:
        target_list = [p.strip() for p in args.providers.split(",")]
        target_providers = [p for p in all_providers if p in target_list]
        print(f"Testing only these providers: {target_providers}")

    all_results = []

    # ========== TEXT TESTS ==========
    if args.text:
        text_cases = []

        # 1. Test every provider with itself as model (very common pattern)
        for prov in target_providers:
            text_cases.append((prov, prov))

        # 2. Test every provider with a few popular models
        for prov in target_providers:
            for m in POPULAR_TEXT_MODELS[:3]:  # limit to 3 per provider
                text_cases.append((prov, m))

        # 3. Test popular regular models with AnyProvider (and a couple big providers)
        for m in regular_models[:50] if args.limit == 0 else regular_models[:args.limit]:  # limit regular models
            text_cases.append((None, m))                    # no provider
            text_cases.append(("AnyProvider", m))

        if args.limit > 0:
            text_cases = text_cases[:args.limit]

        # Deduplicate
        text_cases = list(dict.fromkeys(text_cases))  # preserve order, remove dups

        text_results = run_tests(text_cases, "text", delay=args.delay, max_workers=args.max_workers)
        all_results.extend(text_results)

    # ========== IMAGE TESTS ==========
    if args.image:
        image_cases = []

        # 1. Test every image provider with itself as model
        for prov in image_providers:
            if not target_providers or prov in target_providers:
                image_cases.append((prov, prov))

        # 2. Test image providers with popular image models
        for prov in image_providers:
            if not target_providers or prov in target_providers:
                for m in POPULAR_IMAGE_MODELS:
                    image_cases.append((prov, m))

        # 3. Test some regular image-like models with AnyProvider
        for m in ["flux", "dall-e-3", "gpt-image", "flux-dev"]:
            image_cases.append((None, m))
            image_cases.append(("AnyProvider", m))

        if args.limit > 0:
            image_cases = image_cases[:args.limit]

        image_cases = list(dict.fromkeys(image_cases))

        image_results = run_tests(image_cases, "image", delay=args.delay, max_workers=args.max_workers)
        all_results.extend(image_results)

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "total_tests": len(all_results),
        "results": all_results
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    # Generate summary
    text_success = [r for r in all_results if r["type"] == "text" and r["success"]]
    image_success = [r for r in all_results if r["type"] == "image" and r["success"]]

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total tests run: {len(all_results)}")
    print(f"Text successes:  {len(text_success)} / {len([r for r in all_results if r['type']=='text'])}")
    print(f"Image successes: {len(image_success)} / {len([r for r in all_results if r['type']=='image'])}")

    if text_success:
        print("\nWorking TEXT combinations (sample):")
        for r in text_success[:10]:
            print(f"  ✅ {r['provider'] or 'Any'} | {r['model'] or '(default)'}")

    if image_success:
        print("\nWorking IMAGE combinations (sample):")
        for r in image_success[:10]:
            print(f"  ✅ {r['provider'] or 'Any'} | {r['model'] or '(default)'}  → {r['detail'][:60]}")

    # Save human-readable summary
    summary_file = args.output.replace(".json", "_summary.txt")
    with open(summary_file, "w") as f:
        f.write(f"G4F Model Test Summary - {datetime.now().isoformat()}\n")
        f.write(f"Base: {BASE_URL}\n\n")
        f.write(f"Text working: {len(text_success)}\n")
        f.write(f"Image working: {len(image_success)}\n\n")
        f.write("Working TEXT:\n")
        for r in sorted(text_success, key=lambda x: (x['provider'] or '', x['model'] or '')):
            f.write(f"  {r['provider'] or 'None'} | {r['model'] or 'default'} → {r['detail']}\n")
        f.write("\nWorking IMAGE:\n")
        for r in sorted(image_success, key=lambda x: (x['provider'] or '', x['model'] or '')):
            f.write(f"  {r['provider'] or 'None'} | {r['model'] or 'default'} → {r['detail']}\n")

    print(f"\nDetailed results saved to: {args.output}")
    print(f"Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()