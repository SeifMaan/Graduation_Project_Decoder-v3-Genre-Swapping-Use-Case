# retrieval.py
import json
import re
from collections import Counter
from datetime import datetime, timezone
from neo4j import GraphDatabase


NEO4J_URI = "neo4j://localhost:7687"
NEO4J_AUTH = ("neo4j", "12345678")
DB_NAME = "db5"

driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)


def run(session, query, **params):
    return session.run(query, **params).data()


# ===========================================================================
# WHAT-IF PROMPT PARSING
# ===========================================================================


def parse_what_if_prompt(user_prompt: str) -> dict:
    """Extract key elements from a what-if prompt"""
    elements = {
        "divergence_point": "",
        "changed_character_status": {},
        "new_relationships": [],
        "key_events": [],
        "time_skip": None,
        "original_prompt": user_prompt,
    }

    # Look for divergence point patterns
    lines = user_prompt.split("\n")
    for line in lines:
        lower_line = line.lower()
        if (
            "what if" in lower_line
            or "never" in lower_line
            or "chose to" in lower_line
            or "instead" in lower_line
        ):
            if not elements["divergence_point"]:
                elements["divergence_point"] = line.strip()

    # Look for character status changes
    character_patterns = [
        (r"(?:feyre|feyre archeron).*?(?:mercenary|human|not fae|mortal)", "Feyre"),
        (r"(?:rhys|rhysand).*?(?:dying|unraveling|weakened|bargain)", "Rhysand"),
        (r"(?:cassian).*?(?:assassin|hunting|tracking)", "Cassian"),
    ]

    for pattern, char_name in character_patterns:
        match = re.search(pattern, user_prompt.lower())
        if match:
            elements["changed_character_status"][char_name] = match.group(0)

    # Look for time references
    time_match = re.search(r"(\d+)\s*(year|month|week)s?", user_prompt.lower())
    if time_match:
        elements["time_skip"] = int(time_match.group(1))

    # Extract key events
    event_patterns = [
        r"(?:never|didn\'t|chose not to|walked away from)",
        r"(?:instead|alternatively)",
        r"(?:now|three years later|after)",
    ]

    for pattern in event_patterns:
        matches = re.findall(pattern + r"[^.!?]*[.!?]", user_prompt.lower())
        elements["key_events"].extend(matches)

    return elements


def generate_causal_chains_from_prompt(divergence_point: str, user_prompt: str) -> list:
    """Generate causal chain structure based on what-if prompt"""

    chains = []

    # Extract key changes from prompt
    if (
        "never went back" in user_prompt.lower()
        or "never returned" in user_prompt.lower()
    ):
        chains.append(
            {
                "chain_id": "divergence_001",
                "description": "Feyre never returns to save Tamlin Under the Mountain",
                "chain_type": "divergence",
                "story_function": "inciting_incident",
                "events": [
                    {
                        "event_id": "event_001",
                        "description": "Feyre kills Amarantha and walks away from Prythian",
                        "chapter": 1,
                        "time_index": 1,
                    },
                    {
                        "event_id": "event_002",
                        "description": "The bargain with Rhysand remains unfulfilled",
                        "chapter": 1,
                        "time_index": 2,
                    },
                ],
            }
        )

    if "mercenary" in user_prompt.lower() or "hunts" in user_prompt.lower():
        chains.append(
            {
                "chain_id": "character_001",
                "description": "Feyre becomes a hardened mercenary in human lands",
                "chain_type": "character_arc",
                "story_function": "transformation",
                "events": [],
            }
        )

    if "dying" in user_prompt.lower() and "rhys" in user_prompt.lower():
        chains.append(
            {
                "chain_id": "stakes_001",
                "description": "Rhysand deteriorates from unfulfilled bargain",
                "chain_type": "tension",
                "story_function": "stakes_escalation",
                "events": [],
            }
        )

    if "cassian" in user_prompt.lower() and (
        "assassin" in user_prompt.lower() or "hunting" in user_prompt.lower()
    ):
        chains.append(
            {
                "chain_id": "conflict_001",
                "description": "Cassian sent as assassin, becomes hunted instead",
                "chain_type": "irony",
                "story_function": "reversal",
                "events": [],
            }
        )

    return chains


# ===========================================================================
# NEO4J RETRIEVAL FUNCTIONS
# ===========================================================================


