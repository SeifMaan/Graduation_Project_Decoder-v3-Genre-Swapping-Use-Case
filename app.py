import json
import re
import streamlit as st
from pathlib import Path
from datetime import datetime

from retrieval import load_retrieval_data, retrieve_context
from generation import (
    compile_context,
    generate_blueprint,
    generate_outline,
    generate_scene,
)
from state import initialize_world_state, update_world_state, validate_scene

# ---------------------------------------------------------------------------
# Create output directories
# ---------------------------------------------------------------------------
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Create a session-specific subfolder for this generation run
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SAGA",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
}

.stApp {
    background-color: #0e0e0e;
    color: #e8e0d0;
}

h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: #e8e0d0 !important;
}

.saga-title {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 700;
    color: #e8e0d0;
    letter-spacing: 0.15em;
    text-align: center;
    margin-bottom: 0.1rem;
}

.saga-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #7a6f5e;
    text-align: center;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

.divider {
    border: none;
    border-top: 1px solid #2a2520;
    margin: 1.5rem 0;
}

.stage-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    padding: 2px 10px;
    border: 1px solid #5c4a2a;
    color: #c9a84c;
    background: #1a1508;
    margin-bottom: 0.5rem;
}

.prose-block {
    background: #141210;
    border-left: 3px solid #5c4a2a;
    padding: 1.5rem 2rem;
    font-family: 'Playfair Display', serif;
    font-size: 1rem;
    line-height: 1.9;
    color: #d4cabb;
    white-space: pre-wrap;
    border-radius: 0 4px 4px 0;
    margin-bottom: 1rem;
}

.warning-box {
    background: #1a0e08;
    border: 1px solid #7a3a1a;
    color: #e08050;
    padding: 0.6rem 1rem;
    font-size: 0.75rem;
    border-radius: 3px;
    margin-top: 0.5rem;
}

.json-block {
    background: #0a0a0a;
    border: 1px solid #2a2520;
    padding: 1rem;
    font-size: 0.72rem;
    color: #8a8070;
    border-radius: 4px;
    overflow-x: auto;
    max-height: 400px;
    overflow-y: auto;
}

.stat-row {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
    margin: 1rem 0;
}

.stat-chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #7a6f5e;
    border: 1px solid #2a2520;
    padding: 3px 10px;
    border-radius: 2px;
}

.stat-chip span {
    color: #c9a84c;
    margin-left: 6px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0a0a0a;
    border-right: 1px solid #1e1c18;
}

