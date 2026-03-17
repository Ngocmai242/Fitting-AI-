"""
test_idmvton.py — test connection to IDM-VTON
Chạy: cd backend && python test_idmvton.py
"""
import os, sys, tempfile, urllib.request

print("=" * 60)
print("TEST IDM-VTON CONNECTION")
print("=" * 60)

# Test 1: import
print("\n[1] Import gradio_client...")
try:
    from gradio_client import Client, handle_file
    import gradio_client
    print(f"    OK — version: {gradio_client.__version__}")
except ImportError as e:
    print(f"    FAIL — {e}")
    print("    → Chạy: pip install 'gradio-client==0.9.0'")
    sys.exit(1)

# Test 2: download ảnh test
print("\n[2] Download ảnh test...")
tmp = tempfile.mkdtemp()
person_path  = os.path.join(tmp, "person.jpg")
garment_path = os.path.join(tmp, "garment.jpg")
try:
    urllib.request.urlretrieve(
        "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=512&q=80",
        person_path
    )
    urllib.request.urlretrieve(
        "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=512&q=80",
        garment_path
    )
    print(f"    OK — image saved at {tmp}")
except Exception as e:
    print(f"    FAIL — {e}")
    sys.exit(1)

# Test 3: thử từng space
print("\n[3] Testing connection to each Space...")
SPACES = [
    "yisol/IDM-VTON",
    "freddyaboulton/IDM-VTON",
    "adi1516/IDM_VTON",
]
HF_TOKEN = os.getenv("HF_TOKEN", "")

working_space = None
for space in SPACES:
    print(f"\n    → Trying {space}...")
    try:
        client = Client(space, hf_token=HF_TOKEN)
        print(f"      Connection: OK")
        # Try actual prediction
        result = client.predict(
            dict={"background": handle_file(person_path), "layers": [], "composite": None},
            garm_img=handle_file(garment_path),
            garment_des="",
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=20,
            seed=42,
            api_name="/tryon"
        )
        out_img = result[0] if isinstance(result, (list, tuple)) else result
        print(f"      Predict: OK → {out_img}")
        working_space = space
        break
    except Exception as e:
        print(f"      FAIL — {type(e).__name__}: {str(e)[:200]}")

print("\n" + "=" * 60)
if working_space:
    print(f"✅ WORKING SPACE: {working_space}")
    print("→ Update the code to use this space as the primary priority.")
else:
    print("❌ ALL SPACES FAILED")
    print("→ See details above to identify the cause.")
    print("→ Solutions:")
    print("   1. Register HF_TOKEN at https://huggingface.co/settings/tokens")
    print("   2. Add to .env: HF_TOKEN=hf_xxxxxxxxxxxx")
    print("   3. Run this test again")
print("=" * 60)

