import json

BLUEPRINT_SYSTEM = """
You are a master narrative architect specializing in story structure.

Create a detailed, comprehensive story blueprint based on the provided context.

Your blueprint MUST include:
- A compelling title
- A clear premise
- Total chapters (between 5-30 depending on story complexity)
- Central conflict
- Character arcs for main characters (with start state, end state, and key turning points)
- Acts with chapter ranges and narrative goals

IMPORTANT: For WHAT-IF scenarios, completely ignore canon relationships and character states.
The user prompt defines the alternative reality - follow it strictly.

Return ONLY valid JSON. No other text.
"""


OUTLINE_SYSTEM = """
You are a narrative planner.

Create a detailed chapter outline with specific scenes.

For WHAT-IF scenarios: Follow the alternative premise strictly.
For SEQUEL: Continue from where the story ended.
For GENRE_SWAP: Maintain plot points but adjust tone.

Return ONLY valid JSON with this exact structure:
{
    "chapter_number": number,
    "chapter_title": "string",
    "scenes": [
        {
            "title": "string",
            "summary": "string",
            "pov_character": "string",
            "key_beats": ["beat1", "beat2"]
        }
    ],
    "world_state_changes": []
}
"""


PROSE_SYSTEM = """
You are a professional fiction writer.

Write immersive, vivid scene prose that:
- Maintains consistent character voices
- Shows, doesn't tell
- Includes sensory details
- Advances the plot
- Maintains continuity

For WHAT-IF scenarios: Write as if the alternative reality is the ONLY reality.
Do not reference canon events that didn't happen in this timeline.

Write 500-1000 words per scene.
"""


ROMCOM_STYLE = """
Tone:
- witty and playful dialogue
- emotionally warm
- comedic misunderstandings
- romantic tension with humor
- banter between characters
- lighthearted even during conflict
"""


FANTASY_STYLE = """
Tone:
- mythic and epic
- immersive worldbuilding
- lyrical prose
- high emotional stakes
- magical elements woven naturally
"""


THRILLER_STYLE = """
Tone:
- tense and suspenseful
- psychologically intense
- paranoid atmosphere
- quick pacing
- unexpected revelations
- dark and brooding
"""


def get_genre_modifier(genre: str | None):
    """Get genre-specific tone modifiers"""
    if genre == "romcom":
        return ROMCOM_STYLE
    if genre == "fantasy":
        return FANTASY_STYLE
    if genre == "psychological_thriller":
        return THRILLER_STYLE
    return ""


def parse_what_if_prompt(user_prompt: str) -> dict:
    """Extract key elements from a what-if prompt"""
    elements = {
        "divergence_point": "",
        "changed_character_status": {},
        "new_relationships": [],
        "key_events": [],
        "time_skip": None,
    }

    # Look for common patterns
    if "never" in user_prompt.lower() or "didn't" in user_prompt.lower():
        # Extract divergence point
        lines = user_prompt.split("\n")
        for line in lines:
            if "what if" in line.lower() or "chose to" in line.lower():
                elements["divergence_point"] = line.strip()

    # Look for time references
    import re

    time_match = re.search(r"(\d+)\s*(year|month|week)s?", user_prompt.lower())
    if time_match:
        elements["time_skip"] = int(time_match.group(1))

    return elements


def build_blueprint_prompt(
    compiled_context: dict,
    genre_modifier: str,
) -> str:
    """Build prompt for blueprint generation with enhanced what-if handling"""

    use_case = compiled_context.get("use_case", "sequel")
    user_prompt = compiled_context.get("user_prompt", "")
    genre = compiled_context.get("genre")
    retrieved_context = compiled_context.get("retrieved_context", {})

    # Special handling for what-if scenarios
    what_if_override = ""
    if use_case == "what_if":
        what_if_override = f"""
⚠️ IMPORTANT - THIS IS A WHAT-IF SCENARIO ⚠️

The user has specified an alternative reality. IGNORE the retrieved context if it contradicts this premise.

ALTERNATIVE REALITY PREMISE:
{user_prompt}

Follow this premise EXACTLY. Do not use canon relationships or character states.
Create a completely new story where:
1. The divergence point is strictly followed
2. Character statuses are as described in the prompt
3. Relationships are as described in the prompt
4. Canon events that wouldn't happen in this timeline are ignored

GENERATE A BLUEPRINT FOR THIS ALTERNATIVE REALITY ONLY.
"""

    # Normal context for sequel/genre_swap
    normal_context = f"""
RETRIEVED CONTEXT (for reference only - use as source material):
{json.dumps(retrieved_context, indent=2)[:4000]}

USER PROMPT/DIRECTION:
{user_prompt}

USE CASE: {use_case}
{"" if not genre else f"TARGET GENRE: {genre}"}

GENRE MODIFIER:
{genre_modifier}
"""

    # Combine based on use case
    if use_case == "what_if":
        context_section = what_if_override
    else:
        context_section = normal_context

    return f"""
{context_section}

Based on this information, create a complete story blueprint.
The blueprint should be detailed and structured.
Include character arcs, acts, and total chapters.

For SEQUEL: Continue naturally from where the story left off.
For WHAT-IF: Create an entirely new timeline based on the premise.
For GENRE_SWAP: Keep plot points, change tone.

Return ONLY valid JSON.
"""


