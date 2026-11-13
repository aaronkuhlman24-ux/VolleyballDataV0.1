import os
import sqlite3
import urllib.request
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NCAA & Pro Volleyball Analytics",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "volleyball_stats.db")
REMOTE_DB_URL = "https://github.com/aaronkuhlman24-ux/VolleyballDataV0.1/releases/download/v1%2C0/volleyball_stats.db"

# Custom CSS for deep navy header cards, badges, and clean table polish
st.markdown("""
<style>
    .player-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #F8FAFC;
        padding: 1.4rem 1.8rem;
        border-radius: 12px;
        margin-bottom: 0.75rem;
        border-left: 6px solid #38BDF8;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    }
    .player-card h2 {
        margin: 0 0 0.35rem 0;
        color: #FFFFFF;
        font-size: 1.75rem;
        letter-spacing: -0.02em;
    }
    .player-meta {
        color: #CBD5E1;
        font-size: 0.95rem;
        margin-bottom: 0.2rem;
    }
    .badge {
        display: inline-block;
        background-color: #1E3A8A;
        color: #DBEAFE;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.4rem;
        border: 1px solid #3B82F6;
    }
    .badge-status {
        background-color: #065F46;
        color: #D1FAE5;
        border: 1px solid #10B981;
    }
</style>
""", unsafe_allow_html=True)

STAT_HELP = {
    "overall_ke": "Kills minus attack errors, divided by total attack attempts.",
    "overall_wke": "Actual kill efficiency minus expected kill efficiency based on incoming pass quality.",
    "wKE_plus": "League-adjusted weighted kill efficiency scaled so 100 equals the seasonal positional average.",
    "ke_on_perf_pass": "Kill efficiency on attacks following a perfect (#) pass or dig.",
    "ke_on_pos_pass": "Kill efficiency on attacks following a positive (+) pass or dig.",
    "ke_on_med_pass": "Kill efficiency on attacks following a medium (!) pass or dig.",
    "ke_on_poor_pass": "Kill efficiency on attacks following a poor (- or /) out-of-system pass.",
    "fbso_wke": "Weighted kill efficiency during First-Ball Side-Out (off serve receive) rallies.",
    "trans_wke": "Weighted kill efficiency during Transition rallies (after a dig or freeball).",
    "ace_rate": "Service aces divided by total serves attempted.",
    "serve_error_rate": "Service errors divided by total serves attempted.",
    "xBP": "Expected Break Point value per serve based on aces, errors, and forced opponent pass ratings.",
    "xBP_plus": "League-adjusted Expected Break Point value scaled so 100 equals the seasonal positional average.",
    "reception_rating_0_3": "Average serve-receive pass rating on a 0-to-3 scale (#=3, +=2, !=1, -//=0).",
    "rec_perf_rate": "Percentage of serve-receive attempts rated as perfect (3-point pass).",
    "rec_pos_rate": "Percentage of serve-receive attempts rated as positive (2-point pass).",
    "rec_med_rate": "Percentage of serve-receive attempts rated as medium (1-point pass).",
    "rec_poor_rate": "Percentage of serve-receive attempts resulting in an overpass or error (0-point pass).",
    "dig_rating_0_3": "Average dig control rating on a 0-to-3 scale (#=3, +=2, !=1, -//=0).",
    "dig_perf_rate": "Percentage of dig attempts rated as perfect control (3-point dig).",
    "dig_pos_rate": "Percentage of dig attempts rated as positive control (2-point dig).",
    "dig_med_rate": "Percentage of dig attempts rated as medium control (1-point dig).",
    "dig_poor_rate": "Percentage of dig attempts resulting in an overpass or error (0-point dig).",
    "freeball_rating_0_3": "Average freeball pass rating on a 0-to-3 scale (#=3, +=2, !=1, -//=0).",
    "fb_perf_rate": "Percentage of freeball passes rated as perfect (3-point pass).",
    "fb_pos_rate": "Percentage of freeball passes rated as positive (2-point pass).",
    "fb_med_rate": "Percentage of freeball passes rated as medium (1-point pass).",
    "fb_poor_rate": "Percentage of freeball passes resulting in an overpass or error (0-point pass).",
    "blocks_per_set": "Total solo and assisted stuff blocks divided by sets played.",
    "APAA": "Attacking Points Above Average relative to positional baseline.",
    "SetPAA": "Setting Points Above Average relative to positional baseline.",
    "PPAA": "Passing & Defensive Points Above Average relative to positional baseline.",
    "ServePAA": "Serving Points Above Average relative to positional baseline.",
    "BPAA": "Blocking Points Above Average relative to positional baseline.",
    "Total_PAA": "Cumulative Points Above Average across all volleyball skill phases.",
}


def is_valid_sqlite(path):
    if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
        return False
    with open(path, "rb") as f:
        return f.read(16) == b"SQLite format 3\x00"


