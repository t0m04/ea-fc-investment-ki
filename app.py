
import streamlit as st, pandas as pd, os, re

st.set_page_config(page_title="EA FC Trading KI — Chat+", layout="centered")
st.title("🤖 EA FC Trading KI — Chat+")

@st.cache_data
def load_recs():
    p = "output/recommendations.csv"
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

def parse_budget(text):
    text = text.lower().replace(",", "")
    m = re.search(r'(\d+(\.\d+)?)\s*(m|mn|mio)', text)
    if m: return int(float(m.group(1)) * 1_000_000)
    m = re.search(r'(\d+(\.\d+)?)\s*(k|tsd)', text)
    if m: return int(float(m.group(1)) * 1_000)
    m = re.search(r'(\d{3,9})', text)
    if m: return int(m.group(1))
    return None

def filter_recs(query, recs):
    budget = parse_budget(query) or 0
    league, seg_hint = None, None
    for lg in recs['league'].dropna().unique():
        if str(lg).lower() in query.lower():
            league = lg; break
    for s in ['fodder','meta','elite']:
        if s in query.lower():
            seg_hint = s; break
    df = recs.copy()
    if budget>0: df = df[df['buy_below'] <= budget]
    if league: df = df[df['league']==league]
    if seg_hint: df = df[df['segment']==seg_hint]
    return df, budget, league, seg_hint

def make_answer(df, budget):
    if df.empty:
        msg = "Ich finde nichts Passendes."
        if budget>0: msg += f" (Budget: {budget:,} Coins)".replace(",", ".")
        return msg
    df = df.sort_values(['expected_profit_coins','confidence'], ascending=[False, False]).head(5)
    lines=[f"Top {len(df)} Vorschläge" + (f" für dein Budget **{budget:,}** Coins" if budget>0 else "") + ":"]
    for _, r in df.iterrows():
        lines.append(f"- **{r['player_name']}** ({r['rating']} {r['position']}, {r['league']}) → "
                     f"Kaufe ≤ **{int(r['buy_below']):,}** • Ziel **{int(r['target_sell']):,}** • "
                     f"Gewinn ~ **{int(r['expected_profit_coins']):,}** • Konfidenz {r['confidence']:.0%} • {r['window']}")
    return "\n".join(lines).replace(",", ".")

# Session state
if "messages" not in st.session_state: st.session_state.messages=[]
if "cart" not in st.session_state: st.session_state.cart=[]

recs = load_recs()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Frag mich nach Investments …"):
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"): st.markdown(prompt)
    # Answer
    df,budget,league,seg = filter_recs(prompt,recs)
    if not budget:
        reply="Bitte gib dein Budget an (z. B. '150k', '1.2m')."
    elif df.empty and recs.empty:
        reply="Keine Daten vorhanden. Lade CSVs in `data/` und starte `eafc_invest.py`."
    elif df.empty:
        reply="Ich habe keine Vorschläge mit deinen Filtern gefunden. Willst du alle Ligen/Segmente sehen?"
    else:
        reply = make_answer(df,budget)
        # Add buttons for cart
        with st.chat_message("assistant"):
            st.markdown(reply)
            for _, r in df.iterrows():
                if st.button(f"🛒 {r['player_name']} ({r['buy_below']:,})", key=f"cart_{r['player_name']}"):
                    st.session_state.cart.append(r.to_dict())
                    st.success(f"{r['player_name']} in den Kaufkorb gelegt!")
        reply=None
    if reply:
        with st.chat_message("assistant"): st.markdown(reply)
    if reply: st.session_state.messages.append({"role":"assistant","content":reply})

# Kaufkorb anzeigen
st.markdown("---")
with st.expander("🛒 Mein Kaufkorb"):
    if not st.session_state.cart:
        st.write("Noch leer.")
    else:
        dfc=pd.DataFrame(st.session_state.cart)
        st.dataframe(dfc[['player_name','buy_below','target_sell','expected_profit_coins','confidence']])
        st.write("Gesamt Coins für Käufe:", int(dfc['buy_below'].sum()))