def build_outline_prompt(
    blueprint: dict,
    world_state: dict,
    previous_summaries: list[str],
    chapter_number: int,
) -> str:
    """Build prompt for chapter outline generation"""

    # Extract what-if context if present
    what_if_note = ""
    if "what_if_premise" in blueprint:
        what_if_note = f"""
WHAT-IF NOTE: This chapter MUST follow the alternative reality premise:
{blueprint.get('what_if_premise', '')}

Ignore canon. Write for the alternative timeline only.
"""

    return f"""
{what_if_note}

BLUEPRINT:
{json.dumps(blueprint, indent=2)[:3000]}

CURRENT WORLD STATE:
{json.dumps(world_state, indent=2)[:1500]}

PREVIOUS CHAPTER SUMMARIES:
{json.dumps(previous_summaries, indent=2)}

Generate a detailed outline for chapter {chapter_number}.
Include 2-4 scenes that advance the story according to the blueprint.

For WHAT-IF: Ensure the chapter reflects the alternative reality described in the blueprint.
For SEQUEL: Maintain continuity with previous events.
For GENRE_SWAP: Keep plot progression, adjust tone.

Return ONLY valid JSON with the specified structure.
"""


def build_scene_prompt(
    scene_outline: dict,
    chapter_outline: dict,
    world_state: dict,
    previous_scene_ending: str,
    genre_modifier: str,
) -> str:
    """Build prompt for scene prose generation"""

    pov_character = scene_outline.get("pov_character", "Feyre")
    scene_title = scene_outline.get("title", "Untitled Scene")
    scene_summary = scene_outline.get("summary", "No summary provided")

    # Extract what-if override if present in world_state
    what_if_note = ""
    if world_state.get("what_if_mode"):
        what_if_note = f"""
⚠️ WHAT-IF MODE ACTIVE ⚠️
This scene takes place in an alternative reality.
Do not reference canon events that didn't happen in this timeline.
Write as if the what-if premise is the ONLY true history.
POV Character Status: {world_state.get('what_if_character_status', {}).get(pov_character, 'As defined in premise')}
"""

    return f"""
{what_if_note}

CHAPTER CONTEXT:
Title: {chapter_outline.get('chapter_title', 'Unknown')}
Number: {chapter_outline.get('chapter_number', 'Unknown')}

SCENE TO WRITE:
Title: {scene_title}
Summary: {scene_summary}
POV Character: {pov_character}
Key Beats: {json.dumps(scene_outline.get('key_beats', []), indent=2)}

WORLD STATE (current):
{json.dumps(world_state, indent=2)[:1000]}

WHERE THE PREVIOUS SCENE ENDED:
{previous_scene_ending}

GENRE MODIFIER:
{genre_modifier}

Write this scene as immersive prose. Start where the previous scene ended.
Include:
- Dialogue that reveals character
- Sensory details (sights, sounds, smells, textures)
- Emotional beats
- Physical descriptions

Write approximately 500-800 words.
Maintain consistency with the world state and previous events.
{ "Follow the what-if premise strictly." if world_state.get("what_if_mode") else "Stay true to established characters." }
"""


def build_what_if_divergence_prompt(
    user_prompt: str,
    retrieved_context: dict,
) -> str:
    """Special prompt for establishing what-if divergence points"""

    # Parse the what-if prompt
    elements = parse_what_if_prompt(user_prompt)

    return f"""
WHAT-IF SCENARIO ANALYSIS

USER'S ALTERNATIVE REALITY:
{user_prompt}

IDENTIFIED ELEMENTS:
- Divergence Point: {elements['divergence_point']}
- Time Skip: {elements['time_skip'] if elements['time_skip'] else 'Not specified'} years
- Character Changes: {json.dumps(elements['changed_character_status'], indent=2)}

ORIGINAL CANON (TO BE OVERRIDDEN):
Key characters from source material but their relationships and statuses may change.

YOUR TASK:
Create a divergence analysis that:
1. Identifies the exact point where history changed
2. Maps out the ripple effects of that change
3. Defines new character statuses and relationships
4. Establishes the new "canon" for this timeline

Return JSON with:
{{
    "divergence_point": "description of when/where things changed",
    "causal_ripples": ["effect1", "effect2"],
    "character_changes": {{
        "character_name": {{
            "original_status": "what they were",
            "new_status": "what they are in this timeline",
            "reason_for_change": "why"
        }}
    }},
    "relationship_changes": [
        {{
            "relationship": "description",
            "original_state": "canon state",
            "new_state": "what-if state"
        }}
    ],
    "new_timeline_premise": "one sentence summary of the alternative reality"
}}
"""


def build_causal_chain_prompt(
    divergence_point: str,
    user_prompt: str,
) -> str:
    """Build prompt for generating causal chains from a divergence point"""

    return f"""
CAUSAL CHAIN GENERATION

DIVERGENCE POINT:
{divergence_point}

USER PROMPT:
{user_prompt}

Generate a causal chain showing how this single change ripples through the story.

For each major event that would change, explain:
1. What originally happened (canon)
2. What happens instead (what-if)
3. Why this change occurs

Return JSON array of causal links:
[
    {{
        "event_name": "name",
        "canon_version": "what happened originally",
        "what_if_version": "what happens in alternative timeline",
        "causal_reason": "why this change occurs",
        "affected_characters": ["character1", "character2"]
    }}
]
"""