def ensure_database():
    if is_valid_sqlite(DB_PATH):
        return
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if not REMOTE_DB_URL:
        return

    with st.spinner("Downloading volleyball database (first boot only, takes ~15–25 seconds)..."):
        tmp_path = DB_PATH + ".tmp"
        try:
            req = urllib.request.Request(
                REMOTE_DB_URL,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req) as resp, open(tmp_path, "wb") as out_file:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out_file.write(chunk)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            st.error(f"Database download failed ({e}). URL tried: {REMOTE_DB_URL}")
            st.stop()

        if not is_valid_sqlite(tmp_path):
            os.remove(tmp_path)
            st.error("Downloaded file is not a valid SQLite database. Verify that REMOTE_DB_URL points directly to the published release asset (.db) and that the release is not a Draft.")
            st.stop()

        os.replace(tmp_path, DB_PATH)

def get_connection():
    ensure_database()
    if os.path.exists(DB_PATH):
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(ttl=300)
def get_existing_tables():
    conn = get_connection()
    df = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    conn.close()
    return set(df["name"].tolist())


@st.cache_data(ttl=300)
def get_table_columns(table_name):
    conn = get_connection()
    df = pd.read_sql(f"PRAGMA table_info({table_name})", conn)
    conn.close()
    return set(df["name"].tolist())


@st.cache_data(ttl=300)
def get_player_list():
    conn = get_connection()
    df = pd.read_sql(
        "SELECT DISTINCT player_name FROM season_stats WHERE player_name IS NOT NULL AND player_name != '' ORDER BY player_name ASC",
        conn
    )
    conn.close()
    return df["player_name"].tolist()


@st.cache_data(ttl=300)
def get_filter_options():
    conn = get_connection()
    cols = get_table_columns("season_stats")
    seasons = pd.read_sql("SELECT DISTINCT season FROM season_stats ORDER BY season DESC", conn)["season"].tolist()
    positions = ["All"] + pd.read_sql(
        "SELECT DISTINCT position FROM season_stats WHERE position IS NOT NULL AND position != 'Unknown' ORDER BY position ASC",
        conn
    )["position"].tolist()
    leagues = ["All"]
    if "league" in cols:
        leagues += pd.read_sql("SELECT DISTINCT league FROM season_stats WHERE league IS NOT NULL ORDER BY league ASC", conn)["league"].tolist()
    confs = ["All"]
    if "conference" in cols:
        confs += pd.read_sql("SELECT DISTINCT conference FROM season_stats WHERE conference IS NOT NULL AND conference != 'Unknown' ORDER BY conference ASC", conn)["conference"].tolist()
    team_col = "canonical_team" if "canonical_team" in cols else "primary_team"
    teams = pd.read_sql(f"SELECT DISTINCT {team_col} AS t FROM season_stats WHERE {team_col} IS NOT NULL ORDER BY t ASC", conn)["t"].tolist()
    conn.close()
    return seasons, positions, leagues, confs, teams


@st.cache_data(ttl=300)
def compute_player_comps(target_pid, target_pos, target_season):
    """Computes Top 5 most similar players within the same position using standardized z-scores."""
    conn = get_connection()
    cols = get_table_columns("season_stats")
    id_col = "canonical_player_id" if "canonical_player_id" in cols else "player_id"
    team_col = "canonical_team" if "canonical_team" in cols else "primary_team"

    metric_candidates = [
        "overall_wke", "fbso_wke", "trans_wke", "xBP",
        "reception_rating_0_3", "dig_rating_0_3", "blocks_per_set"
    ]
    avail_metrics = [m for m in metric_candidates if m in cols]
    if len(avail_metrics) < 3:
        conn.close()
        return pd.DataFrame()

    query = f"""
        SELECT {id_col} AS pid, player_name, {team_col} AS team, season, position, sets_played, overall_att,
               {', '.join(avail_metrics)}
        FROM season_stats
        WHERE position = ? AND sets_played >= 15
    """
    df = pd.read_sql(query, conn, params=(target_pos,))
    conn.close()

    if df.empty:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    for m in avail_metrics:
        df[m] = pd.to_numeric(df[m], errors="coerce")

  target_rows = df[(df["pid"] == target_pid) & (df["season"] == target_season)]
    if target_rows.empty:
        target_rows = df[df["pid"] == target_pid]
    if target_rows.empty:
        return pd.DataFrame()

   for m in avail_metrics:
        df[m] = pd.to_numeric(df[m], errors="coerce")

    target_rows = df[(df["pid"] == target_pid) & (df["season"] == target_season)]
    if target_rows.empty:
        target_rows = df[df["pid"] == target_pid]
    if target_rows.empty:
        return pd.DataFrame()

    t_vec = target_rows.iloc[-1]
    peers = df[df["pid"] != target_pid].copy()
    if peers.empty:
        return pd.DataFrame()

    stds = peers[avail_metrics].std().replace(0, 1).fillna(1).astype(float)
    means = peers[avail_metrics].mean().fillna(0).astype(float)

    z_peers = ((peers[avail_metrics].fillna(means) - means) / stds).astype(float)
    z_target = ((t_vec[avail_metrics].fillna(means) - means) / stds).astype(float)

    sq_sum = ((z_peers - z_target) ** 2).sum(axis=1).astype(float)
    dist = np.sqrt(sq_sum)
    peers["Similarity"] = (100 / (1 + (dist / len(avail_metrics)))).round(1)

    top_comps = (
        peers.sort_values(by="Similarity", ascending=False)
        .drop_duplicates(subset=["pid"])
        .head(5)
    )
    out_cols = ["player_name", "team", "season", "Similarity"] + avail_metrics[:3]
    return top_comps[out_cols]

