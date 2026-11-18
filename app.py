import json
import os

try:
    import gradio as gr
except ImportError:  # pragma: no cover - allows import in minimal test environments
    gr = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOCK_FILE = os.path.join(BASE_DIR, "mock_data.json")
PHOTOS_DIR = os.path.join(BASE_DIR, "sample_data", "photos")


def load_mock_data():
    if os.path.exists(MOCK_FILE):
        with open(MOCK_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


DATA = load_mock_data()

# File mapping using exact file basenames
PHOTO_MAP = {
    "Drax (Clear Dog)": {"key": "drax", "base": "Drax"},
    "Evy (Clear Dog)": {"key": "evy", "base": "Evy"},
    "Spadie (Clear Cat)": {"key": "spadie", "base": "Spadie"},
    "Dakota (Hard Case / Blurry)": {"key": "dakota", "base": "Dakota"},
    "Toby (Edge Case / Flagged)": {"key": "toby", "base": "Toby"},
}


def _safe_text(value, default="N/A"):
    if value is None or value == "":
        return default
    return str(value)


def _safe_upper(value, default="N/A"):
    text = _safe_text(value, default)
    if text == default:
        return default
    return text.upper()


def find_image_file(base_name):
    if not base_name:
        return None

    extensions = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]
    folders_to_check = [PHOTOS_DIR, BASE_DIR]

    for folder in folders_to_check:
        for ext in extensions:
            for candidate_name in {base_name, base_name.lower(), base_name.upper()}:
                path = os.path.join(folder, candidate_name + ext)
                if os.path.exists(path):
                    return path
    return None


def run_photo_to_profile(photo_selection):
    profiles = DATA.get("photo_to_profile", {})
    selected_info = PHOTO_MAP.get(photo_selection) or PHOTO_MAP.get("Drax (Clear Dog)", {})
    img_path = find_image_file(selected_info.get("base"))
    item = profiles.get(selected_info.get("key"), {})

    badge = "⚠️ Flagged for Human Review" if item.get("human_review") else "✅ Verified / Auto-Approved"

    photo_status = ""
    if not img_path:
        photo_status = f"\n\n*(Note: Photo file `{selected_info.get('base', 'Unknown')}.jpg` not found in `sample_data/photos/`)*"

    markdown_card = f"""
### 🐾 Adoption Listing Card: {item.get('pet_name', 'Unknown')}
* **Species:** {item.get('species', 'N/A')}
* **Estimated Breed:** {item.get('breed_guess', 'N/A')} *(Confidence: { _safe_upper(item.get('confidence', 'N/A')) })*
* **Estimated Age:** {item.get('estimated_age', 'N/A')}
* **Fee Tier:** {item.get('adoption_fee_tier', 'N/A')}
* **Review Status:** **{badge}**{photo_status}

**Personality & Household Profile:**
> {item.get('personality', 'No description available.')}

**Care & Living Requirements:**
> {item.get('care_requirements', 'No specific care instructions.')}
"""
    return img_path, markdown_card, json.dumps(item, indent=2, default=str)


# Part C1: Inquiry Triage
def get_triage_queue():
    queue = DATA.get("triage_queue", [])
    table_data = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        review_status = "⚠️ REVIEW" if item.get("human_review") else "AUTO"
        table_data.append([
            item.get("id"),
            _safe_upper(item.get("urgency"), "N/A"),
            item.get("category", "N/A"),
            item.get("routing", "Unassigned"),
            review_status,
            item.get("summary", "No summary")
        ])
    return table_data


# Part C2: Counselor Persona & Guardrail
def run_counselor_guardrail(query_type):
    counselor_data = DATA.get("counselor_demo", {})
    if query_type == "Standard Inquiry (Pass Case)":
        demo_case = counselor_data.get("valid_query", {})
    else:
        demo_case = counselor_data.get("caught_query", {})

    if not demo_case:
        user_msg = "No sample case available."
        draft = "No draft response available."
        status_header = "🟡 **Guardrail Verdict: NO DATA**"
        notes = "The mock data file is empty or missing the required counselor demo record."
        final_output = draft
        return user_msg, draft, status_header, notes, final_output

    user_msg = demo_case.get("adopter_message", "")
    draft = demo_case.get("draft_reply", "")
    verdict = demo_case.get("judge_verdict", "PASS")
    notes = demo_case.get("judge_notes", "")
    escalated = demo_case.get("requires_human_escalation", False)
    final_output = demo_case.get("escalation_message") or draft if escalated else draft

    badge_icon = "🟢" if verdict == "PASS" else "🔴"
    status_header = f"{badge_icon} **Guardrail Verdict: {verdict}**"

    return user_msg, draft, status_header, notes, final_output


