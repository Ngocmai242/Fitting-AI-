from gradio_client import Client

spaces = [
    "yisol/IDM-VTON",
    "Nymbo/Virtual-Try-On",
    "xiaozaa/Kolors-Virtual-Try-On",
    "franciseng/IDM-VTON"
]

for s in spaces:
    try:
        print(f"\n--- Testing Space: {s} ---")
        c = Client(s)
        print("API Info:")
        print(c.view_api())
    except Exception as e:
        print(f"Failed to load {s}: {e}")