def get_book_meta(s, book_title):
    rows = run(s, "MATCH (b:Book {title: $title}) RETURN b", title=book_title)
    if not rows:
        raise ValueError(f"Book '{book_title}' not found in database.")
    return dict(rows[0]["b"])


def get_ending_events(s, book_title, top_n=10):
    rows = run(
        s,
        """
        MATCH (b:Book {title: $title})-[:HAS_EVENT]->(e:Event)
        WHERE e.is_critical = true
        RETURN e.id             AS id,
               e.description    AS description,
               e.chapter_index  AS chapter,
               e.criticality_score AS score,
               e.why_critical   AS why_critical,
               e.critical_order AS order,
               e.story_impact   AS story_impact
        ORDER BY e.critical_order DESC
        LIMIT $n
        """,
        title=book_title,
        n=top_n,
    )
    return sorted(rows, key=lambda r: r.get("order") or 0)


def get_character_states(s, book_title):
    entities = run(
        s,
        """
        MATCH (b:Book {title: $title})-[:HAS_ENTITY]->(e:Entity)
        WHERE e.entity_type = 'character'
        RETURN e.name           AS name,
               e.mention_count  AS mention_count,
               e.descriptions   AS descriptions,
               e.first_seen_ch  AS first_seen_chapter,
               properties(e)    AS all_props
        ORDER BY e.mention_count DESC
        """,
        title=book_title,
    )

    # If no characters found via relationship, try direct Entity query
    if not entities:
        entities = run(
            s,
            """
            MATCH (e:Entity)
            WHERE e.entity_type = 'character'
            RETURN e.name           AS name,
                   e.mention_count  AS mention_count,
                   e.descriptions   AS descriptions,
                   e.first_seen_ch  AS first_seen_chapter,
                   properties(e)    AS all_props
            ORDER BY e.mention_count DESC
            LIMIT 20
            """,
        )

    results = []
    for ent in entities:
        name = ent["name"]

        canon_state = {
            k.replace("canon_", ""): v
            for k, v in (ent["all_props"] or {}).items()
            if k.startswith("canon_")
        }

        aliases = run(
            s,
            """
            MATCH (e:Entity {name: $name})-[:HAS_ALIAS]->(a:Alias)
            RETURN a.text AS alias
            """,
            name=name,
        )

        transitions = run(
            s,
            """
            MATCH (e:Entity {name: $name})-[:HAD_STATE_CHANGE]->(st:StateTransition)
            RETURN st.attribute      AS attribute,
                   st.previous_state AS previous_state,
                   st.new_state      AS new_state,
                   st.change_type    AS change_type,
                   st.evidence       AS evidence,
                   st.chapter_index  AS chapter
            ORDER BY st.chapter_index ASC
            """,
            name=name,
        )

        results.append(
            {
                "name": name,
                "mention_count": ent["mention_count"],
                "first_seen_chapter": ent["first_seen_chapter"],
                "descriptions": ent.get("descriptions") or [],
                "aliases": [a["alias"] for a in aliases],
                "canon_state": canon_state,
                "state_transitions": [dict(t) for t in transitions],
            }
        )

    return results


def get_relationship_summary(s):
    rows = run(
        s,
        """
        MATCH (a:Entity)-[r:HAS_RELATIONSHIP]->(b:Entity)
        RETURN a.name             AS entity_a,
               b.name             AS entity_b,
               r.type             AS relationship_type,
               r.latest_change    AS latest_change,
               r.latest_evidence  AS evidence,
               r.last_seen_ch     AS last_seen_chapter
        ORDER BY r.last_seen_ch DESC
        """,
    )
    return [dict(r) for r in rows]


def get_unresolved_threads(s, book_title, min_potential=7):
    rows = run(
        s,
        """
        MATCH (e:Event)-[:IS_DIVERGENCE_POINT]->(d:DivergencePoint)
        WHERE d.divergence_potential >= $min_potential
        RETURN e.id                    AS event_id,
               e.description           AS event_description,
               e.chapter_index         AS chapter,
               e.is_critical           AS is_critical,
               d.decision_made         AS decision_made,
               d.alternatives          AS alternatives,
               d.divergence_potential  AS divergence_potential,
               d.alternate_timeline    AS alternate_timeline
        ORDER BY d.divergence_potential DESC
        """,
        min_potential=min_potential,
    )
    return [dict(r) for r in rows]