# Part C3: Match Explainer
def run_match_explainer():
    match_data = DATA.get("match_demo", {})
    household = match_data.get("household_profile", "Household profile unavailable.")
    pet = match_data.get("pet_evaluated", "Pet profile unavailable.")
    verdict = match_data.get("majority_verdict", "No verdict available.")
    reasons = "\n".join([f"- {r}" for r in match_data.get("top_reasons", [])]) or "- No compatibility reasons available."
    concern = match_data.get("top_concern", "No primary concern available.")

    runs = match_data.get("runs", [])
    run_log = ""
    for r in runs:
        if not isinstance(r, dict):
            continue
        run_log += f"**Run {r.get('run_id', 'Unknown')} Verdict:** {r.get('fit_rating', 'N/A')}\n*Reasoning:* {r.get('reasoning', 'No reasoning provided.')}\n\n"

    if not run_log:
        run_log = "No individual run logs available."

    return household, pet, verdict, reasons, concern, run_log


# Part D: Innovation Feature
def run_intake_sentinel():
    sentinel = DATA.get("innovation_feature", {})
    rec = sentinel.get("sample_record", {})

    if not rec:
        report_text = """
### 🛡️ Shelter Intake & Quarantine Sentinel: No record available
* **Intake Date:** N/A
* **Rabies Status:** ❌ Missing / Not Available
* **DHPP Core Vaccine:** ❌ Missing
* **Bordetella Vaccine:** ❌ Missing
* **Quarantine Required:** **N/A**
* **Clinical Assessment:** No sample record available.
"""
        return report_text, "{}"

    report_text = f"""
### 🛡️ Shelter Intake & Quarantine Sentinel: {rec.get('pet_name', 'Unknown')} (ID: {rec.get('animal_id', 'N/A')})
* **Intake Date:** {rec.get('intake_date', 'N/A')}
* **Rabies Status:** {'✅ Current (Expires ' + rec.get('rabies_expiry', 'N/A') + ')' if rec.get('rabies_vaccinated') else '❌ Lapsed / Missing'}
* **DHPP Core Vaccine:** {'✅ Confirmed' if rec.get('dhpp_vaccinated') else '❌ Missing'}
* **Bordetella Vaccine:** {'✅ Confirmed' if rec.get('bordetella_vaccinated') else '⚠️ Pending Administration'}
* **Quarantine Required:** **{'YES - ISOLATION REQUIRED' if rec.get('quarantine_recommended') else 'NO - GENERAL HOUSING CLEARED'}**
* **Clinical Assessment:** {rec.get('quarantine_reason', 'No assessment provided.')}
"""
    return report_text, json.dumps(rec, indent=2, default=str)


