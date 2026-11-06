"""
ETH outlets: themes and authors — Streamlit dashboard

Run:
    pip install streamlit pandas plotly
    streamlit run eth_dashboard_app.py

Expects df_final.csv next to this file (or change DATA_PATH), with columns:
year, issue_month, outlet, title, author_str, theme_str, n_words, url, text
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = "df_final.csv"

OUTLET_NAMES = {"news": "ETH News", "globe": "Globe", "life": "Life"}
OUTLET_COLORS = {"ETH News": "#2F6FDE", "Globe": "#E07A1F", "Life": "#2E9E6B"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Optional: merge spelling variants of the same person, e.g.
# AUTHOR_FIXES = {"Samuel Schlaefli": "Samuel Schläfli"}
AUTHOR_FIXES = {}
UNKNOWN = "unknown author"

# The 24 theme categories, grouped by area, with the original ETH News tags
# that were combined into each one.
THEME_CATEGORIES = {
    "Medicine & life sciences": {
        "Medicine & health": ["Medicine", "Health sciences", "Life sciences and medicine",
                              "Personalised medicine", "Pharmaceutical sciences", "Neurosciences",
                              "Human movement sciences", "Coronavirus"],
        "Biology": ["Biology", "Biotechnology", "Systems biology", "Computational Biology",
                    "Evolution", "Plant sciences"],
        "Animal research": ["Animal experiments", "3R - Replace, Reduce, Refine"],
        "Food & agriculture": ["Agricultural sciences", "World food system", "Food sciences",
                               "Nutritional sciences"],
    },
    "Environment, earth, space & energy": {
        "Environment & climate": ["Environmental sciences", "Climate sciences", "Biodiversity",
                                  "Environmental Engineering"],
        "Earth & space": ["Earth sciences", "Geophysics", "Earth and Planetary Sciences",
                          "Earthquakes", "Geochemistry and Petrology", "Geology",
                          "Planetary sciences", "Astronomy", "Space research"],
        "Energy & mobility": ["Energy sciences", "Mobility"],
        "Sustainability": ["Sustainability"],
    },
    "Natural sciences, engineering & computing": {
        "Physics": ["Physics", "Quantum sciences", "Particle physics"],
        "Chemistry & materials": ["Chemistry", "Materials science", "Nanosciences"],
        "Engineering": ["Engineering sciences", "Mechanical engineering", "Electrical engineering",
                        "Civil engineering", "Process engineering", "Microtechnology",
                        "Imaging technology", "Digital fabrication"],
        "Robotics": ["Robotics"],
        "Computing & data": ["Computer and information technology", "Data science",
                             "Supercomputing", "Computational sciences", "Mathematics",
                             "Statistics", "Systems science"],
        "Artificial intelligence": ["Artificial intelligence"],
        "Architecture & planning": ["Architecture", "Spatial planning", "Urban design",
                                    "Architecture and spatial planning", "Landscape architecture",
                                    "Geoinformation", "Building systems"],
    },
    "Social sciences & humanities": {
        "Social sciences & humanities": ["Social sciences", "Political science", "Economics",
                                         "Behavioural sciences", "Humanities",
                                         "Humanities and social sciences", "International studies",
                                         "Conflict research", "Security research", "Management",
                                         "Ethics", "History of science", "Business cycle research",
                                         "Law", "Risk research", "Psychology"],
    },
    "University life": {
        "International": ["International", "International development"],
        "Cooperations": ["Cooperations"],
        "Innovation & spin-offs": ["Innovation & Industry", "Spin-offs and patents"],
        "Teaching & learning": ["Teaching & Learning", "Learning and instruction",
                                "Critical Thinking"],
        "People & careers": ["Careers", "People", "Diversity", "International Women's Day",
                             "Obituary"],
        "Awards": ["The latest honours and prizes", "Research awards",
                   "Industry and innovation prizes", "Lectureships and honours", "Other prizes",
                   "Teaching awards"],
        "University & governance": ["Society & Institution", "Executive Board",
                                    "Administration and infrastructure", "Funding", "Donations",
                                    "Boards and university groups", "rETHink", "Hönggerberg campus",
                                    "Zentrum campus", "Locations", "Campus Heilbronn"],
        "Events & culture": ["Events", "Culture and sport"],
    },
}

THEME_NOTE = (
    "**Where the themes come from.** "
    "ETH News articles carry topic tags chosen by ETH's editors. We grouped those tags into "
    f"{sum(len(v) for v in THEME_CATEGORIES.values())} broader themes (see *Theme categories* "
    "at the bottom of the page). "
    "Globe and Life articles have no tags, so their themes were **predicted by a computer**: a "
    "language model that learned from ETH News articles and their themes from 2020 to 2026, and "
    "then read each magazine article and suggested matching themes. The results are quite "
    "reliable, but an individual Globe or Life article may now and then get a theme a person "
    "would not have picked. Patterns across many articles are more trustworthy than single ones."
)


# ---------------------------------------------------------------- data
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.dropna(subset=["year", "title"]).reset_index(drop=True)

    df["year"] = df["year"].astype(int)
    df["outlet_name"] = df["outlet"].map(OUTLET_NAMES).fillna(df["outlet"])
    df["n_words"] = pd.to_numeric(df["n_words"], errors="coerce").fillna(0).astype(int)

    def split(value):
        if pd.isna(value) or not str(value).strip():
            return []
        return [x.strip() for x in str(value).split(",") if x.strip()]

    df["authors"] = df["author_str"].apply(split).apply(
        lambda names: [AUTHOR_FIXES.get(n, n) for n in names] or ["unknown author"]
    )
    df["themes"] = df["theme_str"].apply(split)
    df["author_str"] = df["authors"].str.join(", ")
    df["theme_str"] = df["themes"].str.join(", ")

    # Sort key for "January" ... or "Issue 3"
    def period_rank(p):
        p = str(p)
        if p in MONTHS:
            return MONTHS.index(p) + 1
        digits = "".join(ch for ch in p if ch.isdigit())
        return int(digits) if digits else 0

    df["period_rank"] = df["issue_month"].apply(period_rank)

    return df


df = load_data(DATA_PATH)
ALL_THEMES = sorted({t for ts in df["themes"] for t in ts})

st.set_page_config(page_title="ETH Communications Dashboard (2024-2026)", layout="wide")


# ---------------------------------------------------------------- filters
st.sidebar.header("Filters")


def reset_filters():
    """Back to the start: all outlets, all years, all authors, all themes, empty searches."""
    st.session_state["outlet_select"] = list(OUTLET_NAMES.values())
    st.session_state["year_select"] = "All years"
    st.session_state["author_select"] = "All authors"
    st.session_state["theme_select"] = "All themes"
    st.session_state["author_search"] = ""
    st.session_state["article_search"] = ""
    st.session_state.pop("authors_table", None)  # clears the clicked row in the authors table


st.sidebar.button("Reset all filters", on_click=reset_filters, width="stretch")

st.session_state.setdefault("outlet_select", list(OUTLET_NAMES.values()))  # start: all outlets
outlet_choice = st.sidebar.multiselect("Outlet", list(OUTLET_NAMES.values()), key="outlet_select")

years = sorted(df["year"].unique())
year_pick = st.sidebar.selectbox("Year", ["All years"] + [str(y) for y in reversed(years)],
                                 key="year_select")
year_choice = years if year_pick == "All years" else [int(year_pick)]

# Author list follows the outlet and year filters, with article counts
base = df[df["outlet_name"].isin(outlet_choice) & df["year"].isin(year_choice)]
author_counts = base.explode("authors")["authors"].value_counts()
# "unknown author" always goes last
author_counts = pd.concat([author_counts.drop(UNKNOWN, errors="ignore"),
                           author_counts.loc[author_counts.index == UNKNOWN]])
author_options = ["All authors"] + list(author_counts.index)
# A previously picked author may drop out of the list when outlet/year change
if st.session_state.get("author_select") not in author_options:
    st.session_state["author_select"] = "All authors"
author_pick = st.sidebar.selectbox(
    "Author (articles)", author_options, key="author_select",
    format_func=lambda a: a if a == "All authors" else f"{a} ({author_counts[a]})",
)
author = None if author_pick == "All authors" else author_pick

theme = st.sidebar.selectbox("Theme (filters the article list)", ["All themes"] + ALL_THEMES,
                             key="theme_select")
theme = None if theme == "All themes" else theme


def apply_filters(data, use_outlet=True, use_year=True, use_author=True, use_theme=False):
    mask = pd.Series(True, index=data.index)
    if use_outlet:
        mask &= data["outlet_name"].isin(outlet_choice)
    if use_year:
        mask &= data["year"].isin(year_choice)
    if use_author and author:
        mask &= data["authors"].apply(lambda a: author in a)
    if use_theme and theme:
        mask &= data["themes"].apply(lambda t: theme in t)
    return data[mask]


view = apply_filters(df)


# ---------------------------------------------------------------- header
st.title("ETH outlets: themes and authors")

scope = " · ".join([
    ", ".join(outlet_choice) if len(outlet_choice) < len(OUTLET_NAMES) else "All outlets",
    year_pick,
    author or "all authors",
])

if view.empty:
    st.info(f"{scope}: no articles match these filters.")
    st.stop()

theme_counts = view.explode("themes")["themes"].value_counts()
if len(theme_counts):
    st.markdown(
        f"{scope}. The most common theme is **{theme_counts.index[0]}**, "
        f"on **{theme_counts.iloc[0] / len(view):.0%}** of articles."
    )

with st.expander("How to read this dashboard"):
    st.markdown(
        "- **Screen**: This dashboard is best used on a large screen (as opposed to table, laptop, smartphone) \n"
        "- **Potential errors**: This dashboard has a few imprecisions and is only a side project and should also be read like one \n"
        "- **Theme share**: share of articles tagged with a theme. Articles carry several themes, "
        "so shares add up to more than 100%.\n"
        "- **Authors**: articles with no author count under *unknown author*; each co-author is "
        "credited with the whole article.\n"
        "- **Author-specific stats**: Authors can either be selected on the sidebar are from the author table below. \n"
        "- **Issue / month**: ETH News and Life are dated by month, Globe by issue number.\n"
        "- **Themes**: ETH News themes come from editors' tags; Globe and Life themes are "
        "predicted by a language model trained on ETH News (see the blue note below)."
    )

st.info(THEME_NOTE, icon="ℹ️")

k = st.columns(4)
k[0].metric("Articles", f"{len(view):,}")
k[1].metric("Words per article", f"{round(view['n_words'].mean()):,}")
k[2].metric("Themes covered", f"{len(theme_counts):,}")
k[3].metric("Top theme", theme_counts.index[0] if len(theme_counts) else "—")


# ---------------------------------------------------------------- charts
# theme -> area, for colouring and grouping
THEME_AREA = {t: area for area, themes in THEME_CATEGORIES.items() for t in themes}
AREA_COLORS = dict(zip(THEME_CATEGORIES.keys(),
                       ["#D1495B", "#2E9E6B", "#2F6FDE", "#8E5EA2", "#E0A31F"]))


def theme_counts_for(data):
    """One row per theme: theme, area, articles, share of the articles in `data`."""
    t = (data.explode("themes").dropna(subset=["themes"])
         .groupby("themes").size().rename("articles").reset_index()
         .rename(columns={"themes": "theme"}))
    t["area"] = t["theme"].map(THEME_AREA).fillna("Other")
    t["share"] = t["articles"] / len(data)
    return t


def draw_treemap(d, n_articles, title, key):
    """Treemap of themes grouped by area. d: rows with theme, area, articles, share."""
    area_totals = d.groupby("area")["articles"].sum()
    root = f"{title} · {n_articles:,} articles"

    # Build the tree by hand: root -> area -> theme
    ids, labels, parents, values, colors, texts, hovers = [], [], [], [], [], [], []
    ids.append("root"); labels.append(root); parents.append("")
    values.append(int(area_totals.sum())); colors.append("rgba(0,0,0,0)")
    texts.append(""); hovers.append(root)
    for area, total in area_totals.items():
        ids.append(area); labels.append(area); parents.append("root")
        values.append(int(total)); colors.append(AREA_COLORS.get(area, "#999999"))
        texts.append(""); hovers.append(area)
    for _, r in d.iterrows():
        ids.append(f"{r['area']}/{r['theme']}"); labels.append(r["theme"])
        parents.append(r["area"]); values.append(int(r["articles"]))
        colors.append(AREA_COLORS.get(r["area"], "#999999"))
        texts.append(f"{r['share']:.0%} of articles")
        hovers.append(f"{r['theme']}<br>{r['articles']:,} of {n_articles:,} articles "
                      f"({r['share']:.1%})")

    # Quick look: top 5 themes as a simple bar chart
    top5 = d.sort_values(["articles", "theme"], ascending=[False, True]).head(5)
    bar = go.Figure(go.Bar(
        x=top5["share"], y=top5["theme"], orientation="h",
        marker=dict(color=[AREA_COLORS.get(a, "#999999") for a in top5["area"]], cornerradius=3),
        text=[f"{v:.0%}" for v in top5["share"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11),
        customdata=top5["articles"],
        hovertemplate="%{y}<br>%{customdata:,} of " + f"{n_articles:,}" +
                      " articles (%{x:.1%})<extra></extra>",
    ))
    bar.update_layout(
        title=dict(text=f"Top 5 themes · {title}", font=dict(size=12), x=0, xanchor="left",
                   y=1, yanchor="top", pad=dict(t=0)),
        height=115, margin=dict(l=0, r=40, t=20, b=0), bargap=0.45,
        font=dict(size=11),
        xaxis=dict(visible=False, range=[0, top5["share"].max() * 1.2 if len(top5) else 1]),
        yaxis=dict(autorange="reversed", title=None),
    )
    st.plotly_chart(bar, width="stretch", key=f"{key}_top5")

    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total", text=texts, hovertext=hovers,
        texttemplate="<b>%{label}</b><br>%{text}",
        hovertemplate="%{hovertext}<extra></extra>",
        marker=dict(colors=colors, cornerradius=3),
        pathbar=dict(visible=True), sort=True,
    ))
    fig.update_layout(height=640, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, width="stretch", key=key)


def treemap_tabs(groups, all_label, key_prefix):
    """Tabs with an 'All ...' treemap first (if all_label is set and there is more than
    one group), then one tab per group."""
    if view.explode("themes")["themes"].dropna().empty:
        st.caption("No themes for these filters.")
        return
    show_all = bool(all_label) and len(groups) > 1
    tabs = st.tabs(([all_label] if show_all else []) + [name for name, _ in groups])
    if show_all:
        with tabs[0]:
            draw_treemap(theme_counts_for(view), len(view), all_label, f"{key_prefix}_all")
    for tab, (name, data) in zip(tabs[1:] if show_all else tabs, groups):
        with tab:
            draw_treemap(theme_counts_for(data), len(data), name, f"{key_prefix}_{name}")


TREEMAP_NOTE = ("Bigger box = more articles on that theme; colours group themes into areas. "
                "An article with several themes counts in each of them. "
                "Globe and Life themes are predicted by a model.")

# Share of articles per outlet: one simple stacked bar across the full width
outlet_n = view["outlet_name"].value_counts().reindex(list(OUTLET_NAMES.values())).dropna()
share_fig = go.Figure()
for outlet_name, n in outlet_n.items():
    share = n / len(view)
    share_fig.add_trace(go.Bar(
        x=[share], y=["Articles"], orientation="h", name=outlet_name,
        marker=dict(color=OUTLET_COLORS.get(outlet_name)),
        # narrow slices get the name and share on two lines, so the label stays upright
        text=f"{outlet_name} {share:.0%}" if share >= 0.08 else f"{outlet_name}<br>{share:.0%}",
        textposition="inside", insidetextanchor="middle", textangle=0,
        textfont=dict(color="white", size=13),
        hovertemplate=f"{outlet_name}: {int(n):,} of {len(view):,} articles ({share:.1%})<extra></extra>",
    ))
share_fig.update_layout(
    barmode="stack", height=70, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
    xaxis=dict(visible=False, range=[0, 1]), yaxis=dict(visible=False),
)
st.caption("Share of articles by outlet, for the years and author picked")
st.plotly_chart(share_fig, width="stretch", key="outlet_share_bar")

left, right = st.columns(2)

# Themes per outlet: treemaps
with left:
    st.subheader("Themes per outlet")
    st.caption("One map per outlet, for the years and author picked. " + TREEMAP_NOTE)
    outlet_groups = [(o, view[view["outlet_name"] == o])
                     for o in OUTLET_NAMES.values() if (view["outlet_name"] == o).any()]
    treemap_tabs(outlet_groups, "All outlets", "treemap_outlet")

# Themes per year: treemaps
with right:
    st.subheader("Themes per year")
    st.caption("One map per year, for the outlets and author picked. " + TREEMAP_NOTE)
    year_groups = [(str(y), view[view["year"] == y])
                   for y in sorted(view["year"].unique(), reverse=True)]
    treemap_tabs(year_groups, None, "treemap_year")  # "All outlets" on the left covers all years

st.caption("Each tab shows the top 5 themes, then all themes as a treemap. "
           "In the treemaps: click an area to zoom in, click the top bar to zoom out.")


# ---------------------------------------------------------------- authors
st.subheader("Authors")
st.caption("Articles per author for the outlets and years picked. Click a row or pick an author in the sidebar to see their profile.")

base_authors = base.explode("authors").rename(columns={"authors": "author"})


def top3(series):
    counts = pd.Series([t for ts in series for t in ts]).value_counts()
    return ", ".join(counts.index[:3])


authors_table = (
    base_authors.groupby("author")
    .agg(articles=("title", "size"),
         words=("n_words", "sum"),
         top_themes=("themes", top3),
         outlets=("outlet_name", lambda s: ", ".join(sorted(s.unique()))),
         first_year=("year", "min"),
         last_year=("year", "max"))
    .reset_index()
)
# Most articles first, "unknown author" always last
authors_table["_unknown"] = authors_table["author"] == UNKNOWN
authors_table = (authors_table
                 .sort_values(["_unknown", "articles", "words"], ascending=[True, False, False])
                 .drop(columns="_unknown"))

search = st.text_input("Search authors", key="author_search")
if search:
    authors_table = authors_table[authors_table["author"].str.contains(search, case=False, regex=False)]
authors_table = authors_table.reset_index(drop=True)

# Remember which author sits in which row, so a click can be translated into a name
st.session_state["_authors_shown"] = authors_table["author"].tolist()


def pick_author_from_table():
    """Clicking a row selects that author in the sidebar; clicking it again clears it."""
    rows = st.session_state["authors_table"].selection.rows
    shown = st.session_state.get("_authors_shown", [])
    if rows and rows[0] < len(shown):
        st.session_state["author_select"] = shown[rows[0]]
    else:
        st.session_state["author_select"] = "All authors"


st.caption("Click an author's row to select them in the sidebar.")
st.dataframe(authors_table, width="stretch", hide_index=True, height=420,
             column_config={"words": st.column_config.NumberColumn(format="%d")},
             key="authors_table", on_select=pick_author_from_table,
             selection_mode="single-row")


# ---------------------------------------------------------------- articles
st.subheader("Articles")
st.caption("Every article matching the filters (including the theme), newest first.")

articles = apply_filters(df, use_theme=True).sort_values(
    ["year", "period_rank"], ascending=False
)
q = st.text_input("Search titles, authors or themes", key="article_search")
if q:
    hay = articles["title"] + " " + articles["author_str"] + " " + articles["theme_str"]
    articles = articles[hay.str.contains(q, case=False, regex=False)]

st.dataframe(
    articles[["year", "issue_month", "url", "title", "author_str", "outlet_name",
              "theme_str", "n_words"]],
    width="stretch", hide_index=True, height=480,
    column_config={
        "issue_month": "Issue / month",
        "outlet_name": "Outlet",
        "author_str": "Authors",
        "theme_str": "Themes",
        "n_words": st.column_config.NumberColumn("Words", format="%d"),
        "url": st.column_config.LinkColumn("Link", display_text="Open"),
    },
)

# ---------------------------------------------------------------- theme categories
st.subheader("Theme categories")
st.caption(
    "What each theme means. For ETH News, each theme combines the editors' original tags listed "
    "here. For Globe and Life, the model assigned these same themes by reading the article."
)

theme_rows = []
for area, themes in THEME_CATEGORIES.items():
    for theme_name, tags in themes.items():
        n_articles = int(df["themes"].apply(lambda ts: theme_name in ts).sum())
        theme_rows.append({
            "Area": area,
            "Theme": theme_name,
            "Includes these ETH News tags": ", ".join(tags),
            "Articles (all outlets)": n_articles,
        })
theme_table = pd.DataFrame(theme_rows)

area_tabs = st.tabs(list(THEME_CATEGORIES.keys()))
for tab, area in zip(area_tabs, THEME_CATEGORIES.keys()):
    with tab:
        st.dataframe(
            theme_table[theme_table["Area"] == area].drop(columns="Area"),
            width="stretch", hide_index=True,
            column_config={
                "Includes these ETH News tags": st.column_config.TextColumn(width="large"),
                "Articles (all outlets)": st.column_config.NumberColumn(format="%d"),
            },
        )