section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextArea label,
section[data-testid="stSidebar"] p {
    color: #7a6f5e !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* Inputs */
.stTextArea textarea, .stSelectbox select {
    background: #141210 !important;
    border: 1px solid #2a2520 !important;
    color: #e8e0d0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
}

/* Buttons */
.stButton > button {
    background: #1a1508 !important;
    border: 1px solid #5c4a2a !important;
    color: #c9a84c !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #2a2010 !important;
    border-color: #c9a84c !important;
}

/* Progress / spinner */
.stSpinner > div {
    border-top-color: #c9a84c !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: #141210 !important;
    color: #7a6f5e !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helper functions for saving files
# ---------------------------------------------------------------------------
def save_json_file(data: dict, filepath: Path) -> None:
    """Save JSON data to a file"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    st.info(f"💾 Saved: {filepath}")


def save_chapter(
    chapter_number: int, title: str, scenes: list[str], output_dir: Path
) -> None:
    """Save a chapter to a text file"""
    chapter_path = output_dir / f"chapter_{chapter_number:02d}.txt"

    with open(chapter_path, "w", encoding="utf-8") as f:
        f.write(f"CHAPTER {chapter_number}\n")
        f.write(f"{title}\n\n")
        f.write("\n\n---\n\n".join(scenes))

    st.info(f"💾 Saved: {chapter_path}")


def save_metadata(metadata: dict, output_dir: Path) -> None:
    """Save generation metadata"""
    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    st.info(f"💾 Saved: {metadata_path}")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="saga-title">S A G A</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="saga-sub">Structured Adaptive Generation Architecture</div>',
    unsafe_allow_html=True,
)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

# Hardcoded book title - only one book in DB
BOOK_TITLE = "A Court of Frost and Starlight.epub"

# ---------------------------------------------------------------------------
# Sidebar — configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Configuration")
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.info(f"📖 Using book: **{BOOK_TITLE}**")

    use_case = st.selectbox(
        "Use case",
        options=["sequel", "what_if", "genre_swap"],
        format_func=lambda x: {
            "sequel": "Sequel Generation",
            "what_if": "What-If / Divergent Timeline",
            "genre_swap": "Genre Swap",
        }[x],
    )

    genre = None
    if use_case == "genre_swap":
        genre = st.selectbox(
            "Target genre",
            options=["romcom", "fantasy", "psychological_thriller"],
            format_func=lambda x: {
                "romcom": "Romantic Comedy",
                "fantasy": "Fantasy",
                "psychological_thriller": "Psychological Thriller",
            }[x],
        )

    user_prompt = st.text_area(
        "Generation prompt",
        placeholder={
            "sequel": "Continue the story focusing on unresolved political tensions...",
            "what_if": "What if the protagonist never betrayed the kingdom?",
            "genre_swap": "Rewrite the story preserving its core relationships...",
        }.get(use_case, ""),
        height=120,
    )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    show_raw_context = st.checkbox("Show raw retrieved context", value=False)
    show_blueprint = st.checkbox("Show blueprint JSON", value=False)
    show_outline = st.checkbox("Show chapter outlines", value=False)
    show_warnings = st.checkbox("Show consistency warnings", value=True)

    # Option to save files
    save_files = st.checkbox("💾 Save outputs to files", value=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    run_btn = st.button("▶  Generate", use_container_width=True)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
if not run_btn:
    st.markdown(
        """
    <div style="text-align:center; margin-top: 5rem; color: #3a3530;">
        <div style="font-family: 'Playfair Display', serif; font-size: 1.4rem; font-style: italic;">
            Configure your generation in the sidebar<br>and press Generate to begin.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------
if not user_prompt.strip():
    st.error("A generation prompt is required.")
    st.stop()

# Create session output directory if saving files
if save_files:
    session_dir = OUTPUT_DIR / f"{use_case}_{timestamp}"
    session_dir.mkdir(exist_ok=True)
    st.info(f"📁 Files will be saved to: {session_dir}")

# ---------------------------------------------------------------------------
# Stage 1 — Retrieval
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="stage-badge">Stage 1 — Adaptive Retrieval</div>',
    unsafe_allow_html=True,
)

with st.spinner(f"Querying Neo4j for '{BOOK_TITLE}'..."):
    try:
        raw_data = load_retrieval_data(BOOK_TITLE)
        st.success(f"Successfully retrieved data for '{BOOK_TITLE}'")

        # Save raw retrieval data if saving files
        if save_files:
            data_dir = DATA_DIR
            retrieval_file = data_dir / f"retrieval_{timestamp}.json"
            save_json_file(raw_data, retrieval_file)

    except Exception as e:
        st.error(f"Neo4j retrieval failed: {e}")
        st.stop()

retrieved = retrieve_context(
    use_case=use_case,
    retrieval_data=raw_data,
    user_prompt=user_prompt,
    genre=genre,
)

# Save retrieved context
if save_files:
    context_file = session_dir / "retrieved_context.json"
    save_json_file(retrieved, context_file)

# Stats
stats_html = '<div class="stat-row">'
stats_html += f'<div class="stat-chip">mode<span>{retrieved["mode"]}</span></div>'
if genre:
    stats_html += f'<div class="stat-chip">genre<span>{genre}</span></div>'
stats_html += f'<div class="stat-chip">characters<span>{len(retrieved.get("character_states", []))}</span></div>'
stats_html += f'<div class="stat-chip">relationships<span>{len(retrieved.get("relationship_summary", []))}</span></div>'
if use_case == "sequel":
    stats_html += f'<div class="stat-chip">open threads<span>{len(retrieved.get("unresolved_threads", []))}</span></div>'
if use_case == "what_if":
    stats_html += f'<div class="stat-chip">causal chains<span>{len(retrieved.get("causal_chains", []))}</span></div>'
if use_case == "genre_swap":
    stats_html += f'<div class="stat-chip">genre events<span>{len(retrieved.get("genre_events", []))}</span></div>'
stats_html += "</div>"
st.markdown(stats_html, unsafe_allow_html=True)

if show_raw_context:
    with st.expander("Raw retrieved context"):
        st.markdown(
            f'<div class="json-block"><pre>{json.dumps(retrieved, indent=2, default=str)}</pre></div>',
            unsafe_allow_html=True,
        )

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Stage 2 — Compile + Blueprint
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="stage-badge">Stage 2 — Blueprint Generation</div>',
    unsafe_allow_html=True,
)

compiled = compile_context(
    retrieved_context=retrieved,
    user_prompt=user_prompt,
    use_case=use_case,
    genre=genre,
)

with st.spinner("Generating narrative blueprint..."):
    try:
        blueprint = generate_blueprint(compiled)

        # Save blueprint
        if save_files:
            blueprint_file = session_dir / "blueprint.json"
            save_json_file(blueprint, blueprint_file)

    except Exception as e:
        st.error(f"Blueprint generation failed: {e}")
        st.stop()

# Get total chapters from blueprint (default to 3 if not specified)
total_chapters = blueprint.get("total_chapters", blueprint.get("chapters", 3))
if isinstance(total_chapters, dict):
    total_chapters = len(total_chapters.get("chapters", [3]))
elif isinstance(total_chapters, list):
    total_chapters = len(total_chapters)
else:
    try:
        total_chapters = int(total_chapters)
    except:
        total_chapters = 3

st.success(f"Blueprint ready — {total_chapters} chapter arc planned.")