def build_column_config(df_cols):
    cfg = {}
    for c in df_cols:
        if c in STAT_HELP:
            fmt = "%.1f" if c in ["wKE_plus", "xBP_plus", "APAA", "SetPAA", "PPAA", "ServePAA", "BPAA", "Total_PAA"] else (
                "%.2f%%" if c.endswith("_rate") else "%.4f"
            )
            cfg[c] = st.column_config.NumberColumn(label=c, help=STAT_HELP[c], format=fmt)
    return cfg


def download_csv_button(df, filename, key):
    if df is not None and not df.empty:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Table as CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            key=key
        )


def navigate_to_player(player_name):
    st.session_state["player_search_box"] = player_name
    st.query_params["player"] = player_name


def navigate_to_team(team_name, season_val=None):
    st.session_state["hub_team"] = team_name
    if season_val is not None:
        st.session_state["hub_season"] = int(season_val)
    st.session_state["active_nav"] = "🏟️ Team & Conference Hubs"
    st.query_params["team"] = team_name


# ---------------------------------------------------------
# HEADER, GLOSSARY & NAVIGATION
# ---------------------------------------------------------
st.title("🏐 NCAA & Pro Volleyball Analytics")

ensure_database()
if not os.path.exists(DB_PATH):
    st.error(f"Database not found at `{DB_PATH}`. Run `compile_unified_database.py` first.")
    st.stop()

tables = get_existing_tables()
season_cols = get_table_columns("season_stats")
seasons_list, positions_list, leagues_list, confs_list, teams_list = get_filter_options()
players = get_player_list()

# Sync query params into session state on initial load
qp_player = st.query_params.get("player", None)
if qp_player and qp_player in players and "player_search_box" not in st.session_state:
    st.session_state["player_search_box"] = qp_player

qp_team = st.query_params.get("team", None)
if qp_team and qp_team in teams_list and "hub_team" not in st.session_state:
    st.session_state["hub_team"] = qp_team
    if "active_nav" not in st.session_state:
        st.session_state["active_nav"] = "🏟️ Team & Conference Hubs"

with st.expander("📖 Stat Glossary & Formula Guide (Hover over any column header for quick tooltips)"):
    g_cols = st.columns(3)
    items = list(STAT_HELP.items())
    chunk = (len(items) + 2) // 3
    for idx, col in enumerate(g_cols):
        with col:
            for k, v in items[idx * chunk:(idx + 1) * chunk]:
                st.markdown(f"**`{k}`**: {v}")

NAV_OPTIONS = [
    "🔍 Player Profile & Splits",
    "🏆 Positional & PAA Leaderboards",
    "🏟️ Team & Conference Hubs",
    "🔮 Projections & Portal / FA Search"
]
if "active_nav" not in st.session_state:
    st.session_state["active_nav"] = NAV_OPTIONS[0]

active_view = st.segmented_control(
    "Navigation",
    options=NAV_OPTIONS,
    key="active_nav",
    label_visibility="collapsed"
)
if not active_view:
    active_view = NAV_OPTIONS[0]

st.divider()

