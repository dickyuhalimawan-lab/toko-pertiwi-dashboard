"""
=======================================================================
DASHBOARD TOKO PERTIWI v5 — dengan LOGIN, siap di-deploy ke web
=======================================================================
Perubahan dari v4:
- Ada halaman login (email + password) sebelum dashboard bisa dilihat
- Kredensial Supabase & login dibaca dari st.secrets (kalau di-deploy ke
  Streamlit Cloud) ATAU dari config_supabase.py (kalau dijalankan lokal)
  — jadi file yang SAMA bisa dipakai di dua tempat tanpa diubah.

CARA JALANKAN LOKAL (masih sama seperti sebelumnya):
    py -m streamlit run dashboard_v5.py

CARA DEPLOY KE WEB: ikuti instruksi yang diberikan terpisah.
=======================================================================
"""

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, date
from urllib.parse import quote

st.set_page_config(page_title="Toko Pertiwi — Sales & Promosi", layout="wide", page_icon="🧱")

# ----------------------------------------------------------------
# KONFIGURASI — coba st.secrets dulu (utk versi web/deploy),
# kalau tidak ada baru pakai config_supabase.py (utk lokal)
# ----------------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    LOGIN_EMAIL = st.secrets["LOGIN_EMAIL"]
    LOGIN_PASSWORD = st.secrets["LOGIN_PASSWORD"]
except Exception:
    from config_supabase import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
    LOGIN_EMAIL = "dickyuhalimawan@gmail.com"
    LOGIN_PASSWORD = "11111111"  # GANTI INI kalau sudah siap dipakai serius

# ======================================================================
# TEMA — palet terang, aksen "blueprint & safety tape"
# ======================================================================
BG = "#F4F6F8"
PANEL = "#FFFFFF"
BORDER = "#DDE2E8"
TEXT = "#1F242B"
TEXT_MUTED = "#5B6470"
BLUE = "#1D7FA8"
AMBER = "#C97D0E"
TEAL = "#237A61"
RUST = "#BD432B"
VIOLET = "#6355C7"
GREY = "#8A93A0"

CHART_COLORWAY = [BLUE, AMBER, TEAL, RUST, VIOLET, GREY]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"], p, div, span, label {{ font-family: 'IBM Plex Sans', sans-serif; }}
h1, h2, h3 {{ font-family: 'Space Grotesk', sans-serif; }}

