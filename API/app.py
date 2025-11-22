# app.py
from dotenv import load_dotenv
from fastapi import FastAPI
import pandas as pd
import numpy as np
import psycopg2
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import GRU, Dense
from datetime import datetime, timedelta
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL") 
MODEL_FILE = "gru_model_latest.h5"
PRODUCT_LINK = "https://www.amazon.in/pricehistory.app/dp/B0CS6H3Y9G?tag=cuelinkss26094-21&ascsubtag=20251122clwf9dn9rfbh&th=1"

app = FastAPI(title="Samsung S24 Price Prediction API")

# ---------------- DB ----------------
def connect_db():
    return psycopg2.connect(DATABASE_URL)

def load_price_data():
    conn = connect_db()
    df = pd.read_sql("SELECT date, price_inr, price_thb FROM pricehistory ORDER BY date ASC", conn)
    conn.close()

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values('date')
    return df

def get_last_trained_date():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT last_trained_date FROM last_trained_date LIMIT 1", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    
    if df.empty or df["last_trained_date"].iloc[0] is None:
        return None
    return pd.to_datetime(df["last_trained_date"].iloc[0]).date()

def update_last_trained_date(new_date):
    conn = connect_db()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM last_trained_date")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO last_trained_date(last_trained_date) VALUES (%s)", (new_date,))
        else:
            cur.execute("UPDATE last_trained_date SET last_trained_date = %s", (new_date,))
    conn.commit()
    conn.close()

# ---------------- Data Processing ----------------
def clean_data(df, seq_length=10, alpha=0.2):
    full_dates = pd.date_range(df['date'].min(), pd.Timestamp.today())
    df = df.set_index('date').reindex(full_dates)
    df.index.name = 'date'
    df['price_inr'] = df['price_inr'].ffill()
    
    data = df['price_inr'].values.reshape(-1,1)
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)

    X, y = [], []
    for i in range(len(data_scaled)-seq_length):
        X.append(data_scaled[i:i+seq_length])
        y.append(data_scaled[i+seq_length])
    X = np.array(X)
    y = np.array(y)

    last_prices = pd.Series(X[:,-1,0])
    smoothed = last_prices.ewm(alpha=alpha, adjust=False).mean()
    pct_change = smoothed.pct_change().abs().fillna(0)
    keep_idx = pct_change <= 1
    return X[keep_idx.values], y[keep_idx.values], scaler

# ---------------- Model ----------------
def train_gru(X_train, y_train, seq_length=10, epochs=199):
    model = Sequential()
    model.add(GRU(50, activation='relu', input_shape=(seq_length,1)))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.fit(X_train, y_train, epochs=epochs, batch_size=32, verbose=1)
    return model

def predict_30_days(model, last_seq, scaler, exchange_rate):
    preds = []
    current_seq = last_seq.copy()
    for _ in range(30):
        pred = model.predict(current_seq[np.newaxis,:,:], verbose=0)
        preds.append(pred[0,0])
        current_seq = np.vstack([current_seq[1:], pred])

    preds_inr = scaler.inverse_transform(np.array(preds).reshape(-1,1)).flatten()
    preds_thb = preds_inr * exchange_rate

    dates = pd.date_range(datetime.today()+timedelta(days=1), periods=30)

    return pd.DataFrame({
        "date": dates,
        "predicted_price_inr": preds_inr,
        "predicted_price_thb": preds_thb
    })

# ---------------- API ----------------
@app.get("/predict")
def predict():
    df = load_price_data()
    if df.empty:
        return {"error": "No price data available."}

    latest_db_date = df["date"].iloc[-1].date()
    last_trained_date = get_last_trained_date()

    seq_length = 10
    X, y, scaler = clean_data(df, seq_length=seq_length)

    model = load_model(MODEL_FILE) if os.path.exists(MODEL_FILE) else None

    if last_trained_date != latest_db_date or model is None:
        model = train_gru(X, y, seq_length=seq_length, epochs=199)
        model.save(MODEL_FILE)
        update_last_trained_date(latest_db_date)

    last_seq = X[-1]
    exchange_rate = df.iloc[-1]["price_thb"] / df.iloc[-1]["price_inr"]
    predictions_df = predict_30_days(model, last_seq, scaler, exchange_rate)

    return {
        "product_link": PRODUCT_LINK,
        "latest_prices": df.tail(10).to_dict(orient="records"),
        "predictions": predictions_df.to_dict(orient="records")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)