if show_blueprint:
    with st.expander("Blueprint JSON"):
        st.markdown(
            f'<div class="json-block"><pre>{json.dumps(blueprint, indent=2, default=str)}</pre></div>',
            unsafe_allow_html=True,
        )

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Stages 3-5 — Outline + Prose per chapter
# ---------------------------------------------------------------------------
world_state = initialize_world_state(compiled)
previous_summaries = []
previous_scene_ending = ""

# Store all generated chapters for saving
generated_chapters = []

# Use total_chapters from blueprint instead of user input
for chapter_num in range(1, total_chapters + 1):

    st.markdown(
        f'<div class="stage-badge">Chapter {chapter_num} — Outline & Prose</div>',
        unsafe_allow_html=True,
    )

    # Outline
    with st.spinner(f"Generating chapter {chapter_num} outline..."):
        try:
            outline = generate_outline(
                blueprint=blueprint,
                world_state=world_state,
                previous_summaries=previous_summaries,
                chapter_number=chapter_num,
            )

            # Save outline
            if save_files:
                outline_file = session_dir / f"chapter_{chapter_num:02d}_outline.json"
                save_json_file(outline, outline_file)

        except Exception as e:
            st.error(f"Outline generation failed for chapter {chapter_num}: {e}")
            break

    chapter_title = outline.get("chapter_title", f"Chapter {chapter_num}")
    st.markdown(f"### {chapter_num}. *{chapter_title}*")

    if show_outline:
        with st.expander(f"Chapter {chapter_num} outline"):
            st.markdown(
                f'<div class="json-block"><pre>{json.dumps(outline, indent=2, default=str)}</pre></div>',
                unsafe_allow_html=True,
            )

    # Scenes
    scenes = outline.get("scenes", [])
    chapter_scenes = []

    if not scenes:
        st.warning("No scenes returned in outline.")
    else:
        for scene_idx, scene in enumerate(scenes, 1):
            scene_label = scene.get("title", scene.get("summary", f"Scene {scene_idx}"))
            st.markdown(f"**{scene_label}**")

            with st.spinner(f"Writing scene: {scene_label}..."):
                try:
                    prose = generate_scene(
                        scene_outline=scene,
                        chapter_outline=outline,
                        world_state=world_state,
                        previous_scene_ending=previous_scene_ending,
                        genre=genre,
                    )
                except Exception as e:
                    st.error(f"Scene generation failed: {e}")
                    prose = ""

            if prose:
                st.markdown(
                    f'<div class="prose-block">{prose}</div>',
                    unsafe_allow_html=True,
                )

                chapter_scenes.append(prose)

                if show_warnings:
                    warnings = validate_scene(prose, world_state, outline, genre)
                    if warnings:
                        for w in warnings:
                            st.markdown(
                                f'<div class="warning-box">⚠ {w}</div>',
                                unsafe_allow_html=True,
                            )

                # Track ending for next scene continuity
                sentences = [s.strip() for s in prose.split(".") if s.strip()]
                previous_scene_ending = (
                    ". ".join(sentences[-3:]) if len(sentences) >= 3 else prose[-300:]
                )

    # Save chapter if we have scenes
    if chapter_scenes and save_files:
        save_chapter(chapter_num, chapter_title, chapter_scenes, session_dir)
        generated_chapters.append(
            {"number": chapter_num, "title": chapter_title, "scenes": chapter_scenes}
        )

    # Update world state
    world_state = update_world_state(world_state, outline)
    previous_summaries.append(f"Chapter {chapter_num} - {chapter_title}")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Save metadata and final output
# ---------------------------------------------------------------------------
if save_files and generated_chapters:
    # Save metadata about the generation
    metadata = {
        "timestamp": timestamp,
        "book_title": BOOK_TITLE,
        "use_case": use_case,
        "genre": genre,
        "user_prompt": user_prompt,
        "total_chapters": total_chapters,
        "chapters": generated_chapters,
    }
    save_metadata(metadata, session_dir)

    # Also save a compiled full story
    full_story_path = session_dir / "full_story.txt"
    with open(full_story_path, "w", encoding="utf-8") as f:
        for chapter in generated_chapters:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"CHAPTER {chapter['number']}\n")
            f.write(f"{chapter['title']}\n")
            f.write(f"{'='*60}\n\n")
            f.write("\n\n---\n\n".join(chapter["scenes"]))
            f.write("\n\n")
    st.info(f"💾 Saved full story: {full_story_path}")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<div style="text-align:center; padding: 2rem 0; color: #3a3530;">
    <div style="font-family: 'Playfair Display', serif; font-size: 1rem; font-style: italic;">
        Generation complete. Generated {total_chapters} chapter(s).
    </div>
    {f'<div style="font-size: 0.8rem; margin-top: 0.5rem;">Files saved to: {session_dir}</div>' if save_files and generated_chapters else ''}
</div>
""",
    unsafe_allow_html=True,
)