[data-testid="stAppViewContainer"] {{ background: {BG}; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebar"] * {{ color: {TEXT_MUTED}; }}

[data-testid="stMetric"] {{
    background: {PANEL}; border: 1px solid {BORDER}; border-left: 3px solid {BLUE};
    padding: 14px 18px; border-radius: 6px;
}}
[data-testid="stMetricValue"] {{ font-family: 'Space Grotesk', sans-serif; color: {TEXT}; }}
[data-testid="stMetricLabel"] {{ color: {TEXT_MUTED}; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{ background: transparent; color: {TEXT_MUTED}; font-weight: 500; padding: 10px 18px; }}
.stTabs [aria-selected="true"] {{ color: {BLUE} !important; border-bottom: 2px solid {BLUE} !important; }}

[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 6px; }}

.tp-head {{ border-left: 3px solid var(--tp-accent, {BLUE}); padding: 4px 0 4px 14px; margin: 10px 0 4px 0; }}
.tp-head h3 {{ margin: 0; font-size: 1.08rem; color: {TEXT}; }}
.tp-head p {{ margin: 2px 0 0 0; color: {TEXT_MUTED}; font-size: 0.87rem; }}

.tp-explain {{ color: {TEXT_MUTED}; font-size: 0.88rem; line-height: 1.5; margin: 4px 0 12px 0; max-width: 780px; }}

.tp-hero {{ display: flex; gap: 36px; align-items: baseline; padding: 6px 0 18px 0; flex-wrap: wrap; }}
.tp-hero-num {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 2.6rem; color: {BLUE}; line-height: 1; }}
.tp-hero-lbl {{ color: {TEXT_MUTED}; font-size: 0.85rem; margin-top: 4px; }}
.tp-hero-sub {{ font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 1.5rem; color: {TEXT}; }}

.tp-insight {{
    background: #FFF8EC; border-left: 3px solid {AMBER};
    padding: 12px 16px; border-radius: 6px; margin: 8px 0 18px 0;
    color: {TEXT}; font-size: 0.92rem; line-height: 1.55;
}}
.tp-insight b {{ color: {AMBER}; }}
</style>
""", unsafe_allow_html=True)


# ======================================================================
# LOGIN GATE — halaman ini yang muncul PERTAMA sebelum dashboard
# ======================================================================
def login_screen():
    st.markdown(f"""
    <div style="max-width:380px; margin: 60px auto 0 auto; text-align:center;">
        <div style="font-family:'Space Grotesk',sans-serif; font-size:1.6rem; font-weight:700; color:{TEXT};">🧱 Toko Pertiwi</div>
        <div style="color:{TEXT_MUTED}; font-size:0.9rem; margin-top:4px;">Masuk untuk mengakses dashboard Sales & Promosi</div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
        if submitted:
            if email.strip().lower() == LOGIN_EMAIL.strip().lower() and password == LOGIN_PASSWORD:
                st.session_state["tp_logged_in"] = True
                st.rerun()
            else:
                st.error("Email atau password salah.")


if not st.session_state.get("tp_logged_in"):
    login_screen()
    st.stop()


# ----------------------------------------------------------------
# Helper format angka gaya Indonesia
# ----------------------------------------------------------------
def id_num(x, decimals=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "-"
    s = f"{x:,.{decimals}f}"
    integer_part, _, decimal_part = s.partition(".")
    integer_part = integer_part.replace(",", ".")
    return f"{integer_part},{decimal_part}" if decimals > 0 else integer_part


def id_rp(x, decimals=0):
    return f"Rp {id_num(x, decimals)}"


def id_rp_short(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "-"
    if abs(x) >= 1_000_000_000:
        return f"Rp {id_num(x/1_000_000_000, 1)} M"
    if abs(x) >= 1_000_000:
        return f"Rp {id_num(x/1_000_000, 1)} jt"
    if abs(x) >= 1_000:
        return f"Rp {id_num(x/1_000, 0)} rb"
    return id_rp(x)


def id_pct(x, decimals=1):
    return f"{id_num(x, decimals)}%"


def head(title: str, caption: str = "", accent: str = BLUE):
    cap_html = f"<p>{caption}</p>" if caption else ""
    st.markdown(f'<div class="tp-head" style="--tp-accent:{accent}"><h3>{title}</h3>{cap_html}</div>', unsafe_allow_html=True)


def explain(html: str):
    st.markdown(f'<div class="tp-explain">{html}</div>', unsafe_allow_html=True)


def insight(html: str):
    st.markdown(f'<div class="tp-insight">💡 {html}</div>', unsafe_allow_html=True)


def style_fig(fig, height=380):
    fig.update_layout(
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family="IBM Plex Sans, sans-serif", color=TEXT, size=13),
        colorway=CHART_COLORWAY, margin=dict(l=10, r=10, t=30, b=10), height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig


def styled_table(df, currency_cols=None, number_cols=None, pct_cols=None, color_col=None, invert_color=False):
    if df.empty:
        return df
    fmt = {}
    for c in (currency_cols or []):
        if c in df.columns:
            fmt[c] = lambda v: id_rp(v)
    for c in (number_cols or []):
        if c in df.columns:
            fmt[c] = lambda v: id_num(v)
    for c in (pct_cols or []):
        if c in df.columns:
            fmt[c] = lambda v: id_pct(v)
    styler = df.style.format(fmt)
    if color_col and color_col in df.columns:
        def _c(v):
            try:
                v = float(v)
            except (TypeError, ValueError):
                return ""
            positif_warna = RUST if invert_color else TEAL
            negatif_warna = TEAL if invert_color else RUST
            if v > 0:
                return f"color: {positif_warna}; font-weight: 600;"
            if v < 0:
                return f"color: {negatif_warna}; font-weight: 600;"
            return ""
        styler = styler.map(_c, subset=[color_col])
    return styler


@st.cache_data(ttl=300)
def sb(view: str, query: str = "") -> pd.DataFrame:
    url = f"{SUPABASE_URL}/rest/v1/{view}?{query}"
    resp = requests.get(url, headers={
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }, timeout=30)
    resp.raise_for_status()
    return pd.DataFrame(resp.json())


# ======================================================================
# HERO
# ======================================================================
daily = sb("v_tp_sales_daily", "order=tanggal.asc")
weekly = sb("v_tp_sales_weekly", "order=minggu_mulai.asc")
dow = sb("v_tp_sales_by_dow", "order=urutan_hari.asc")

col_title, col_refresh, col_logout = st.columns([4, 1, 1])
with col_title:
    st.markdown("## Toko Pertiwi")
    st.caption("Sales & Promosi — data langsung dari Supabase, ter-update otomatis tiap hari")
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
with col_logout:
    if st.button("🚪 Keluar"):
        st.session_state["tp_logged_in"] = False
        st.rerun()

if not daily.empty:
    total_omzet = daily["omzet"].astype(float).sum()
    total_faktur = int(daily["jumlah_faktur"].astype(int).sum())
    rentang = f"{daily['tanggal'].min()} — {daily['tanggal'].max()}"

    st.markdown(f"""
    <div class="tp-hero">
        <div><div class="tp-hero-num">{id_rp_short(total_omzet)}</div><div class="tp-hero-lbl">Total omzet tercatat</div></div>
        <div><div class="tp-hero-sub">{id_num(total_faktur)}</div><div class="tp-hero-lbl">Total faktur</div></div>
        <div><div class="tp-hero-sub">{id_rp_short(total_omzet/max(len(daily),1))}</div><div class="tp-hero-lbl">Rata-rata omzet/hari</div></div>
        <div><div class="tp-hero-sub" style="font-size:1.1rem;color:{TEXT_MUTED}">{rentang}</div><div class="tp-hero-lbl">Rentang data</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Badge kesehatan sinkronisasi data ----
    try:
        last_date = datetime.strptime(daily["tanggal"].max(), "%Y-%m-%d").date()
        days_stale = (date.today() - last_date).days
    except (TypeError, ValueError):
        days_stale = None

    if days_stale is not None:
        if days_stale <= 1:
            b_color, b_bg, b_text = TEAL, "#EAF6F1", f"✅ Data up to date — transaksi terakhir {last_date}"
        elif days_stale <= 3:
            b_color, b_bg, b_text = AMBER, "#FFF8EC", f"⚠️ Data telat {days_stale} hari — transaksi terakhir {last_date}, cek sinkronisasi"
        else:
            b_color, b_bg, b_text = RUST, "#FCEDEA", f"🔴 Sinkronisasi kemungkinan macet — data terakhir {days_stale} hari lalu ({last_date})"
        st.markdown(
            f'<div style="display:inline-block; background:{b_bg}; border:1px solid {b_color}; color:{b_color}; '
            f'padding:5px 14px; border-radius:20px; font-size:0.82rem; font-weight:600; margin-bottom:10px;">{b_text}</div>',
            unsafe_allow_html=True,
        )

st.markdown(f'<hr style="border-color:{BORDER}; margin:0 0 18px 0;">', unsafe_allow_html=True)

tab_ringkasan, tab_ranking, tab_promosi, tab_segmen, tab_kualitas = st.tabs([
    "Ringkasan & Tren", "Ranking Barang/Kategori", "Promosi & Bundling",
    "Segmentasi Transaksi", "Kualitas Data",
])

# ==================================================================
# TAB 1: RINGKASAN & TREN
# ==================================================================
with tab_ringkasan:
    head("Tren omzet harian", "Tiap titik = total penjualan 1 hari", BLUE)
    explain("Grafik ini menjawab pertanyaan paling dasar: <b>apakah toko sedang naik, turun, atau stabil?</b> "
            "Naik-turun harian itu wajar (efek akhir pekan, tanggal muda/tua) — yang perlu diwaspadai adalah kalau garis ini "
            "menurun terus selama beberapa hari berturut-turut, bukan cuma satu hari sepi.")
    if not daily.empty:
        fig = px.area(daily, x="tanggal", y="omzet")
        fig.update_traces(line_color=BLUE, fillcolor="rgba(29,127,168,0.12)")
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        head("Tren mingguan", "Rata-kan noise harian, lihat arah sebenarnya", AMBER)
        explain("Kalau tren harian terlalu naik-turun untuk disimpulkan, lihat versi mingguan ini — "
                "lebih jelas terlihat apakah minggu ini benar-benar lebih baik/buruk dari minggu lalu.")
        if not weekly.empty:
            fig2 = px.bar(weekly, x="minggu_mulai", y="omzet")
            fig2.update_traces(marker_color=AMBER)
            fig2.update_yaxes(tickformat=",.0f")
            st.plotly_chart(style_fig(fig2, 300), use_container_width=True)

    with col_b:
        head("Pola hari dalam seminggu", "Bentuk kelopak = performa hari itu", VIOLET)
        explain("Tiap 'kelopak' mewakili satu hari (Senin di atas, berputar searah jarum jam). "
                "Kelopak yang pendek = hari yang secara konsisten sepi — kandidat waktu terbaik untuk promosi, "
                "karena mendorong hari yang sudah ramai biasanya kurang efektif dibanding mengisi hari yang kosong.")
        if not dow.empty:
            fig3 = go.Figure(go.Barpolar(
                r=dow["total_omzet"].astype(float), theta=dow["hari"],
                marker_color=dow["total_omzet"].astype(float),
                marker_colorscale=[[0, "#EDEFF2"], [1, VIOLET]],
                marker_line_color=BORDER, marker_line_width=1,
            ))
            fig3.update_layout(polar=dict(bgcolor=PANEL,
                               radialaxis=dict(showticklabels=False, gridcolor=BORDER),
                               angularaxis=dict(gridcolor=BORDER, color=TEXT_MUTED)))
            st.plotly_chart(style_fig(fig3, 320), use_container_width=True)
            termurah = dow.loc[dow["total_omzet"].astype(float).idxmin(), "hari"]
            teramai = dow.loc[dow["total_omzet"].astype(float).idxmax(), "hari"]
            insight(f"<b>{teramai}</b> adalah hari paling ramai, <b>{termurah}</b> paling sepi. "
                    f"Kalau mau coba promosi flash-sale, jadwalkan di hari {termurah} — bukan di hari yang sudah ramai secara alami.")

# ==================================================================
# TAB 2: RANKING BARANG & KATEGORI
# ==================================================================
with tab_ranking:
    cat = sb("v_tp_sales_by_category", "order=omzet.desc")
    abc = sb("v_tp_abc_analysis", "order=rank_omzet.asc")
    eff = sb("v_tp_category_efficiency", "order=omzet_per_sku.asc")

    head("Peta kategori", "Ukuran kotak = besarnya omzet kategori itu", BLUE)
    explain("Bayangkan ini denah toko dilihat dari atas: kotak paling besar adalah kategori yang paling banyak "
            "menyumbang omzet. Kalau suatu saat kotak besar ini tiba-tiba mengecil dibanding kunjungan sebelumnya, "
            "itu sinyal untuk dicek — kehabisan stok? Ada kompetitor baru di kategori itu?")
    if not cat.empty:
        fig = px.treemap(cat.head(30), path=["kategori"], values="omzet",
                          color="omzet", color_continuous_scale=[[0, "#DCEAF1"], [1, BLUE]])
        fig.update_traces(textfont_size=13, marker_line_color=PANEL, marker_line_width=2,
                           texttemplate="%{label}<br>" + "Rp%{value:,.0f}")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_fig(fig, 420), use_container_width=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        head("Klasifikasi ABC (Pareto)", "Barang mana yang WAJIB selalu ada stoknya", TEAL)
        explain("Prinsip klasik toko retail: biasanya sebagian kecil barang menyumbang sebagian besar omzet. "
                "<b>Kelas A</b> adalah barang-barang itu — kalau salah satunya kehabisan stok, dampaknya langsung "
                "terasa di omzet harian. <b>Kelas C</b> sebaliknya: banyak jenis barang, tapi kontribusinya kecil-kecil — "
                "kandidat untuk dikurangi variannya atau dihabiskan lewat diskon.")
        if not abc.empty:
            summary = abc.groupby("kelas_abc").agg(jumlah_sku=("kode_barang", "count"), total_omzet=("omzet", "sum")).reset_index()
            fig = go.Figure(go.Pie(labels=summary["kelas_abc"], values=summary["total_omzet"], hole=0.62,
                                    marker=dict(colors=[TEAL, AMBER, GREY])))
            total_all = summary["total_omzet"].sum()
            fig.add_annotation(text=id_rp_short(total_all), x=0.5, y=0.52, showarrow=False,
                                font=dict(size=20, color=TEXT, family="Space Grotesk"))
            fig.add_annotation(text="total omzet", x=0.5, y=0.42, showarrow=False, font=dict(size=11, color=TEXT_MUTED))
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
            st.dataframe(styled_table(summary, currency_cols=["total_omzet"], number_cols=["jumlah_sku"]),
                         use_container_width=True, hide_index=True)

    with col_b:
        head("Efisiensi kategori", "Omzet per SKU — kategori 'gemuk' vs efisien", RUST)
        explain("Ini membandingkan omzet yang dihasilkan per varian barang. Kategori dengan garis merah punya "
                "banyak varian tapi masing-masing kontribusinya kecil — itu berarti modal & rak toko terpakai untuk "
                "sesuatu yang perputarannya lambat. Kategori efisien sebaliknya: sedikit varian, tapi masing-masing laris.")
        if not eff.empty:
            eff_show = eff[eff["status_efisiensi"] != "Normal"].head(12)
            fig = px.bar(eff_show.sort_values("omzet_per_sku"), x="omzet_per_sku", y="kategori", orientation="h",
                         color="status_efisiensi",
                         color_discrete_map={"Kurang Efisien (byk SKU, omzet/SKU rendah)": RUST, "Sangat Efisien": TEAL})
            fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title="Omzet per SKU (Rp)")
            fig.update_xaxes(tickformat=",.0f")
            st.plotly_chart(style_fig(fig, 380), use_container_width=True)

    with st.expander("📋 Lihat detail ABC per barang (semua SKU)"):
        if not abc.empty:
            st.dataframe(styled_table(abc, currency_cols=["omzet"], number_cols=["rank_omzet", "total_sku"],
                                       pct_cols=["persen_kumulatif", "persen_sku_kumulatif"]),
                         use_container_width=True, hide_index=True)

    head("Ranking lengkap kategori", "", GREY)
    if not cat.empty:
        st.dataframe(styled_table(cat, currency_cols=["omzet", "rata2_omzet_per_hari"], number_cols=["jumlah_sku_aktif", "total_qty"]),
                     use_container_width=True, hide_index=True)

# ==================================================================
# TAB 3: PROMOSI & BUNDLING
# ==================================================================
with tab_promosi:
    basket_pairs = sb("v_tp_basket_pairs", "order=jumlah_faktur_bersama.desc&limit=15")
    cat_cooc = sb("v_tp_category_cooccurrence", "order=jumlah_faktur_bersama.desc&limit=12")
    basket_size = sb("v_tp_basket_size")
    momentum = sb("v_tp_category_momentum", "order=perubahan_persen.asc")
    new_items = sb("v_tp_new_item_performance", "order=jumlah_transaksi.desc")

    head("Ukuran belanja per struk", "Peluang cross-sell paling langsung", AMBER)
    explain("Tiap struk dikelompokkan berdasarkan berapa jenis barang yang dibeli sekaligus. "
            "Bandingkan grafik kiri (jumlah struk) dengan grafik kanan (nilai rata-rata) — kalau mayoritas struk "
            "ada di kelompok '1 barang' tapi nilainya jauh lebih kecil dari kelompok '2-3 barang', itu artinya "
            "cuma dengan menawarkan SATU barang tambahan ke pembeli, nilai transaksi bisa naik signifikan.")
    if not basket_size.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(basket_size, x="kelompok_ukuran", y="jumlah_faktur", text="persen_faktur")
            fig.update_traces(marker_color=AMBER, texttemplate="%{text}%", textposition="outside")
            fig.update_layout(yaxis_title="Jumlah faktur", xaxis_title=None)
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
        with c2:
            fig2 = px.bar(basket_size, x="kelompok_ukuran", y="rata2_nilai_faktur")
            fig2.update_traces(marker_color=TEAL)
            fig2.update_layout(yaxis_title="Rata-rata Rp/faktur", xaxis_title=None)
            fig2.update_yaxes(tickformat=",.0f")
            st.plotly_chart(style_fig(fig2, 300), use_container_width=True)
        satu = basket_size[basket_size["kelompok_ukuran"] == "1 barang"]
        dua_tiga = basket_size[basket_size["kelompok_ukuran"] == "2-3 barang"]
        if not satu.empty and not dua_tiga.empty:
            insight(f"<b>{id_pct(satu.iloc[0]['persen_faktur'])} struk cuma beli 1 barang</b> (rata-rata {id_rp(satu.iloc[0]['rata2_nilai_faktur'])}), "
                    f"padahal struk 2-3 barang rata-rata sudah {id_rp(dua_tiga.iloc[0]['rata2_nilai_faktur'])} — "
                    "hampir tiga kali lipat. Latih kasir menawarkan satu barang pelengkap yang relevan (lihat tabel di bawah) sebelum transaksi selesai.")

    col_a, col_b = st.columns(2)
    with col_a:
        head("Barang sering dibeli bersamaan", "Dasar ide bundling per-barang", BLUE)
        explain("Kalau dua kode barang sering muncul di faktur yang sama, itu artinya pelanggan memang butuh keduanya "
                "sekaligus (misal fitting pipa + lem-nya). Pajang berdekatan di rak, atau tawarkan sebagai paket.")
        if not basket_pairs.empty:
            fig = px.bar(basket_pairs.sort_values("jumlah_faktur_bersama"), x="jumlah_faktur_bersama", y="kode_a",
                         orientation="h", hover_data=["kode_b"])
            fig.update_traces(marker_color=BLUE)
            fig.update_layout(yaxis_title=None, xaxis_title="Jumlah faktur bersama")
            st.plotly_chart(style_fig(fig, 380), use_container_width=True)
    with col_b:
        head("Kategori sering dibeli bersamaan", "Dasar ide paket lintas kategori", VIOLET)
        explain("Versi lebih luas dari tabel kiri — kalau dua KATEGORI (bukan cuma dua barang spesifik) sering "
                "muncul bersamaan, itu bisa jadi dasar paket promosi yang lebih besar, misal 'paket mulai renovasi'.")
        if not cat_cooc.empty:
            st.dataframe(styled_table(cat_cooc, number_cols=["jumlah_faktur_bersama"]),
                         use_container_width=True, hide_index=True, height=380)

    head("Kategori besar tapi melambat", "Prioritas promosi #1 — bukan yang memang tak laku", RUST)
    explain("Ini beda dari 'barang tidak laku' biasa. Ini kategori yang TERBUKTI besar (total omzet tinggi) tapi "
            "arahnya sedang menurun dibanding awal periode. Kategori seperti ini paling layak diselidiki dan "
            "didorong lewat promosi — karena pasarnya sudah terbukti ada, cuma sedang melemah.")
    if not momentum.empty:
        sig = momentum[momentum["total_omzet"].astype(float) > 2_000_000].copy()
        if not sig.empty:
            st.dataframe(styled_table(sig, currency_cols=["omzet_paruh_awal", "omzet_paruh_akhir", "total_omzet"],
                                       pct_cols=["perubahan_persen"], color_col="perubahan_persen"),
                         use_container_width=True, hide_index=True)
        st.caption("Berbasis perbandingan paruh-awal vs paruh-akhir periode data yang ada — akan lebih akurat setelah beberapa minggu.")

    head("Performa barang baru", "Pertama terjual dalam 7 hari terakhir data", TEAL)
    explain("Barang yang baru muncul di data dan sudah punya beberapa transaksi berarti langsung diterima pasar — "
            "pertimbangkan tambah stoknya. Yang cuma terjual sekali dan tidak berulang, masih terlalu dini disimpulkan.")
    if not new_items.empty:
        st.dataframe(styled_table(new_items, currency_cols=["omzet"], number_cols=["jumlah_transaksi", "total_qty", "umur_hari_dlm_data"]),
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada barang baru terdeteksi di jendela data saat ini.")

# ==================================================================
# TAB 4: SEGMENTASI TRANSAKSI
# ==================================================================
with tab_segmen:
    segs = sb("v_tp_transaction_segments")
    named = sb("v_tp_named_customer_summary", "order=total_belanja.desc")

    head("Segmentasi nilai transaksi", "Top 10% faktur vs sisanya", AMBER)
    explain("Semua faktur dikelompokkan jadi 3 berdasarkan besar-kecilnya nilai: 'Borongan/Proyek' (10% faktur "
            "dengan nilai terbesar), 'Menengah', dan 'Retail Kecil'. Ini menjawab pertanyaan penting: apakah omzet "
            "toko ditopang oleh banyak pembeli kecil, atau segelintir pembeli besar?")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if not segs.empty:
            fig = go.Figure(go.Pie(labels=segs["segmen"], values=segs["total_omzet"], hole=0.55,
                                    marker=dict(colors=[AMBER, BLUE, GREY])))
            st.plotly_chart(style_fig(fig, 340), use_container_width=True)
    with col_b:
        if not segs.empty:
            st.dataframe(styled_table(segs, currency_cols=["rata2_nilai_faktur", "total_omzet"],
                                       number_cols=["jumlah_faktur"], pct_cols=["persen_dari_omzet"]),
                         use_container_width=True, hide_index=True)
    top10 = segs[segs["segmen"].str.contains("Borongan", na=False)] if not segs.empty else pd.DataFrame()
    if not top10.empty:
        insight(f"<b>{id_pct(top10.iloc[0]['persen_dari_omzet'])} omzet</b> berasal dari cuma {id_num(top10.iloc[0]['jumlah_faktur'])} faktur "
                "'Borongan/Proyek'. Ini artinya kesehatan omzet toko lebih ditentukan oleh menjaga hubungan baik dengan "
                "segelintir pembeli besar ini, dibanding mengejar volume pembeli retail harian.")

    head("Pelanggan bernama", "Di luar Tunai POS / Pelanggan Umum", TEAL)
    explain("Mayoritas transaksi toko tidak tercatat atas nama siapa pun (pembeli tunai/walk-in). Daftar di bawah "
            "adalah pengecualian — pelanggan yang identitasnya tercatat di Accurate, biasanya karena mereka pembeli "
            "rutin atau punya hubungan bisnis (B2B). Layak dipertimbangkan untuk program relasi/kredit khusus.")
    if not named.empty:
        st.dataframe(styled_table(named, currency_cols=["total_belanja", "rata2_per_faktur"], number_cols=["jumlah_faktur"]),
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada pelanggan bernama di data saat ini.")

# ==================================================================
# TAB 5: KUALITAS DATA
# ==================================================================
with tab_kualitas:
    st.markdown(
        f'<div class="tp-insight" style="border-left-color:{GREY}">🔍 Tab ini memantau kesehatan data, bukan performa bisnis — '
        "baris di sini kemungkinan besar salah input, dicek dulu sebelum dijadikan dasar keputusan.</div>",
        unsafe_allow_html=True,
    )

    price_var = sb("v_tp_item_price_variance", "order=rentang_persen.desc&limit=25")
    recency = sb("v_tp_item_recency", "order=hari_sejak_terakhir_terjual.desc&limit=20")
    unit_errors = sb("v_tp_potential_unit_errors", "order=potensi_selisih_rp.desc&limit=100")

    head("⚠️ Potensi salah satuan yang berdampak ke uang", "Transaksi yang harganya menyimpang jauh dari pola biasa", RUST)
    explain(
        "Tiap transaksi dibandingkan dengan harga yang <b>paling sering dipakai</b> untuk kombinasi barang+satuan yang sama. "
        "Kalau menyimpang jauh, ditampilkan di sini beserta perkiraan selisih uangnya. "
        "<b>PENTING — ini bisa berarti dua hal berbeda, harus dicek manual ke penginputnya:</b><br>"
        "① <b>Uang benar-benar kurang/lebih diterima</b> — kasir memang mengenakan harga yang salah ke pembeli.<br>"
        "② <b>Uang sudah benar, cuma label satuan yang salah dipilih di sistem</b> — misalnya bermaksud jual 15 SAK dengan harga SAK yang benar, "
        "tapi di sistem ke-pilih satuan 'KG'. Uang yang diterima kemungkinan tetap benar, tapi <b>stok jadi salah tercatat</b> "
        "(sistem mengurangi 15 KG dari stok, padahal fisik yang keluar 15 SAK = 750 KG) — ini tetap perlu dibenahi meski bukan soal uang."
    )
    if not unit_errors.empty:
        st.dataframe(
            styled_table(
                unit_errors[["no_faktur", "tanggal", "penginput", "kode_barang", "nama_barang", "unit",
                             "harga_modus", "harga_transaksi_ini", "qty", "uang_tercatat",
                             "uang_seharusnya_jika_ikut_modus", "potensi_selisih_rp"]],
                currency_cols=["harga_modus", "harga_transaksi_ini", "uang_tercatat",
                               "uang_seharusnya_jika_ikut_modus", "potensi_selisih_rp"],
                number_cols=["qty"], color_col="potensi_selisih_rp", invert_color=True,
            ),
            use_container_width=True, hide_index=True,
        )
        total_selisih = unit_errors["potensi_selisih_rp"].astype(float).sum()
        n_kurang = (unit_errors["potensi_selisih_rp"].astype(float) > 0).sum()
        n_lebih = (unit_errors["potensi_selisih_rp"].astype(float) < 0).sum()
        insight(f"Dari {len(unit_errors)} transaksi mencurigakan: <b>{n_kurang} berpotensi uang kurang tercatat</b>, "
                f"<b>{n_lebih} berpotensi lebih</b> (bersih {id_rp(total_selisih)}). "
                "Cek dulu langsung ke faktur aslinya di Accurate dan tanya penginputnya sebelum menyimpulkan ini kerugian nyata — "
                "kemungkinan besar sebagian besar cuma salah label satuan, bukan salah kasih harga ke pembeli.")
    else:
        st.caption("Belum ada transaksi yang menyimpang cukup jauh untuk ditandai.")

    head("Variasi harga jual (SKU + satuan yang sama)", "", GREY)
    explain("Barang dengan rentang harga sangat lebar (>90%) di satuan yang SAMA biasanya bukan diskon nyata — "
            "sering kali kasir salah pilih satuan (misal pilih 'per KG' padahal maksudnya 'per SAK'). "
            "Tapi hati-hati: kalau harga yang sama dipakai KONSISTEN oleh banyak kasir di banyak tanggal, itu justru "
            "kebijakan harga yang disengaja (mis. jual eceran per-KG memang lebih mahal per-satuan berat dibanding beli per-SAK utuh) — "
            "bukan kesalahan. Yang perlu dicek adalah baris yang MENYIMPANG dari pola mayoritasnya.")
    if not price_var.empty:
        st.dataframe(styled_table(price_var, currency_cols=["harga_terendah", "harga_tertinggi", "harga_rata2"],
                                   number_cols=["jumlah_baris_transaksi", "jumlah_harga_berbeda"], pct_cols=["rentang_persen"]),
                     use_container_width=True, hide_index=True)

        st.markdown("**🔍 Telusuri per barang — lihat faktur, tanggal, dan penginputnya**")
        price_var_disp = price_var.copy()
        price_var_disp["_label"] = price_var_disp["kode_barang"] + " — " + price_var_disp["nama_barang"].fillna("") + " (" + price_var_disp["unit"] + ")"
        label_to_pair = dict(zip(price_var_disp["_label"], zip(price_var_disp["kode_barang"], price_var_disp["unit"])))
        pilihan = st.selectbox("Pilih barang untuk ditelusuri:", price_var_disp["_label"].tolist(), key="pilih_price_var")
        if pilihan:
            kode_pilih, unit_pilih = label_to_pair[pilihan]
            detail = sb("v_tp_item_price_variance_detail",
                        f"kode_barang=eq.{quote(str(kode_pilih))}&unit=eq.{quote(str(unit_pilih))}&order=unit_price.asc")
            if not detail.empty:
                st.dataframe(
                    styled_table(detail[["no_faktur", "tanggal", "penginput", "qty", "unit_price", "total_price"]],
                                 currency_cols=["unit_price", "total_price"], number_cols=["qty"]),
                    use_container_width=True, hide_index=True,
                )
                explain("Baris paling atas/bawah (harga paling beda dari mayoritas) adalah kandidat pertama untuk dicek ke penginputnya — "
                        "tanyakan apakah waktu itu memang bermaksud jual di satuan tersebut atau salah pilih di kasir.")

    head("Barang paling lama tidak terjual", "", GREY)
    explain("PERINGATAN: data baru mencakup periode pendek (mulai 31 Agustus 2026). 'Lama tidak terjual' di sini "
            "bisa berarti barang itu cuma terjual sekali di awal periode data — BUKAN berarti barang itu benar-benar "
            "mati total. Indikator ini akan jauh lebih bisa dipercaya begitu data terkumpul beberapa bulan.")
    if not recency.empty:
        st.dataframe(styled_table(recency, number_cols=["total_qty_alltime", "hari_sejak_terakhir_terjual"]),
                     use_container_width=True, hide_index=True)

# ======================================================================
# SIDEBAR
# ======================================================================
st.sidebar.markdown("### 🧱 Toko Pertiwi")
st.sidebar.caption("Sumber: Supabase, auto-sync harian. Cache 5 menit.")
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Catatan kualitas data**
- `harga_jual` master TIDAK reliable — semua analisa pakai harga transaksi riil
- HPP baru ada di sebagian kecil SKU — margin belum representatif
- Field satuan (`unit`) kadang salah input kasir
- Rentang data masih pendek — tren akan makin tajam seiring waktu
""")
