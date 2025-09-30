import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split

def synthesize_demo(n_players=50, days=220, seed=42):
    np.random.seed(seed)
    players = [
        {"player_id": i, "player_name": f"Player_{i}", "rating": np.random.randint(75, 92),
         "league": np.random.choice(["EPL","LaLiga","Bundesliga","SerieA"]),
         "nation": np.random.choice(["ENG","ESP","GER","ITA","FRA"])}
        for i in range(1, n_players+1)
    ]
    rows = []
    start = pd.to_datetime("2024-01-01")
    for p in players:
        base_price = np.random.randint(800, 50000)
        price = base_price
        for d in range(days):
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
    return pd.DataFrame(rows)

def engineer(df):
    df = df.sort_values(['player_id','date']).reset_index(drop=True)
    df['price_next_7d'] = df.groupby('player_id')['price'].shift(-7)
    df = df.dropna(subset=['price_next_7d']).copy()
    if len(df)==0:
        return df
    df['pct_change_7d'] = (df['price_next_7d'] - df['price']) / df['price']
    df['price_roll7_med'] = df.groupby('player_id')['price'].transform(lambda x: x.rolling(7, min_periods=1).median())
    df['price_roll30_med'] = df.groupby('player_id')['price'].transform(lambda x: x.rolling(30, min_periods=1).median())
    df['is_event'] = (df['event'] != "none").astype(int)
    df['dayofweek'] = pd.to_datetime(df['date']).dt.dayofweek
    df['days_from_start'] = (pd.to_datetime(df['date']) - pd.to_datetime(df['date']).min()).dt.days
    return df

def main():
    os.makedirs("output", exist_ok=True)
    data_path = "demo_data.csv"
    if os.path.exists(data_path):
        df_raw = pd.read_csv(data_path, parse_dates=['date'])
    else:
        df_raw = synthesize_demo()

    df = engineer(df_raw)

    # Fallback: Wenn zu wenige Zeilen (z.B. Demo CSV mit 2 Zeilen), nutze synthetische Daten
    if len(df) < 100:
        df_raw = synthesize_demo()
        df = engineer(df_raw)

    if len(df) == 0:
        raise RuntimeError("Zu wenige Daten nach Feature-Engineering. Bitte liefere mehr Tage/Spieler in der CSV.")

    features = ['price','rating','league','nation','is_event','price_roll7_med','price_roll30_med','dayofweek','days_from_start']
    cat_cols = ['league','nation']

    preprocessor = ColumnTransformer([('cat', OneHotEncoder(handle_unknown='ignore'), cat_cols)], remainder='passthrough')
    model = RandomForestRegressor(n_estimators=100, random_state=42)

    # Wenn sehr wenige Zeilen, ohne Testsplit trainieren
    if len(df) < 50:
        X_train, y_train = df[features], df['pct_change_7d']
        pipe = make_pipeline(preprocessor, model)
        pipe.fit(X_train, y_train)
    else:
        X_train, X_test, y_train, y_test = train_test_split(df[features], df['pct_change_7d'], test_size=0.2, random_state=42)
        pipe = make_pipeline(preprocessor, model)
        pipe.fit(X_train, y_train)

    latest = df.groupby('player_id').apply(lambda g: g.loc[g['date'].idxmax()]).reset_index(drop=True)
    latest['pred_pct_change_7d'] = pipe.predict(latest[features])
    latest['expected_profit_coins'] = (latest['pred_pct_change_7d'] * latest['price']).astype(int)
    latest['buy_below'] = (latest['price'] * (1 + latest['pred_pct_change_7d']*0.3)).astype(int)

    recommendations = latest.sort_values('pred_pct_change_7d', ascending=False).head(20)
    recommendations.to_csv("output/recommendations.csv", index=False)
    print("✅ Empfehlungen gespeichert in output/recommendations.csv")

if __name__ == "__main__":
    main()