# =========================================================
# VIEW 1: PLAYER PROFILE, SPLITS, GAME LOGS & COMPS
# =========================================================
if active_view == "🔍 Player Profile & Splits":
    selected_player = st.selectbox(
        "Search Player Name",
        options=players,
        key="player_search_box"
    )

    if selected_player:
        st.query_params["player"] = selected_player
        conn = get_connection()
        p_seasons = pd.read_sql(
            "SELECT * FROM season_stats WHERE player_name = ? ORDER BY season ASC",
            conn,
            params=(selected_player,)
        )
        p_career = pd.read_sql(
            "SELECT * FROM career_stats WHERE player_name = ? LIMIT 1",
            conn,
            params=(selected_player,)
        ) if "career_stats" in tables else pd.DataFrame()

        if not p_seasons.empty:
            latest = p_seasons.iloc[-1]
            pid_col = "canonical_player_id" if "canonical_player_id" in p_seasons.columns else "player_id"
            active_pid = latest[pid_col]
            team_col_p = "canonical_team" if "canonical_team" in p_seasons.columns else "primary_team"
            team_disp = latest.get(team_col_p) or "Unknown Team"
            conf_disp = latest.get("conference", "Unknown Conf")
            league_disp = latest.get("league", "NCAA")
            status_disp = latest.get("roster_status", "Active")
            jersey_disp = latest.get("player_number", "")
            pos_disp = latest.get("position", "")
            class_disp = latest.get("year_in_school", "")
            path_disp = p_career.iloc[0]["career_school_path"] if (not p_career.empty and "career_school_path" in p_career.columns) else team_disp

            h_in = latest.get("height_inches")
            if pd.isna(h_in) and not p_career.empty and "height_inches" in p_career.columns:
                h_in = p_career.iloc[0]["height_inches"]
            height_str = f" &nbsp;•&nbsp; <strong>Height:</strong> {int(h_in)//12}'{int(h_in)%12}\"" if pd.notna(h_in) and h_in > 0 else ""

            st.markdown(f"""
            <div class="player-card">
                <div>
                    <span class="badge">{league_disp}</span>
                    <span class="badge">{conf_disp}</span>
                    <span class="badge badge-status">{status_disp}</span>
                </div>
                <h2>{selected_player} <span style="font-weight:400; color:#94A3B8;">| {'#' + str(jersey_disp) + ' ' if jersey_disp else ''}{pos_disp} ({class_disp})</span></h2>
                <div class="player-meta"><strong>Current Team:</strong> {team_disp}{height_str} &nbsp;•&nbsp; <strong>Career Path:</strong> {path_disp}</div>
            </div>
            """, unsafe_allow_html=True)

            # Clickable Team Roster Buttons for every team the player played on
            played_teams_df = (
                p_seasons[[team_col_p, "season", "league"]]
                .dropna(subset=[team_col_p])
                .drop_duplicates(subset=[team_col_p], keep="last")
            )
            if not played_teams_df.empty:
                t_btn_cols = st.columns([1.4] + [1.2] * len(played_teams_df) + [max(1.0, 5.0 - 1.2 * len(played_teams_df))])
                with t_btn_cols[0]:
                    st.caption("View Team Roster:")
                for idx_t, (_, trow) in enumerate(played_teams_df.iterrows()):
                    t_name = trow[team_col_p]
                    t_yr = int(trow["season"])
                    if t_name in teams_list:
                        with t_btn_cols[idx_t + 1]:
                            st.button(
                                f"🏟️ {t_name} ({t_yr})",
                                key=f"jump_team_{active_pid}_{t_name}_{t_yr}",
                                on_click=navigate_to_team,
                                args=(t_name, t_yr),
                                use_container_width=True
                            )

            # Top KPI Callout Row
            if not p_career.empty:
                car = p_career.iloc[0]
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                k1.metric("Career wKE", f"{car.get('career_overall_wke', 0.0):.4f}")
                k2.metric("Career xBP", f"{car.get('career_xBP', 0.0):.4f}" if pd.notna(car.get('career_xBP')) else "N/A")
                k3.metric("Rec Rating (0-3)", f"{car.get('career_rec_rating_0_3', 0.0):.4f}")
                k4.metric("Dig Rating (0-3)", f"{car.get('career_dig_rating_0_3', 0.0):.4f}" if pd.notna(car.get('career_dig_rating_0_3')) else "N/A")
                k5.metric("Blocks / Set", f"{car.get('career_blocks_per_set', 0.0):.4f}")
                paa_val = car.get("career_Total_PAA")
                k6.metric("Career Total PAA", f"{paa_val:.1f}" if pd.notna(paa_val) else "N/A")

            # -------------------------------------------------
            # STANDARD GRID + PASS-TYPE SWING SPLITS + PROJECTION ROWS
            # -------------------------------------------------
            st.markdown("#### Season Progression & Pass-Type Swing Splits")
            base_cols = [
                "season", "league", "canonical_team", "year_in_school", "sets_played",
                "overall_att", "overall_ke", "overall_wke", "wKE_plus",
                "ke_on_perf_pass", "ke_on_pos_pass", "ke_on_med_pass", "ke_on_poor_pass",
                "fbso_wke", "trans_wke",
                "serves_total", "xBP", "xBP_plus", "ace_rate",
                "reception_rating_0_3", "dig_rating_0_3", "freeball_rating_0_3",
                "blocks_per_set", "APAA", "SetPAA", "PPAA", "ServePAA", "BPAA", "Total_PAA"
            ]
            valid_base = [c for c in base_cols if c in p_seasons.columns]
            grid_df = p_seasons[valid_base].copy()
            if "canonical_team" in grid_df.columns:
                grid_df = grid_df.rename(columns={"canonical_team": "team"})
            grid_df["season"] = grid_df["season"].astype(str)

            next_yr = int(p_seasons["season"].max()) + 1
            proj_df = pd.DataFrame()
            if "projections" in tables:
                proj_df = pd.read_sql(
                    "SELECT * FROM projections WHERE player_id = ? AND target_season = ?",
                    conn,
                    params=(active_pid, next_yr)
                )

            proj_rows = []
            for tier_label in [f"{next_yr} Proj (10th - Floor)", f"{next_yr} Proj (50th - Avg)", f"{next_yr} Proj (90th - Ceiling)"]:
                prow = {c: np.nan for c in grid_df.columns}
                prow["season"] = tier_label
                if "league" in prow:
                    prow["league"] = league_disp
                if "team" in prow:
                    prow["team"] = team_disp
                if "year_in_school" in prow:
                    prow["year_in_school"] = "Proj"
                if not proj_df.empty:
                    match_t = proj_df[proj_df["percentile_tier"].str.contains(tier_label.split("(")[1][:4], na=False)]
                    if not match_t.empty:
                        mr = match_t.iloc[0]
                        if "overall_wke" in prow: prow["overall_wke"] = mr.get("proj_wke", np.nan)
                        if "xBP" in prow: prow["xBP"] = mr.get("proj_xbp", np.nan)
                        if "reception_rating_0_3" in prow: prow["reception_rating_0_3"] = mr.get("proj_rec_rating", np.nan)
                        if "dig_rating_0_3" in prow: prow["dig_rating_0_3"] = mr.get("proj_dig_rating", np.nan)
                        if "blocks_per_set" in prow: prow["blocks_per_set"] = mr.get("proj_blocks_per_set", np.nan)
                        if "Total_PAA" in prow: prow["Total_PAA"] = mr.get("proj_Total_PAA", np.nan)
                proj_rows.append(prow)

            combined_grid = pd.concat([grid_df, pd.DataFrame(proj_rows)], ignore_index=True)

            st.dataframe(
                combined_grid,
                use_container_width=True,
                hide_index=True,
                column_config=build_column_config(combined_grid.columns)
            )
            download_csv_button(combined_grid, f"{selected_player.replace(' ', '_')}_season_stats.csv", "dl_season_grid")

            # -------------------------------------------------
            # PASS QUALITY RATES BY SKILL (RECEIVE / DIG / FREEBALL)
            # -------------------------------------------------
            pass_dist_cols = [
                "season", "league",
                "reception_attempts", "reception_rating_0_3", "rec_perf_rate", "rec_pos_rate", "rec_med_rate", "rec_poor_rate",
                "dig_attempts", "dig_rating_0_3", "dig_perf_rate", "dig_pos_rate", "dig_med_rate", "dig_poor_rate",
                "freeball_attempts", "freeball_rating_0_3", "fb_perf_rate", "fb_pos_rate", "fb_med_rate", "fb_poor_rate"
            ]
            avail_pass_cols = [c for c in pass_dist_cols if c in p_seasons.columns]
            if len(avail_pass_cols) > 4:
                with st.expander("📊 Pass Quality Breakdown by Skill (Serve Receive / Digs / Freeballs)", expanded=True):
                    pass_df = p_seasons[avail_pass_cols].copy()
                    for rate_c in [c for c in avail_pass_cols if c.endswith("_rate")]:
                        pass_df[rate_c] = (pass_df[rate_c] * 100).round(2)
                    st.dataframe(
                        pass_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config=build_column_config(pass_df.columns)
                    )

            # -------------------------------------------------
            # CLICKABLE CHECKMARK FILTER GRID (GRANULAR SPLITS)
            # -------------------------------------------------
            st.markdown("#### Interactive Situational & Positional Splits")
            if "granular_splits" in tables:
                with st.popover("🎛️ Filter Splits (Swing Zone, Pass Quality, Home/Away, Conference)", use_container_width=False):
                    f_col1, f_col2 = st.columns(2)
                    with f_col1:
                        sel_seasons_sp = st.multiselect(
                            "Seasons",
                            options=sorted(p_seasons["season"].unique().tolist()),
                            default=sorted(p_seasons["season"].unique().tolist()),
                            key="sp_seasons"
                        )
                        st.markdown("**Location**")
                        chk_home = st.checkbox("Home Matches", value=True, key="chk_home")
                        chk_away = st.checkbox("Away Matches", value=True, key="chk_away")

                        st.markdown("**Match Type**")
                        chk_inconf = st.checkbox("In-Conference", value=True, key="chk_inconf")
                        chk_outconf = st.checkbox("Out-of-Conference", value=True, key="chk_outconf")

                    with f_col2:
                        st.markdown("**Swing Position / Zone**")
                        chk_left = st.checkbox("Left Pin (OH)", value=True, key="chk_left")
                        chk_mid = st.checkbox("Middle (MB)", value=True, key="chk_mid")
                        chk_right = st.checkbox("Right Pin (OPP)", value=True, key="chk_right")
                        chk_back = st.checkbox("Back-Row / Pipe", value=True, key="chk_back")
                        chk_other_z = st.checkbox("Other / Non-Attack Touches", value=True, key="chk_other_z")

                        st.markdown("**Incoming Pass / Set Quality**")
                        chk_p_perf = st.checkbox("Perfect (#)", value=True, key="chk_p_perf")
                        chk_p_pos = st.checkbox("Positive (+)", value=True, key="chk_p_pos")
                        chk_p_med = st.checkbox("Medium (!)", value=True, key="chk_p_med")
                        chk_p_poor = st.checkbox("Poor (- /)", value=True, key="chk_p_poor")
                        chk_p_unk = st.checkbox("Unrated / Serve / Block", value=True, key="chk_p_unk")

                ha_list = [x for x, flag in [("Home", chk_home), ("Away", chk_away)] if flag]
                conf_list = [x for x, flag in [("In-Conference", chk_inconf), ("Out-of-Conference", chk_outconf)] if flag]
                zone_list = [
                    x for x, flag in [
                        ("Left", chk_left), ("Middle", chk_mid), ("Right", chk_right),
                        ("BackRow", chk_back), ("Other", chk_other_z), ("N/A", chk_other_z)
                    ] if flag
                ]
                pass_list = [
                    x for x, flag in [
                        ("perf", chk_p_perf), ("pos", chk_p_pos), ("med", chk_p_med),
                        ("poor", chk_p_poor), ("unknown", chk_p_unk), ("N/A", chk_p_unk)
                    ] if flag
                ]

                if sel_seasons_sp and ha_list and conf_list and zone_list and pass_list:
                    sp_query = f"""
                        SELECT season,
                               SUM(att) AS att, SUM(kills) AS kills, SUM(errors) AS errors,
                               SUM(serves) AS serves, SUM(aces) AS aces, SUM(serve_errors) AS serve_errors,
                               SUM(xbp_pts) AS xbp_pts,
                               SUM(rec_att) AS rec_att, SUM(rec_pts) AS rec_pts,
                               SUM(dig_att) AS dig_att, SUM(dig_pts) AS dig_pts,
                               SUM(fb_att) AS fb_att, SUM(fb_pts) AS fb_pts,
                               SUM(blocks) AS blocks
                        FROM granular_splits
                        WHERE canonical_player_id = ?
                          AND season IN ({','.join(['?'] * len(sel_seasons_sp))})
                          AND home_away IN ({','.join(['?'] * len(ha_list))})
                          AND is_conference IN ({','.join(['?'] * len(conf_list))})
                          AND swing_zone IN ({','.join(['?'] * len(zone_list))})
                          AND pass_quality IN ({','.join(['?'] * len(pass_list))})
                        GROUP BY season
                        ORDER BY season ASC
                    """
                    sp_params = [active_pid] + sel_seasons_sp + ha_list + conf_list + zone_list + pass_list
                    sp_res = pd.read_sql(sp_query, conn, params=sp_params)
                    if not sp_res.empty:
                        sp_res["overall_ke"] = np.where(sp_res["att"] > 0, ((sp_res["kills"] - sp_res["errors"]) / sp_res["att"]).round(4), 0.0)
                        sp_res["xBP"] = np.where(sp_res["serves"] > 0, (sp_res["xbp_pts"] / sp_res["serves"]).round(4), 0.0)
                        sp_res["reception_rating_0_3"] = np.where(sp_res["rec_att"] > 0, (sp_res["rec_pts"] / sp_res["rec_att"]).round(4), 0.0)
                        sp_res["dig_rating_0_3"] = np.where(sp_res["dig_att"] > 0, (sp_res["dig_pts"] / sp_res["dig_att"]).round(4), 0.0)
                        sp_res = sp_res.drop(columns=["xbp_pts", "rec_pts", "dig_pts", "fb_pts"])
                        st.dataframe(sp_res, use_container_width=True, hide_index=True, column_config=build_column_config(sp_res.columns))
                    else:
                        st.info("No touches logged matching that exact filter combination.")
                else:
                    st.warning("Select at least one option in each filter category.")
            else:
                st.info("Run the updated extraction script (`build_stats_by_player_id.py` + `compile_unified_database.py`) to enable granular situational splits.")

            # -------------------------------------------------
            # MATCH-BY-MATCH GAME LOGS + CLICKABLE PLAYER COMPS
            # -------------------------------------------------
            sub_col1, sub_col2 = st.columns([2.1, 1.1])
            with sub_col1:
                st.markdown("#### Match-by-Match Game Log")
                if "match_stats" in tables:
                    log_season = st.selectbox(
                        "Game Log Season",
                        options=sorted(p_seasons["season"].unique().tolist(), reverse=True),
                        key="gamelog_season_sel"
                    )
                    logs_df = pd.read_sql(
                        """
                        SELECT match_date, canonical_opponent AS opponent, home_away, is_conference,
                               result, sets_played, kills, errors, att, ke AS overall_ke, wke AS overall_wke,
                               serves, aces, serve_errors, xBP, rec_att, rec_rating AS reception_rating_0_3,
                               digs, dig_rating AS dig_rating_0_3, blocks
                        FROM match_stats
                        WHERE canonical_player_id = ? AND season = ?
                        ORDER BY match_date ASC
                        """,
                        conn,
                        params=(active_pid, log_season)
                    )
                    if not logs_df.empty:
                        st.dataframe(logs_df, use_container_width=True, hide_index=True, column_config=build_column_config(logs_df.columns))
                        download_csv_button(logs_df, f"{selected_player.replace(' ', '_')}_{log_season}_gamelog.csv", "dl_gamelog")
                    else:
                        st.info("No match logs found for this season.")
                else:
                    st.info("Match-by-match game logs will appear once `match_stats` is compiled.")

            with sub_col2:
                st.markdown("#### Top 5 Similar Players (Click to View)")
                comps_df = compute_player_comps(active_pid, pos_disp, int(latest["season"]))
                if not comps_df.empty:
                    for c_idx, crow in comps_df.iterrows():
                        comp_name = crow["player_name"]
                        comp_team = crow["team"]
                        comp_yr = int(crow["season"])
                        comp_sim = crow["Similarity"]
                        comp_wke = crow.get("overall_wke", 0.0)
                        st.button(
                            f"👤 {comp_name} ({comp_team} '{str(comp_yr)[-2:]}) — {comp_sim}% match | wKE {comp_wke:.3f}",
                            key=f"comp_btn_{active_pid}_{c_idx}_{comp_name}",
                            on_click=navigate_to_player,
                            args=(comp_name,),
                            use_container_width=True
                        )
                else:
                    st.info("Not enough positional volume to compute comps.")

        conn.close()

