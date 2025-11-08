import re, base64, pandas as pd, json

# --- read and decrypt ---
html = open("message-4.txt", "r", encoding="utf-8").read()
blob = re.search(r'PagePriceHistoryDataSet\s*=\s*"([^"]+)"', html).group(1)

key = 'O7TXnQ9BzPhkqL3vANf2igREWoMFrjxZwaIYuHt4b5UJs068CcmDVKSdl1epyG'  # from page
raw = base64.b64decode(blob)
dec = bytes([raw[i] ^ ord(key[i % len(key)]) for i in range(len(raw))]).decode("utf-8")

prices = json.loads(dec)
pts = prices["History"]["Price"]   # list of dicts like [{"x": "...", "y": 57999}, ...]

# --- convert to DataFrame ---
df = pd.DataFrame(pts).rename(columns={"x": "date", "y": "price_inr"})

# --- convert to THB ---
INR_TO_THB = 0.44
df["price_thb"] = df["price_inr"] * INR_TO_THB

# --- save ---
df.to_csv("a55_from_html.csv", index=False)
print(df.head())

# read your CSV from the decrypted API output
# df = pd.read_csv("s24_from_html.csv")

# # add THB column (use current rate)
# INR_TO_THB = 0.44
# df["price_thb"] = df["price_inr"] * INR_TO_THB

# df.to_csv("s24_price_in_thb.csv", index=False)
# print(df.head())