"""
Pulse AI — Streamlit Dashboard
Run: streamlit run dashboard.py
Reads onboarding data passed via URL query params:
  ?age=28&gender=male&weight_kg=78.5&height_cm=178&activity_level=intermediate
Or falls back to sidebar manual entry.
"""

import streamlit as st
import plotly.graph_objects as go
import requests # ⚡ NEW: Needed to talk to the FastAPI backend
from health_engine import HealthEngine, UserInput

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pulse AI · Health Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS injected into Streamlit ────────────────────────────────────────
st.markdown("""
<style>
/* ── Import font ── */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── App shell ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #070B14 !important;
    color: #E8EDF7 !important;
}
.main .block-container { padding-top: 2rem; max-width: 1200px; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Glassmorphism metric card ── */
div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 16px !important;
    padding: 20px 24px !important;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(16px);
    transition: border-color .2s, box-shadow .2s;
}
div[data-testid="metric-container"]:hover {
    border-color: rgba(0,240,255,0.3) !important;
    box-shadow: 0 0 24px rgba(0,240,255,0.08);
}
div[data-testid="metric-container"]::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,240,255,0.5), transparent);
}
div[data-testid="metric-container"] label {
    color: rgba(232,237,247,0.5) !important;
    font-size: 11px !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}
div[data-testid="metric-container"] [data-testid="metric-value"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    color: #00F0FF !important;
}
div[data-testid="metric-container"] [data-testid="metric-delta"] {
    font-size: 12px !important;
}

/* ── Glass panel (general purpose) ── */
.glass-panel {
    background: rgba(10,15,30,0.72);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 28px 32px;
    backdrop-filter: blur(20px);
    position: relative;
    overflow: hidden;
    margin-bottom: 20px;
}
.glass-panel::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,240,255,0.4), rgba(255,45,120,0.4), transparent);
}

/* ── Section labels ── */
.sec-label {
    font-size: 11px; font-weight: 500; letter-spacing: 2.5px;
    text-transform: uppercase; color: #FF2D78;
    margin-bottom: 4px;
}
.sec-title {
    font-family: 'Syne', sans-serif;
    font-size: 22px; font-weight: 800; margin-bottom: 16px;
}

/* ── AI summary box ── */
.ai-box {
    background: rgba(0,240,255,0.05);
    border: 1px solid rgba(0,240,255,0.18);
    border-radius: 14px;
    padding: 20px 24px;
    line-height: 1.75;
    font-size: 15px;
}
.ai-box strong { color: #00F0FF; }

/* ── Insight row ── */
.insight-row {
    display: grid; grid-template-columns: repeat(3,1fr); gap: 14px;
    margin-top: 20px;
}
.insight-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 16px 18px;
    text-align: center;
}
.insight-card .val {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem; font-weight: 800;
    color: #a78bfa; margin-bottom: 4px;
}
.insight-card .lbl {
    font-size: 11px; color: rgba(232,237,247,0.45);
    letter-spacing: 1.5px; text-transform: uppercase;
}

/* ── Logo header ── */
.logo-bar {
    display: flex; align-items: center; gap: 12px; margin-bottom: 32px;
}
.logo-wordmark {
    font-family: 'Syne', sans-serif; font-size: 26px; font-weight: 800;
    background: linear-gradient(90deg, #00F0FF, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.logo-tag {
    font-size: 11px; color: rgba(232,237,247,0.4);
    letter-spacing: 2px; text-transform: uppercase;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(7,11,20,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] label { color: rgba(232,237,247,0.6) !important; font-size: 12px !important; }
[data-testid="stSidebar"] .stSelectbox div, [data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.1) !important;
    color: #E8EDF7 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helper: read URL query params (passed from index.html) ────────────────────
def read_query_params() -> dict:
    qp = st.query_params
    result = {}
    try:
        if "age"            in qp: result["age"]            = int(qp["age"])
        if "gender"         in qp: result["gender"]         = qp["gender"]
        if "weight_kg"      in qp: result["weight_kg"]      = float(qp["weight_kg"])
        if "height_cm"      in qp: result["height_cm"]      = float(qp["height_cm"])
        if "activity_level" in qp: result["activity_level"] = qp["activity_level"]
    except (ValueError, TypeError):
        pass
    return result


# ── Sidebar input form (fallback / manual override) ───────────────────────────
def sidebar_inputs(prefill: dict) -> dict:
    with st.sidebar:
        st.markdown("""
        <div style='padding:16px 0 8px'>
            <div style='font-family:Syne,sans-serif;font-size:20px;font-weight:800;
                        background:linear-gradient(90deg,#00F0FF,#a78bfa);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
                ⚡ Pulse AI
            </div>
            <div style='font-size:10px;letter-spacing:2px;
                        color:rgba(232,237,247,0.4);text-transform:uppercase;margin-top:2px'>
                Health Metrics Engine
            </div>
        </div>
        <hr style='border-color:rgba(255,255,255,0.07);margin:12px 0 20px'>
        """, unsafe_allow_html=True)

        st.markdown("##### 👤 Profile")
        age    = st.number_input("Age",       min_value=1,   max_value=120, value=prefill.get("age", 28))
        gender = st.selectbox("Gender",       ["male", "female", "other"],
                              index=["male","female","other"].index(prefill.get("gender","male")))

        st.markdown("##### 📐 Biometrics")
        weight = st.number_input("Weight (kg)", min_value=1.0,  max_value=400.0,
                                 value=prefill.get("weight_kg", 75.0), step=0.5)
        height = st.number_input("Height (cm)", min_value=50.0, max_value=280.0,
                                 value=prefill.get("height_cm", 175.0), step=0.5)

        st.markdown("##### 🏋️ Experience Level")
        level  = st.selectbox("Activity Level", ["beginner", "intermediate", "advanced"],
                              index=["beginner","intermediate","advanced"].index(
                                  prefill.get("activity_level","intermediate")))

        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("⚡ Calculate Metrics", use_container_width=True)

    return {"age": age, "gender": gender, "weight_kg": weight,
            "height_cm": height, "activity_level": level, "run": run}


# ── BMI Gauge chart (Plotly) ──────────────────────────────────────────────────
def bmi_gauge(bmi_val: float, bmi_cat: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=bmi_val,
        delta={"reference": 22.0, "increasing": {"color": "#FF2D78"},
               "decreasing": {"color": "#00F0FF"}},
        number={"font": {"size": 52, "color": "#E8EDF7",
                         "family": "Syne, sans-serif"}, "suffix": ""},
        title={"text": f"<b>BMI Score</b><br><span style='font-size:14px;"
                       f"color:#a78bfa'>{bmi_cat}</span>",
               "font": {"size": 18, "color": "#E8EDF7"}},
        gauge={
            "axis": {
                "range": [10, 45],
                "tickwidth": 1,
                "tickcolor": "rgba(232,237,247,0.3)",
                "tickfont": {"color": "rgba(232,237,247,0.5)", "size": 11},
            },
            "bar": {"color": "rgba(255,255,255,0.9)", "thickness": 0.06},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [10,   18.5], "color": "rgba(59,130,246,0.25)"},   # underweight blue
                {"range": [18.5, 25.0], "color": "rgba(16,185,129,0.30)"},   # normal green
                {"range": [25.0, 30.0], "color": "rgba(245,158,11,0.30)"},   # overweight yellow
                {"range": [30.0, 35.0], "color": "rgba(239,68,68,0.25)"},    # obese I red
                {"range": [35.0, 40.0], "color": "rgba(239,68,68,0.40)"},    # obese II
                {"range": [40.0, 45.0], "color": "rgba(239,68,68,0.55)"},    # obese III
            ],
            "threshold": {
                "line": {"color": "#00F0FF", "width": 3},
                "thickness": 0.8,
                "value": bmi_val,
            },
        },
    ))

    for x, y, label, color in [
        (0.13, 0.12, "Underweight", "#3B82F6"),
        (0.36, 0.05, "Normal",      "#10B981"),
        (0.62, 0.05, "Overweight",  "#F59E0B"),
        (0.85, 0.12, "Obese",       "#EF4444"),
    ]:
        fig.add_annotation(x=x, y=y, text=label, showarrow=False,
                           font={"size": 10, "color": color}, xref="paper", yref="paper")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 60, "b": 10, "l": 10, "r": 10},
        height=280,
        font={"family": "DM Sans, sans-serif"},
    )
    return fig


# ── Calorie bar chart ─────────────────────────────────────────────────────────
def calorie_chart(maintain: float, lose: float, gain: float) -> go.Figure:
    labels  = ["Lose 0.5 kg/wk", "Maintain", "Gain 0.5 kg/wk"]
    values  = [lose, maintain, gain]
    colors  = ["rgba(0,240,255,0.7)", "rgba(167,139,250,0.7)", "rgba(255,45,120,0.7)"]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker={"color": colors,
                "line": {"color": "rgba(255,255,255,0.1)", "width": 1}},
        text=[f"{int(v)} kcal" for v in values],
        textposition="outside",
        textfont={"color": "#E8EDF7", "size": 13, "family": "Syne, sans-serif"},
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 30, "b": 10, "l": 10, "r": 10},
        height=260,
        yaxis={
            "showgrid": True,
            "gridcolor": "rgba(255,255,255,0.05)",
            "tickfont": {"color": "rgba(232,237,247,0.4)", "size": 11},
            "zeroline": False,
        },
        xaxis={"tickfont": {"color": "rgba(232,237,247,0.6)", "size": 12}},
        showlegend=False,
        bargap=0.35,
    )
    return fig


# ── Main dashboard ────────────────────────────────────────────────────────────
def main():
    prefill = read_query_params()
    inp     = sidebar_inputs(prefill)

    should_run = inp["run"] or bool(prefill)

    # ── Logo ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class='logo-bar'>
        <div>
            <div class='logo-wordmark'>⚡ Pulse AI</div>
            <div class='logo-tag'>Health Metrics Dashboard</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not should_run:
        st.markdown("""
        <div class='glass-panel' style='text-align:center;padding:60px 32px'>
            <div style='font-size:48px;margin-bottom:16px'>🧬</div>
            <div style='font-family:Syne,sans-serif;font-size:22px;font-weight:800;margin-bottom:10px'>
                Ready to Calibrate
            </div>
            <div style='color:rgba(232,237,247,0.5);font-size:15px'>
                Fill in your details in the sidebar and hit <strong style='color:#00F0FF'>Calculate Metrics</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Calculate ─────────────────────────────────────────────────────────────
    try:
        user    = UserInput(
            age=inp["age"], gender=inp["gender"],
            weight_kg=inp["weight_kg"], height_cm=inp["height_cm"],
            activity_level=inp["activity_level"],
        )
        metrics = HealthEngine.calculate(user)
    except ValueError as e:
        st.error(f"⚠️ Validation error: {e}")
        return

    # ── TOP METRIC CARDS ──────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        delta_w = round(metrics.weight_kg - metrics.ideal_weight_max_kg, 1)
        st.metric("⚖️  Current Weight",
                  f"{metrics.weight_kg} kg",
                  delta=f"{delta_w:+.1f} kg vs ideal max",
                  delta_color="inverse")
    with c2:
        st.metric("🔥  Daily Calories (TDEE)",
                  f"{int(metrics.tdee)} kcal",
                  delta=f"BMR: {int(metrics.bmr)} kcal")
    with c3:
        st.metric("💧  Body Fat %",
                  f"{metrics.body_fat_pct}%",
                  delta=metrics.bmi_category)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── GAUGE + CALORIE CHART ─────────────────────────────────────────────────
    left, right = st.columns([1, 1])

    with left:
        st.markdown("""
        <div class='glass-panel'>
            <div class='sec-label'>Biometric Score</div>
            <div class='sec-title'>BMI Gauge</div>
        """, unsafe_allow_html=True)
        st.plotly_chart(bmi_gauge(metrics.bmi, metrics.bmi_category),
                        use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div class='glass-panel'>
            <div class='sec-label'>Energy Targets</div>
            <div class='sec-title'>Calorie Scenarios</div>
        """, unsafe_allow_html=True)
        st.plotly_chart(
            calorie_chart(metrics.calories_maintain,
                          metrics.calories_lose_half_kg,
                          metrics.calories_gain_half_kg),
            use_container_width=True, config={"displayModeBar": False},
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── INSIGHT CARDS ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class='glass-panel'>
        <div class='sec-label'>Key Numbers</div>
        <div class='sec-title'>At a Glance</div>
        <div class='insight-row'>
            <div class='insight-card'>
                <div class='val'>{metrics.bmr:.0f}</div>
                <div class='lbl'>Basal Metabolic Rate (kcal)</div>
            </div>
            <div class='insight-card'>
                <div class='val'>{metrics.ideal_weight_min_kg}–{metrics.ideal_weight_max_kg}</div>
                <div class='lbl'>Ideal Weight Range (kg)</div>
            </div>
            <div class='insight-card'>
                <div class='val'>{metrics.bmi}</div>
                <div class='lbl'>BMI Score</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── AI AGENT SUMMARY ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div class='glass-panel'>
        <div class='sec-label'>🤖 Automated Insight</div>
        <div class='sec-title'>Static Summary</div>
        <div class='ai-box'>
            {metrics.ai_summary.replace(chr(10), '<br>')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ⚡ NEW: INTERACTIVE PULSE AI CHAT ⚡ ──────────────────────────────────
    st.markdown("""
    <div class='glass-panel'>
        <div class='sec-label'>💬 Interactive AI</div>
        <div class='sec-title'>Chat with Pulse AI</div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Secretly construct the exact stats of the user to feed to the AI
    context_string = f"""
    User Profile: Age {user.age}, Gender {user.gender}
    Weight: {user.weight_kg}kg, Height: {user.height_cm}cm, Activity Level: {user.activity_level}
    Current BMI: {metrics.bmi} ({metrics.bmi_category})
    TDEE (Maintenance Calories): {metrics.tdee} kcal
    Body Fat: {metrics.body_fat_pct}%
    """

    # 2. Initialize chat memory
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Opening greeting from AI
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"Hi! I see your TDEE is **{int(metrics.tdee)} kcal** and your BMI is **{metrics.bmi}**. I'm Pulse AI, your personal trainer. Want me to build you a custom workout or meal plan based on your metrics?"
        })

    # 3. Render previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 4. Handle user input
    if prompt := st.chat_input("Ask Pulse AI for a workout or meal plan..."):
        # Display user text
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Call FastAPI backend
        with st.spinner("Pulse AI is thinking... ⚡"):
            try:
                # 🚨 CHANGE THIS URL to your Colab ngrok/localtunnel URL if running the model on Colab!
                # Example: api_url = "https://brave-frogs-sing.loca.lt/chat"
                api_url = "https://angry-goats-fail.loca.lt/chat " 
                
                payload = {
                    "user_message": prompt,
                    "user_context": context_string # We silently pass the health stats here!
                }
                
                response = requests.post(api_url, json=payload)
                
                if response.status_code == 200:
                    ai_reply = response.json().get("ai_response", "Error reading response.")
                else:
                    ai_reply = f"API Error: {response.status_code} - {response.text}"
                
                # Display AI response
                with st.chat_message("assistant"):
                    st.markdown(ai_reply)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                
            except Exception as e:
                st.error(f"Failed to connect to Pulse AI Brain. Make sure your FastAPI backend (api.py) is running! Error: {e}")

    # ── FOOTER ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center;color:rgba(232,237,247,0.25);font-size:11px;
                letter-spacing:1.5px;text-transform:uppercase;padding:24px 0 8px'>
        Pulse AI · Neural Core v2.1 · For informational purposes only
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()