def get_causal_chains(s):
    chains = run(
        s,
        """
        MATCH (cc:CausalChain)
        RETURN cc.chain_id      AS chain_id,
               cc.description   AS description,
               cc.chain_type    AS chain_type,
               cc.story_function AS story_function
        """,
    )
    result = []
    for chain in chains:
        chain_id = chain["chain_id"]
        events = run(
            s,
            """
            MATCH (e:Event)-[:IN_CHAIN]->(cc:CausalChain {chain_id: $chain_id})
            RETURN e.id          AS event_id,
                   e.description AS description,
                   e.chapter_index AS chapter,
                   e.time_index  AS time_index
            ORDER BY e.time_index ASC
            """,
            chain_id=chain_id,
        )
        result.append(
            {
                **dict(chain),
                "events": [dict(e) for e in events],
            }
        )
    return result


def get_flexible_events(s, book_title):
    rows = run(
        s,
        """
        MATCH (b:Book {title: $title})-[:HAS_EVENT]->(e:Event)
        WHERE e.is_flexible = true
        RETURN e.id               AS event_id,
               e.description      AS description,
               e.chapter_index    AS chapter,
               e.flexibility_score AS flexibility_score,
               e.why_flexible     AS why_flexible
        ORDER BY e.flexibility_score DESC
        """,
        title=book_title,
    )
    return [dict(r) for r in rows]


def get_last_scene(s, book_title):
    scene = run(
        s,
        """
        MATCH (b:Book {title: $title})-[:HAS_CHAPTER]->(ch:Chapter)-[:HAS_SCENE]->(sc:Scene)
        RETURN sc.summary      AS summary,
               sc.book_index   AS book_index,
               sc.chapter_index AS chapter_index,
               sc.scene_index  AS scene_index
        ORDER BY sc.chapter_index DESC, sc.scene_index DESC
        LIMIT 1
        """,
        title=book_title,
    )
    if not scene:
        return {}

    sc = dict(scene[0])
    bi, ci, si = sc["book_index"], sc["chapter_index"], sc["scene_index"]

    present = run(
        s,
        """
        MATCH (sc:Scene {book_index: $bi, chapter_index: $ci, scene_index: $si})
              -[:FEATURES]->(e:Entity)
        RETURN e.name AS name, e.entity_type AS entity_type
        """,
        bi=bi,
        ci=ci,
        si=si,
    )

    location = run(
        s,
        """
        MATCH (sc:Scene {book_index: $bi, chapter_index: $ci, scene_index: $si})
              -[:LOCATED_IN]->(l:Entity)
        RETURN l.name AS name, l.description AS description
        """,
        bi=bi,
        ci=ci,
        si=si,
    )

    rel_changes = run(
        s,
        """
        MATCH (sc:Scene {book_index: $bi, chapter_index: $ci, scene_index: $si})
              -[:HAS_RELATIONSHIP_CHANGE]->(rc:RelationshipChange)
        RETURN rc.source_entity AS source,
               rc.target_entity AS target,
               rc.relationship  AS relationship,
               rc.change        AS change,
               rc.evidence      AS evidence
        """,
        bi=bi,
        ci=ci,
        si=si,
    )

    state_changes = run(
        s,
        """
        MATCH (sc:Scene {book_index: $bi, chapter_index: $ci, scene_index: $si})
              -[:HAS_SCENE]-(:Chapter)
        WITH sc
        MATCH (e:Entity)-[:HAD_STATE_CHANGE]->(st:StateTransition {
            chapter_index: $ci,
            scene_index: $si
        })
        RETURN e.name       AS entity,
               st.attribute AS attribute,
               st.new_state AS new_state,
               st.evidence  AS evidence
        """,
        bi=bi,
        ci=ci,
        si=si,
    )

    return {
        **sc,
        "location": location[0] if location else None,
        "entities_present": [dict(p) for p in present],
        "relationship_changes": [dict(r) for r in rel_changes],
        "state_changes": [dict(r) for r in state_changes],
    }


