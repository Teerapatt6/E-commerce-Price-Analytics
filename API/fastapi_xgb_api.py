from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
import psycopg2
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from datetime import timedelta
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="Samsung S24 XGBoost Price Prediction API (Price Difference Model)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

def load_price_history():
    conn = connect_db()
    try:
        df = pd.read_sql("SELECT date, price_inr, price_thb FROM pricehistory ORDER BY date ASC;", conn)
        df['date'] = pd.to_datetime(df['date'])
        df['price_inr'] = df['price_inr'].astype(float)
        df['price_thb'] = df['price_thb'].astype(float)
        return df
    finally:
        conn.close()

def load_scaled_features_and_target():
    conn = connect_db()
    try:
        df_features = pd.read_sql("SELECT * FROM price_features ORDER BY date ASC;", conn)
        df_features['date'] = pd.to_datetime(df_features['date'])

        df_history = pd.read_sql("SELECT date, price_inr FROM pricehistory ORDER BY date ASC;", conn)
        df_history['date'] = pd.to_datetime(df_history['date'])
        df_history['price_inr'] = df_history['price_inr'].astype(float)
        
        df_merged = pd.merge(df_features, df_history, on='date', how='inner')
        
        price_series_clean = df_merged['price_inr']
        price_diff_series = price_series_clean.diff(1)
        
        df_merged = df_merged.iloc[31:].reset_index(drop=True)
        y = price_diff_series.iloc[31:].values.astype(float)
        
        X_scaled = df_merged.drop(columns=['date', 'price_inr'])
        
        return X_scaled.astype(float), y, df_history
    finally:
        conn.close()

def generate_unscaled_features_for_scaler(df):

    price_series = df['price_inr']
    price_thb_series = df['price_thb']
    
    threshold = 0.1
    data_scaled = (price_series - price_series.min()) / (price_series.max() - price_series.min())
    pct_change = data_scaled.pct_change().abs().fillna(0)
    
    keep_idx = pct_change <= threshold
    price_series_clean = price_series.copy()
    price_thb_series_clean = price_thb_series.copy()
    price_series_clean[~keep_idx] = np.nan
    price_thb_series_clean[~keep_idx] = np.nan
    price_series_clean = price_series_clean.ffill()
    price_thb_series_clean = price_thb_series_clean.ffill()
    dates_clean = df['date']
    
    price_diff_series = price_series_clean.diff(1)
    price_thb_diff_series = price_thb_series_clean.diff(1)

    X_feat = pd.DataFrame()
    lags = [1,2,3,5,7,10,14,21,30]
    X_feat['price_lag_1'] = price_series_clean.shift(1)
    for lag in lags[1:]:
        X_feat[f'diff_lag_{lag}'] = price_diff_series.shift(lag)
    X_feat['diff_rolling7_mean'] = price_diff_series.rolling(7).mean().bfill() 
    X_feat['diff_rolling30_mean'] = price_diff_series.rolling(30).mean().bfill() 
    X_feat['diff_rolling7_std'] = price_diff_series.rolling(7).std().bfill() 
    X_feat['diff_rolling30_std'] = price_diff_series.rolling(30).std().bfill() 
    alphas = [0.1,0.3,0.5,0.7]
    for a in alphas:
        col_name = f"ewma_diff_alpha_{str(a).replace('.', '_')}"
        X_feat[col_name] = price_diff_series.ewm(alpha=a, adjust=False).mean()
    X_feat['thb_diff_lag_1'] = price_thb_diff_series.shift(1) 
    X_feat['thb_diff_rolling7'] = price_thb_diff_series.rolling(7).mean().bfill() 
    X_feat['dayofweek'] = dates_clean.dt.dayofweek.astype(float)
    X_feat['dayofyear'] = dates_clean.dt.dayofyear.astype(float)
    X_feat['dayofmonth'] = dates_clean.dt.day.astype(float)

    X_feat = X_feat.iloc[31:].reset_index(drop=True)
    X_feat.fillna(0, inplace=True)
    X_feat = X_feat.astype(float)

    scaler = StandardScaler()
    scaler.fit(X_feat) 
    
    return X_feat.iloc[-1].to_frame().T, scaler


model_cache = {
    'bst': None,
    'scaler': None,
    'df_features_latest': None,
    'last_price': None,
    'last_thb_price': None,
    'exchange_rate': None,
    'last_date': None,
    'is_trained': False
}