# =========================================================
# VIEW 2: POSITIONAL & PAA LEADERBOARDS
# =========================================================
elif active_view == "🏆 Positional & PAA Leaderboards":
    st.subheader("Positional & PAA Leaderboards")

    lb_c1, lb_c2, lb_c3, lb_c4, lb_c5 = st.columns(5)
    with lb_c1:
        lb_season = st.selectbox("Season", options=seasons_list, key="lb_season")
    with lb_c2:
        lb_league = st.selectbox("League", options=leagues_list, key="lb_league")
    with lb_c3:
        lb_pos = st.selectbox("Position", options=positions_list, key="lb_pos")
    with lb_c4:
        lb_mode = st.radio("Stat Type", options=["Rate Stats", "Counting & PAA Totals"], horizontal=True, key="lb_mode")
    with lb_c5:
        min_att = st.number_input("Min Attacks / Serves / Rec", value=75, step=25, key="lb_min_att")

    team_col = "canonical_team" if "canonical_team" in season_cols else "primary_team"
    if lb_mode == "Rate Stats":
        desired_cols = [
            "player_name", "league", f"{team_col} AS team", "position", "year_in_school", "sets_played",
            "overall_att", "overall_wke", "overall_ke", "wKE_plus",
            "ke_on_perf_pass", "ke_on_poor_pass", "fbso_wke", "trans_wke",
            "serves_total", "xBP", "xBP_plus", "ace_rate",
            "reception_rating_0_3", "dig_rating_0_3", "freeball_rating_0_3", "blocks_per_set"
        ]
        default_sort = "overall_wke"
    else:
        desired_cols = [
            "player_name", "league", f"{team_col} AS team", "position", "year_in_school", "sets_played",
            "overall_att", "overall_kills", "overall_errors", "serves_total", "aces",
            "reception_attempts", "dig_attempts", "freeball_attempts", "total_blocks",
            "APAA", "SetPAA", "PPAA", "ServePAA", "BPAA", "Total_PAA"
        ]
        default_sort = "Total_PAA" if "Total_PAA" in season_cols else "overall_kills"

    valid_select = []
    for c in desired_cols:
        raw_c = c.split(" AS ")[0]
        if raw_c in season_cols:
            valid_select.append(c)

    query = f"""
        SELECT {', '.join(valid_select)}
        FROM season_stats
        WHERE season = ?
          AND (overall_att >= ? OR serves_total >= ? OR reception_attempts >= ? OR dig_attempts >= ?)
    """
    params = [lb_season, min_att, min_att, min_att, min_att]

    if lb_league != "All" and "league" in season_cols:
        query += " AND league = ?"
        params.append(lb_league)
    if lb_pos != "All":
        query += " AND position = ?"
        params.append(lb_pos)

    query += f" ORDER BY {default_sort} DESC NULLS LAST"

    conn = get_connection()
    lb_df = pd.read_sql(query, conn, params=params)
    conn.close()

    st.caption(f"Showing **{len(lb_df):,}** qualified players (click any column header to re-sort).")
    st.dataframe(lb_df, use_container_width=True, hide_index=True, column_config=build_column_config(lb_df.columns))
    download_csv_button(lb_df, f"leaderboard_{lb_season}_{lb_pos}.csv", "dl_leaderboard")