def get_character_timelines_summary(s, top_n_chars=6):
    top_chars = run(
        s,
        """
        MATCH (e:Entity)
        WHERE e.entity_type = 'character' AND e.mention_count IS NOT NULL
        RETURN e.name AS name
        ORDER BY e.mention_count DESC
        LIMIT $n
        """,
        n=top_n_chars,
    )

    result = []
    for char in top_chars:
        name = char["name"]
        events = run(
            s,
            """
            MATCH (c:Entity {name: $name})-[r:APPEARS_IN_EVENT]->(e:Event)
            RETURN e.id           AS event_id,
                   e.description  AS description,
                   e.chapter_index AS chapter,
                   r.time_index   AS time_index
            ORDER BY r.time_index DESC
            LIMIT 5
            """,
            name=name,
        )
        result.append(
            {
                "character": name,
                "last_events": [dict(e) for e in reversed(events)],
            }
        )
    return result


def get_all_books(s):
    """Helper function to get all book titles in the database"""
    rows = run(s, "MATCH (b:Book) RETURN b.title as title")
    return [row["title"] for row in rows]


# ===========================================================================
# LOADER — Neo4j → flat dict
# ===========================================================================


def load_retrieval_data(book_title: str) -> dict:
    """
    Queries Neo4j and assembles a flat dict that retrieve_context() can consume.
    Call this once per request, then pass the result into retrieve_context().
    """
    with driver.session(database=DB_NAME) as s:
        # First, verify the book exists
        book_check = run(s, "MATCH (b:Book {title: $title}) RETURN b", title=book_title)
        if not book_check:
            raise ValueError(
                f"Book '{book_title}' not found in database. Available books: {get_all_books(s)}"
            )

        ending_events = get_ending_events(s, book_title)
        last_scene = get_last_scene(s, book_title)
        char_states = get_character_states(s, book_title)
        relationships = get_relationship_summary(s)
        threads = get_unresolved_threads(s, book_title)
        chains = get_causal_chains(s)
        flexible = get_flexible_events(s, book_title)
        trajectories = get_character_timelines_summary(s)

    # Debug info (will appear in terminal where streamlit runs)
    print(f"[DEBUG] Book: {book_title}")
    print(f"[DEBUG] Loaded {len(char_states)} characters")
    print(f"[DEBUG] Loaded {len(relationships)} relationships")
    print(f"[DEBUG] Loaded {len(flexible)} flexible events")
    print(f"[DEBUG] Loaded {len(threads)} unresolved threads")
    print(f"[DEBUG] Loaded {len(chains)} causal chains")

    return {
        # sequel
        "story_ending": {"last_scene": last_scene, "critical_path_tail": ending_events},
        "character_states": char_states,
        "relationship_summary": relationships,
        "unresolved_threads": threads,
        "causal_chains": chains,
        "character_trajectories": trajectories,
        # what_if
        "critical_events": ending_events,
        # genre_swap
        "events": flexible,
        "world_lore": [],
    }


# ===========================================================================
# CONTEXT SLICING — use-case routing with enhanced what-if
# ===========================================================================


def retrieve_context(
    use_case: str,
    retrieval_data: dict,
    user_prompt: str,
    genre: str | None = None,
) -> dict:

    if use_case == "sequel":
        return _retrieve_sequel_context(retrieval_data)

    if use_case == "what_if":
        return _retrieve_what_if_context(retrieval_data, user_prompt)

    if use_case == "genre_swap":
        return _retrieve_genre_context(retrieval_data, genre)

    raise ValueError(f"Unsupported use case: {use_case}")


def _retrieve_sequel_context(data: dict) -> dict:
    return {
        "mode": "sequel",
        "story_ending": data.get("story_ending", {}),
        "character_states": data.get("character_states", [])[:10],
        "relationship_summary": data.get("relationship_summary", [])[:15],
        "unresolved_threads": sorted(
            data.get("unresolved_threads", []),
            key=lambda x: x.get("divergence_potential", 0),
            reverse=True,
        )[:8],
        "character_trajectories": data.get("character_trajectories", [])[:10],
    }