def train_xgb(X_scaled, y, scaler):
    
    n_total = len(X_scaled)
    n_train = int(n_total * 0.85)
    n_val = int(n_total * 0.15)
    
    X_train_scaled = X_scaled[:n_train]
    X_val_scaled = X_scaled[n_train:n_train+n_val]
    y_train = y[:n_train]
    y_val = y[n_train:n_train+n_val]

    dtrain = xgb.DMatrix(X_train_scaled.values, label=y_train)
    dval = xgb.DMatrix(X_val_scaled.values, label=y_val)

    params = {
        'objective': 'reg:squarederror',
        'learning_rate': 0.05,
        'max_depth': 8,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': 42,
        'gamma': 0.5,
        'min_child_weight': 0.5
    }

    evals = [(dtrain, 'train'), (dval, 'val')]

    bst = xgb.train(
        params,
        dtrain,
        num_boost_round=1500,
        evals=evals,
        early_stopping_rounds=30,
        verbose_eval=False
    )
    
    return bst, scaler, n_val

def predict_30_days(df_features_unscaled_latest, bst, scaler, latest_price, latest_date, n_days=30):
    
    X_next_unscaled = df_features_unscaled_latest.copy()
    
    pred_prices = []
    last_price = latest_price
    
    for i in range(1, n_days + 1):
        X_next_unscaled['price_lag_1'] = last_price
        
        current_date = latest_date + timedelta(days=i)
        X_next_unscaled['dayofweek'] = current_date.dayofweek
        X_next_unscaled['dayofyear'] = current_date.timetuple().tm_yday
        X_next_unscaled['dayofmonth'] = current_date.day
        
        X_input_scaled = scaler.transform(X_next_unscaled.values)

        dmatrix_input = xgb.DMatrix(X_input_scaled)
        
        y_diff_pred = bst.predict(dmatrix_input, iteration_range=(0, bst.best_iteration + 1))[0]
        
        next_price = last_price + y_diff_pred
        pred_prices.append(next_price)

        last_price = next_price

    pred_dates = [latest_date + timedelta(days=i) for i in range(1, n_days + 1)]
    return pd.DataFrame({"date": pred_dates, "pred_price_inr": pred_prices})

async def get_trained_model():
    if not model_cache['is_trained']:
        try:
            df_history = load_price_history()
            if df_history.empty:
                raise ValueError("No data found in pricehistory table.")

            latest_date = df_history['date'].iloc[-1]
            latest_price_inr = df_history['price_inr'].iloc[-1]
            latest_price_thb = df_history['price_thb'].iloc[-1]
            latest_exchange_rate = latest_price_thb / latest_price_inr

            df_features_unscaled_latest, scaler = generate_unscaled_features_for_scaler(df_history)

            X_scaled, y, _ = load_scaled_features_and_target()
            
            bst, scaler_returned, n_val = train_xgb(X_scaled, y, scaler)
            
            model_cache.update({
                'bst': bst,
                'scaler': scaler_returned,
                'df_features_latest': df_features_unscaled_latest, 
                'last_price': latest_price_inr,
                'last_thb_price': latest_price_thb,
                'exchange_rate': latest_exchange_rate,
                'last_date': latest_date,
                'is_trained': True
            })
            print(f"Model trained successfully on {len(X_scaled)} data points. Best iteration: {bst.best_iteration + 1}. Validation size: {n_val}")
            
        except Exception as e:
            print(f"Failed to train model: {e}")
            raise

    return model_cache

@app.get("/predict", tags=["Prediction"])
async def predict():

    try:
        cache = await get_trained_model()
        
        predictions_df = predict_30_days(
            cache['df_features_latest'], 
            cache['bst'], 
            cache['scaler'], 
            cache['last_price'],
            cache['last_date'],
            n_days=30
        )
        
        exchange_rate = cache['exchange_rate']
        predictions_df['pred_price_thb'] = predictions_df['pred_price_inr'] * exchange_rate

        return {
            "status": "success",
            "product_url": os.getenv("PRODUCT_URL"),  
            "latest_date": str(cache['last_date'].date()),
            "latest_price_inr": round(cache['last_price'], 2),
            "latest_price_thb": round(cache['last_thb_price'], 2),
            "exchange_rate_inr_to_thb": round(exchange_rate, 4),
            "predictions_count": len(predictions_df),
            "predictions": [
                {
                    "date": str(row['date'].date()), 
                    "price_inr": round(row['pred_price_inr'], 2),
                    "price_thb": round(row['pred_price_thb'], 2)
                }
                for _, row in predictions_df.iterrows()
            ]
        }

    except Exception as e:
        return {"status": "error", "message": f"An error occurred during training or prediction: {e}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_xgb_api:app", host="0.0.0.0", port=8000, reload=True)