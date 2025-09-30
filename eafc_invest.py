import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
import joblib

# === Pfad einstellen ===
data_path = "demo_data.csv"
os.makedirs("output", exist_ok=True)

# === Daten laden oder Demo erzeugen ===
if os.path.exists(data_path):
    df = pd.read_csv(data_path, parse_dates=['date'])
else:
    np.random.seed(42)
    players = [
        {"player_id": i, "player_name": f"Player_{i}", "rating": np.random.randint(75, 92),
         "league": np.random.choice(["EPL","LaLiga","Bundesliga","SerieA"]),
         "nation": np.random.choice(["ENG","ESP","GER","ITA","FRA"])}
        for i in range(1,51)
    ]
    rows = []
    start = pd.to_datetime("2024-01-01")
    for p in players:
        base_price = np.random.randint(800, 50000)
        price = base_price
        for d in range(200):
            date = start + pd.Timedelta(days=d)
            event = "none"
            if np.random.rand() < 0.02:
                event = np.random.choice(["TOTW","SBC","Event"])
                if event == "SBC": price *= 1.1
                elif event == "TOTW": price *= 1.05
            price = max(50, price * (1 + np.random.normal(0, 0.01)))
            rows.append({
                "player_id": p["player_id"],
                "player_name": p["player_name"],
                "date": date,
                "price": price,
                "event": event,
                "rating": p["rating"],
                "league": p["league"],
                "nation": p["nation"]
            })
    df = pd.DataFrame(rows)

# === Feature Engineering ===
df['price_next_7d'] = df.groupby('player_id')['price'].shift(-7)
df = df.dropna(subset=['price_next_7d'])
df['pct_change_7d'] = (df['price_next_7d'] - df['price']) / df['price']
df['price_roll7_med'] = df.groupby('player_id')['price'].transform(lambda x: x.rolling(7, min_periods=1).median())
df['price_roll30_med'] = df.groupby('player_id')['price'].transform(lambda x: x.rolling(30, min_periods=1).median())
df['is_event'] = (df['event'] != "none").astype(int)
df['dayofweek'] = df['date'].dt.dayofweek
df['days_from_start'] = (df['date'] - df['date'].min()).dt.days

features = ['price','rating','league','nation','is_event','price_roll7_med','price_roll30_med','dayofweek','days_from_start']
target = 'pct_change_7d'

train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
cat_cols = ['league','nation']
preprocessor = ColumnTransformer([('cat', OneHotEncoder(handle_unknown='ignore'), cat_cols)], remainder='passthrough')
model = make_pipeline(preprocessor, RandomForestRegressor(n_estimators=100, random_state=42))
model.fit(train_df[features], train_df[target])

# === Empfehlungen berechnen ===
latest = df.groupby('player_id').apply(lambda g: g.loc[g['date'].idxmax()]).reset_index(drop=True)
latest['pred_pct_change_7d'] = model.predict(latest[features])
latest['expected_profit_coins'] = (latest['pred_pct_change_7d'] * latest['price']).astype(int)
latest['buy_below'] = (latest['price'] * (1 + latest['pred_pct_change_7d']*0.3)).astype(int)

recommendations = latest.sort_values('pred_pct_change_7d', ascending=False).head(20)

# === Speichern ===
recommendations.to_csv("output/recommendations.csv", index=False)
joblib.dump(model, "output/eafc_model.joblib")

print("✅ Empfehlungen gespeichert in output/recommendations.csv")
