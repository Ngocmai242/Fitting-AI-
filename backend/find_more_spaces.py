from gradio_client import Client

spaces = [
    "fashn-ai/FASHN-TryOn",
    "humanAIGC/OutfitAnyone",
    "Kwai-Kolors/Kolors-Virtual-Try-On", 
    "yisol/IDM-VTON",
    "levihsu/OOTDiffusion"
]

for s in spaces:
    try:
        print(f"\n--- Testing Space: {s} ---")
        c = Client(s)
        print("API Info:")
        print(c.view_api())
    except Exception as e:
        print(f"Failed to load {s}: {e}")
