from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Steam indie game", page_icon="", layout="wide")
GREEN, RED, GREY = "#1F4D3F", "#B3402E", "#A9B8B1"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
GENRES = {"Adventure": "Adventure", "RPG": "RPG", "Strategy": "Strategy", "Action": "Action",
          "Simulation": "Simulation", "Casual": "Casual", "Racing": "Racing", "Sports": "Sports",
          "Early Access": "Early Access"}

@st.cache_data
def load():
    d = pd.read_csv(Path(__file__).parent / "data" / "steam_clean.csv", parse_dates=["date"])
    d = d[d.petit_studio & (d.price > 0)]
    d["genre"] = d.genres.fillna("").str.split(";").apply(lambda g: [GENRES[x] for x in g if x in GENRES])
    d["period"] = d.fetes.map({True: "Holidays (Nov–Dec)", False: "Rest of the year"})
    return d

d = load()

st.sidebar.header("Filters")
years = st.sidebar.slider("Release years", 2014, 2018, (2014, 2017))
max_price = st.sidebar.slider("Maximum price (€)", 1, 70, 70)
threshold = st.sidebar.selectbox("Success = at least … owners", [20_000, 50_000, 100_000, 200_000], index=1)

f = d[d.annee.between(*years) & (d.price <= max_price)].copy()
f["success"] = f.owners_min >= threshold

st.title("Which game should we release for the holidays?")
st.caption("Small indie studios, paid games on Steam · Steam Store + SteamSpy data · prices converted to euros (£1 ≈ €1.14)")

fe, rest = f[f.fetes], f[~f.fetes]
c1, c2, c3 = st.columns(3)
c1.metric("Games analysed", len(f))
c2.metric("Released during the holidays", len(fe))
c3.metric("Success rate during the holidays", f"{fe.success.mean():.0%}",
          f"{(fe.success.mean() - rest.success.mean()) * 100:+.1f} pts vs rest of the year")

g1, g2 = st.columns(2)

genres = fe.explode("genre").dropna(subset=["genre"])
tg = genres.groupby("genre").success.agg(["mean", "size"]).query("size >= 20").sort_values("mean").reset_index()
tg["mean"] *= 100
g1.plotly_chart(px.bar(tg, x="mean", y="genre", orientation="h", text_auto=".0f", hover_data={"size": True},
                       color_discrete_sequence=[GREEN], title="Success rate by genre (Nov–Dec releases)",
                       labels={"mean": "% of successes", "genre": "", "size": "games"}), width="stretch")

tm = f.groupby("mois").agg(releases=("appid", "size"), success=("success", "mean")).reset_index()
tm["month"] = tm.mois.apply(lambda m: MONTHS[m - 1])
tm["colour"] = tm.month.isin(["Nov", "Dec"]).map({True: "Holidays", False: "Other"})
g2.plotly_chart(px.bar(tm, x="month", y="releases", color="colour", title="Number of releases per month",
                       color_discrete_map={"Holidays": RED, "Other": GREY},
                       labels={"releases": "Games released", "month": "", "colour": ""}),
                width="stretch")

g3, g4 = st.columns(2)

f["band"] = pd.cut(f.price, [0, 5, 10, 15, 25, 70], labels=["< €5", "€5–10", "€10–15", "€15–25", "≥ €25"])
tp = f.groupby(["band", "period"], observed=True).success.mean().mul(100).reset_index()
g3.plotly_chart(px.bar(tp, x="band", y="success", color="period", barmode="group", text_auto=".0f",
                       color_discrete_map={"Holidays (Nov–Dec)": RED, "Rest of the year": GREY},
                       title="Success rate by price", labels={"success": "% of successes", "band": "", "period": ""}),
                width="stretch")

q = fe.copy()
q["fortnight"] = pd.cut(q.date.dt.day + (q.mois - 11) * 30, [0, 15, 30, 45, 61],
                        labels=["Nov 1–15", "Nov 16–30", "Dec 1–15", "Dec 16–31"])
tq = q.groupby("fortnight", observed=True).success.mean().mul(100).reset_index()
g4.plotly_chart(px.bar(tq, x="fortnight", y="success", text_auto=".0f", color="fortnight",
                       color_discrete_sequence=[GREEN, RED, GREEN, RED], title="Success rate by fortnight",
                       labels={"success": "% of successes", "fortnight": ""}).update_layout(showlegend=False),
                width="stretch")

st.plotly_chart(px.scatter(fe.dropna(subset=["ratio_pos"]).query("nb_avis >= 10"), x="price", y="nb_avis",
                           color="success", log_y=True, hover_name="name", opacity=0.6,
                           color_discrete_map={True: GREEN, False: GREY},
                           title="Games released during the holidays: price and number of reviews",
                           labels={"price": "Price (€)", "nb_avis": "Number of reviews (log scale)", "success": "Success"}),
                width="stretch")

st.subheader("Biggest indie hits released during the holidays")
top = fe.sort_values("nb_avis", ascending=False).head(15)
st.dataframe(top[["name", "date", "price", "owners", "nb_avis"]].rename(columns={
    "name": "Game", "date": "Release", "price": "Price (€)", "owners": "Owners (estimate)", "nb_avis": "Reviews"}),
    hide_index=True, width="stretch")

st.caption("⚠️ Games released after 2017 had little time to sell before the data snapshot (May 2019).")