# =========================================================
# VIEW 3: TEAM & CONFERENCE HUBS
# =========================================================
elif active_view == "🏟️ Team & Conference Hubs":
    st.subheader("Team & Conference Hubs")
    hub_c1, hub_c2, hub_c3 = st.columns(3)
    with hub_c1:
        hub_season = st.selectbox("Season", options=seasons_list, key="hub_season")
    with hub_c2:
        hub_conf = st.selectbox("Conference Filter", options=confs_list, key="hub_conf")
    with hub_c3:
        hub_team = st.selectbox("Select Team", options=teams_list, key="hub_team")

    conn = get_connection()
    team_col = "canonical_team" if "canonical_team" in season_cols else "primary_team"

    if hub_team:
        st.query_params["team"] = hub_team
        t_cols = [
            "player_name", "league", "player_number", "position", "year_in_school", "sets_played",
            "overall_att", "overall_kills", "overall_wke", "wKE_plus",
            "serves_total", "xBP", "reception_rating_0_3", "dig_rating_0_3", "blocks_per_set", "Total_PAA"
        ]
        valid_t_cols = [c for c in t_cols if c in season_cols]
        roster_df = pd.read_sql(
            f"SELECT {', '.join(valid_t_cols)} FROM season_stats WHERE season = ? AND {team_col} = ? ORDER BY sets_played DESC, overall_att DESC",
            conn,
            params=(hub_season, hub_team)
        )
        st.markdown(f"#### {hub_team} Roster & Individual Performance ({hub_season})")
        st.dataframe(roster_df, use_container_width=True, hide_index=True, column_config=build_column_config(roster_df.columns))
        download_csv_button(roster_df, f"{hub_team.replace(' ', '_')}_{hub_season}_roster.csv", "dl_team_roster")

    if hub_conf != "All" and "conference" in season_cols:
        st.markdown(f"#### {hub_conf} Team Standings & Efficiency Summary ({hub_season})")
        conf_df = pd.read_sql(
            f"""
            SELECT {team_col} AS team,
                   league,
                   COUNT(DISTINCT player_name) AS roster_size,
                   SUM(overall_att) AS total_att,
                   SUM(overall_kills) AS total_kills,
                   ROUND(AVG(overall_wke), 4) AS avg_player_wke,
                   ROUND(AVG(xBP), 4) AS avg_player_xbp,
                   ROUND(SUM(Total_PAA), 1) AS team_Total_PAA
            FROM season_stats
            WHERE season = ? AND conference = ?
            GROUP BY {team_col}, league
            ORDER BY team_Total_PAA DESC NULLS LAST, avg_player_wke DESC
            """,
            conn,
            params=(hub_season, hub_conf)
        )
        st.dataframe(conf_df, use_container_width=True, hide_index=True, column_config=build_column_config(conf_df.columns))

    conn.close()