# Gradio Application Interface
if gr is not None:
    with gr.Blocks(title="PawsConnect AI Suite", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🐾 PawsConnect AI Feature Suite")
        gr.Markdown("*Demonstrating Multimodal Extraction, Few-Shot Triage, Guardrails, and Match Reasoning.*")

        with gr.Tabs():
            # TAB 1: Part B
            with gr.Tab("Part B: Photo-to-Profile"):
                gr.Markdown("### Automatic Pet Listing Generator (Vision Extraction)")

                photo_dropdown = gr.Dropdown(
                    label="Select Pet Profile / Test Case",
                    choices=list(PHOTO_MAP.keys()),
                    value="Drax (Clear Dog)"
                )
                generate_profile_btn = gr.Button("Generate / Refresh Listing", variant="primary")

                with gr.Row():
                    with gr.Column(scale=1):
                        pet_image_display = gr.Image(label="Pet Photo", type="filepath", height=320)
                    with gr.Column(scale=2):
                        listing_display = gr.Markdown()

                with gr.Accordion("View Raw Structured JSON Record", open=False):
                    json_display = gr.Code(language="json")

                generate_profile_btn.click(
                    fn=run_photo_to_profile,
                    inputs=photo_dropdown,
                    outputs=[pet_image_display, listing_display, json_display]
                )
                photo_dropdown.change(
                    fn=run_photo_to_profile,
                    inputs=photo_dropdown,
                    outputs=[pet_image_display, listing_display, json_display]
                )
                demo.load(
                    fn=run_photo_to_profile,
                    inputs=photo_dropdown,
                    outputs=[pet_image_display, listing_display, json_display]
                )

            # TAB 2: Part C1
            with gr.Tab("Part C1: Inquiry Triage"):
                gr.Markdown("### Shelter Operations Triage Queue (Few-Shot Classification)")
                triage_btn = gr.Button("Refresh Triage Queue", variant="primary")
                triage_table = gr.Dataframe(
                    headers=["Message ID", "Urgency", "Category", "Routing Desk", "Human Review", "Summary"],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    value=get_triage_queue(),
                    interactive=False
                )
                triage_btn.click(fn=get_triage_queue, outputs=triage_table)

            # TAB 3: Part C2
            with gr.Tab("Part C2: Counselor Persona & Guardrail"):
                gr.Markdown("### Adoption Counselor Persona with LLM-as-Judge Guardrail")
                scenario_choice = gr.Radio(
                    label="Select Test Scenario",
                    choices=["Standard Inquiry (Pass Case)", "Veterinary Medical Advice Question (Caught / Revise Case)"],
                    value="Standard Inquiry (Pass Case)"
                )
                run_chat_btn = gr.Button("Submit to Counselor", variant="primary")

                adopter_input_disp = gr.Textbox(label="Adopter Question", interactive=False)
                draft_disp = gr.Textbox(label="Draft Model Response (Pre-Guardrail)", interactive=False)
                judge_verdict_disp = gr.Markdown()
                judge_notes_disp = gr.Textbox(label="LLM-as-Judge Evaluation & Notes", interactive=False)
                final_disp = gr.Textbox(label="Final Customer-Facing Response", interactive=False)

                run_chat_btn.click(
                    fn=run_counselor_guardrail,
                    inputs=scenario_choice,
                    outputs=[adopter_input_disp, draft_disp, judge_verdict_disp, judge_notes_disp, final_disp]
                )

            # TAB 4: Part C3
            with gr.Tab("Part C3: Adopter-Pet Match Explainer"):
                gr.Markdown("### Chain-of-Thought Compatibility Explainer with Self-Consistency Voting")
                evaluate_match_btn = gr.Button("Evaluate Compatibility", variant="primary")

                with gr.Row():
                    house_disp = gr.Textbox(label="Household Profile", lines=3, interactive=False)
                    pet_disp = gr.Textbox(label="Pet Profile Evaluated", lines=3, interactive=False)

                majority_disp = gr.Textbox(label="Self-Consistency Majority Verdict", interactive=False)
                reasons_disp = gr.Markdown()
                concern_disp = gr.Textbox(label="Primary Operational Concern", interactive=False)

                with gr.Accordion("View Step-by-Step Chain-of-Thought (Individual Runs)", open=False):
                    runs_disp = gr.Markdown()

                evaluate_match_btn.click(
                    fn=run_match_explainer,
                    outputs=[house_disp, pet_disp, majority_disp, reasons_disp, concern_disp, runs_disp]
                )

            # TAB 5: Part D
            with gr.Tab("Part D: Innovation Feature"):
                gr.Markdown("### Shelter Intake & Quarantine Sentinel")
                gr.Markdown("Automated extraction of paper intake documents to enforce medical quarantine protocols.")
                run_sentinel_btn = gr.Button("Process Intake Record", variant="primary")
                sentinel_report = gr.Markdown()
                with gr.Accordion("View Quarantine Record JSON", open=False):
                    sentinel_json = gr.Code(language="json")

                run_sentinel_btn.click(
                    fn=run_intake_sentinel,
                    outputs=[sentinel_report, sentinel_json]
                )
else:
    demo = None


if __name__ == "__main__":
    if demo is not None:
        demo.launch()
    else:
        print("Gradio is not installed. Please install gradio to launch the app.")