def _retrieve_what_if_context(data: dict, user_prompt: str) -> dict:
    """
    Enhanced what-if retrieval that prioritizes the user prompt over canon data.
    For what-if scenarios, we return minimal canon data and let the prompt
    define the alternative reality.
    """

    # Parse the what-if prompt for key elements
    what_if_elements = parse_what_if_prompt(user_prompt)

    # Generate causal chains based on the prompt
    causal_chains_from_prompt = generate_causal_chains_from_prompt(
        what_if_elements["divergence_point"], user_prompt
    )

    # Get some canon data for reference (but mark that it should be overridden)
    canon_chains = data.get("causal_chains", [])
    canon_characters = data.get("character_states", [])[:5]

    print(f"[DEBUG] WHAT-IF MODE ACTIVE")
    print(f"[DEBUG] Divergence point: {what_if_elements['divergence_point'][:100]}")
    print(f"[DEBUG] Time skip: {what_if_elements['time_skip']} years")
    print(
        f"[DEBUG] Character changes detected: {len(what_if_elements['changed_character_status'])}"
    )

    return {
        "mode": "what_if",
        "what_if_premise": {
            "divergence_point": what_if_elements["divergence_point"],
            "time_skip": what_if_elements["time_skip"],
            "character_status_changes": what_if_elements["changed_character_status"],
            "key_events": what_if_elements["key_events"][:5],
            "full_prompt": user_prompt,
        },
        # Return minimal canon data - let prompt override
        "character_states": [],  # Empty so prompt takes precedence
        "relationship_summary": [],  # Empty so prompt takes precedence
        "causal_chains": causal_chains_from_prompt,  # Use prompt-generated chains
        "canon_reference": {  # For reference only, marked as canon to ignore
            "canon_characters": canon_characters,
            "canon_chains": canon_chains[:3] if canon_chains else [],
        },
        "user_prompt_override": user_prompt,
        "override_instruction": "IGNORE ALL CANON RELATIONSHIPS. Follow the what_if_premise strictly.",
    }


def _retrieve_genre_context(data: dict, genre: str) -> dict:
    events = data.get("events", [])

    # Also try to get regular events if flexible events are empty
    if not events:
        events = data.get("critical_events", [])[:15]
        print(
            f"[DEBUG] No flexible events found, using {len(events)} critical events instead"
        )

    ranked = sorted(
        events,
        key=lambda e: _genre_score(genre, e.get("description", "")),
        reverse=True,
    )

    return {
        "mode": "genre_swap",
        "genre": genre,
        "genre_events": ranked[:15],
        "character_states": data.get("character_states", [])[:10],
        "relationship_summary": data.get("relationship_summary", [])[:15],
        "world_lore": data.get("world_lore", [])[:10],
    }


# ===========================================================================
# SCORING HELPERS
# ===========================================================================


def _keyword_overlap(a: str, b: str) -> int:
    return len(set(a.lower().split()) & set(b.lower().split()))


def _genre_score(genre: str, text: str) -> int:
    genre_keywords = {
        "romcom": [
            "love",
            "relationship",
            "kiss",
            "awkward",
            "funny",
            "banter",
            "romance",
            "date",
            "heart",
            "smile",
            "laugh",
        ],
        "fantasy": [
            "magic",
            "kingdom",
            "war",
            "dragon",
            "curse",
            "prophecy",
            "spell",
            "sword",
            "throne",
            "fae",
            "prythian",
        ],
        "psychological_thriller": [
            "fear",
            "secret",
            "suspicion",
            "paranoia",
            "murder",
            "dark",
            "twist",
            "mind",
            "betrayal",
            "hunt",
            "stalk",
            "watch",
            "hide",
            "truth",
            "lied",
        ],
    }
    counter = Counter(text.lower().split())
    return sum(counter.get(kw, 0) for kw in genre_keywords.get(genre, []))


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGA Retrieval Layer")
    parser.add_argument("--book", default="A Court of Frost and Daylight")
    parser.add_argument(
        "--use-case", default="sequel", choices=["sequel", "what_if", "genre_swap"]
    )
    parser.add_argument("--prompt", default="")
    parser.add_argument("--genre", default=None)
    parser.add_argument("--out", default="retrieval_context.json")
    args = parser.parse_args()

    data = load_retrieval_data(args.book)
    context = retrieve_context(
        use_case=args.use_case,
        retrieval_data=data,
        user_prompt=args.prompt,
        genre=args.genre,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2, ensure_ascii=False, default=str)

    print(f"[SAGA] Context saved to: {args.out}")
    print(f"[SAGA] Mode: {context.get('mode')}")
    if context.get("mode") == "what_if":
        print(
            f"[SAGA] What-if divergence: {context.get('what_if_premise', {}).get('divergence_point', 'Unknown')[:100]}"
        )

    # Close the driver
    driver.close()