# =========================================================
# VIEW 4: PROJECTIONS & PORTAL / FREE AGENCY SEARCH
# =========================================================
elif active_view == "🔮 Projections & Portal / FA Search":
    st.subheader("Unified Projection & Roster Status Hub (NCAA / MLV / LOVB)")
    st.markdown("Filter projected performance and active rosters across collegiate and professional leagues, including Transfer Portal and Free Agent pools.")

    p_c1, p_c2, p_c3, p_c4 = st.columns(4)
    with p_c1:
        pr_league = st.selectbox("League", options=leagues_list, key="pr_league")
    with p_c2:
        pr_pos = st.selectbox("Position", options=positions_list, key="pr_pos")
    with p_c3:
        pr_team = st.selectbox("Team", options=["All"] + teams_list, key="pr_team")
    with p_c4:
        pr_status = st.selectbox("Roster Status", options=["All", "Active", "Transfer Portal", "Free Agent", "Graduated"], key="pr_status")

    conn = get_connection()
    if "career_stats" in tables:
        c_cols = get_table_columns("career_stats")
        sel_c = [
            "player_name", "league", "latest_team AS team", "conference", "primary_position AS position",
            "latest_class AS class", "roster_status", "career_sets",
            "career_overall_wke", "career_xBP", "career_rec_rating_0_3", "career_dig_rating_0_3",
            "career_blocks_per_set", "career_Total_PAA"
        ]
        valid_sel_c = [c for c in sel_c if c.split(" AS ")[0] in c_cols]

        q_hub = f"SELECT {', '.join(valid_sel_c)} FROM career_stats WHERE 1=1"
        p_hub = []
        if pr_league != "All" and "league" in c_cols:
            q_hub += " AND league LIKE ?"
            p_hub.append(f"%{pr_league}%")
        if pr_pos != "All" and "primary_position" in c_cols:
            q_hub += " AND primary_position = ?"
            p_hub.append(pr_pos)
        if pr_team != "All" and "latest_team" in c_cols:
            q_hub += " AND latest_team = ?"
            p_hub.append(pr_team)
        if pr_status != "All" and "roster_status" in c_cols:
            q_hub += " AND roster_status = ?"
            p_hub.append(pr_status)

        q_hub += " ORDER BY career_Total_PAA DESC NULLS LAST, career_overall_wke DESC"
        hub_res = pd.read_sql(q_hub, conn, params=p_hub)

        if "projections" in tables:
            proj_all = pd.read_sql("SELECT * FROM projections", conn)
            if not proj_all.empty:
                st.markdown("#### Upcoming Season Projections (10th / 50th / 90th Percentiles)")
                st.dataframe(proj_all, use_container_width=True, hide_index=True)

        st.markdown(f"#### Player Directory ({len(hub_res):,} players)")
        st.dataframe(hub_res, use_container_width=True, hide_index=True, column_config=build_column_config(hub_res.columns))
        download_csv_button(hub_res, "volleyball_directory_export.csv", "dl_directory")

    conn.close()
