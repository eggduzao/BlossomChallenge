# **Blossom Challenge** 🏰🎭
> Author: **Eduardo Gade Gusmao**

Maximum Matching in a Castle Ball — with emojis, Manhattan geometry, and a dash of magic.

Welcome to the Blossom Challenge: given a castle floor plan drawn in UTF-8 text (walls, entrance, and a lively crowd of guests rendered as emojis), build a graph from their 2-D spatial configuration (Manhattan distances), apply natural-language dance rules, and compute the maximum number of dancing individuals using a graph-matching algorithm (e.g., Edmonds’ Blossom for general graphs).

Output per dataset: a single integer — the size of the maximum matching (i.e., the number of dancers, not pairs).

---

## ✨ **Story**

The Royal House opens the castle to everyone for a Town Free-Ball. From Queens and Kings to Villagers and Entertainers, the hall fills with potential pairs. Some guests will dance with everyone (looking at you, Jesters 🤹), some won’t dance with specific groups, and the occasional Unicorn 🦄 brings… special rules.

---

## 📦 **What You’re Given**

- A folder of UTF-8 .txt datasets named after places: angkor.txt, andalusia.txt, etc.
- All input test files can be found in ``src/data/``.
- Each file encodes:
	1. an R radius (integer, Manhattan metric),
	2. a castle map (any 2-D shape) using emojis and spaces,
	3. a rule block (natural language with a fixed grammar).

**You produce one integer per dataset:** the maximum number of people who can dance simultaneously (size of the maximum matching).

---

## 🧱🧭 **Input Format**

A dataset file is UTF-8 text with three sections, in order:

1. Radius line (first non-empty line):

```
R = <integer>
```

2.	Map block (one or more lines):

- The castle map is a grid of UTF-8 characters.
- Walls: 🧱 (must appear at least once; the last line containing any 🧱 marks the end of the map block)
- Entrance: 🏰 (optional, treated like floor)
- People/objects: represented as emojis (see the table below).
- Spaces/tabs: walkable floor (people occupy a single text position).
- The castle can be any shape; it does not need to be rectangular or fully enclosed.

3.	Rule block (starts immediately after the last map line containing 🧱):

- One rule per line (UTF-8 text).
- The first three rules are always present:
	- JESTER DANCES WITH ALL
	- FLOWER ONLY DANCES WITH JESTER
	- UNICORN CONNECTS TO ALL AND DANCES WITH ANY
- All other rules are negative constraints of the form:
- <ROLE_A> DOES NOT DANCE WITH <ROLE_B>

> [!NOTE]
> Rules may reference roles that do not appear in the map (harmless) and roles that do appear but have zero instances (also harmless).

> [!TIP]
> Some castle configurations can be very different from what we are used to...

---

## 🧑‍🤝‍🧑 **Canonical Roles & Emojis (UPPER_SNAKE_CASE)**

Each role has a number of fixed, canonical UTF-8 friendly emojis for parsing (consistent across datasets).

| ROLE (name in rules)      | Emojis                                                    | Notes                        |
|--------------------------|------------------------------------------------------------|------------------------------|
| **QUEEN**                | 👸                                                         | exactly one mandatory        |
| **KING**                 | 🤴                                                         | exactly one mandatory        |
| **PRINCESS**             | 👰🏻‍♀ 👰🏼‍♀ 👰🏽‍♀ 👰🏾‍♀ 👰🏿‍♀ 👰‍♀                                         | 1–9 (example canonical)      |
| **PRINCE**               | 🤵🏻‍♂ 🤵🏼‍♂ 🤵🏽‍♂ 🤵🏾‍♂ 🤵🏿‍♂ 🤵‍♂                                         | 1–9 (example canonical)      |
| **ROYAL_ADVISOR**        | 👨🏻‍🎓 👨🏼‍🎓 👨🏽‍🎓 👨🏾‍🎓 👨🏿‍🎓 👨‍🎓 👩🏻‍🎓 👩🏼‍🎓 👩🏽‍🎓 👩🏾‍🎓 👩🏿‍🎓 👩‍🎓 🧑🏻‍🎓 🧑🏼‍🎓 🧑🏽‍🎓 🧑🏾‍🎓 🧑🏿‍🎓 🧑‍🎓 | 1–9                          |
| **CAPTAIN_OF_THE_GUARD** | 🛡️                                                          | 0–1                          |
| **COURT_ATTENDANT**      | 👨🏻‍🍳 👨🏼‍🍳 👨🏽‍🍳 👨🏾‍🍳 👨🏿‍🍳 👨‍🍳 👩🏻‍🍳 👩🏼‍🍳 👩🏽‍🍳 👩🏾‍🍳 👩🏿‍🍳 👩‍🍳 🧑🏻‍🍳 🧑🏼‍🍳 🧑🏽‍🍳 🧑🏾‍🍳 🧑🏿‍🍳 🧑‍🍳 | 0–99                         |
| **CHAMPION_KNIGHT**      | ⚔️                                                          | 0–99                         |
| **CASTLE_GUARD**         | 🗡️                                                          | 0–999                        |
| **TOWNSFOLK**            | 👨🏻‍💼 👨🏼‍💼 👨🏽‍💼 👨🏾‍💼 👨🏿‍💼 👨‍💼 👩🏻‍💼 👩🏼‍💼 👩🏽‍💼 👩🏾‍💼 👩🏿‍💼 👩‍💼 🧑🏻‍💼 🧑🏼‍💼 🧑🏽‍💼 🧑🏾‍💼 🧑🏿‍💼 🧑‍💼 | 0–999                        |
| **VILLAGER**             | 👨🏻‍🌾 👨🏼‍🌾 👨🏽‍🌾 👨🏾‍🌾 👨🏿‍🌾 👨‍🌾 👩🏻‍🌾 👩🏼‍🌾 👩🏽‍🌾 👩🏾‍🌾 👩🏿‍🌾 👩‍🌾 🧑🏻‍🌾 🧑🏼‍🌾 🧑🏽‍🌾 🧑🏾‍🌾 🧑🏿‍🌾 🧑‍🌾 | 0–9999                       |
| **JESTER**               | 🤹🏻 🤹🏼 🤹🏽 🤹🏾 🤹🏿 🤹                                          | 0–99                         |
| **FLOWER**               | 🌸                                                           | 0–9999, walkable             |
| **UNICORN**              | 🦄                                                           | 0–1                          |
| **WALL**                 | 🧱                                                           | non-walkable                 |
| **ENTRANCE**             | 🏰                                                           | walkable (like floor)        |

> [!NOTE]
> All emojis are widely available across fonts, parse cleanly in UTF-8, and we are able to increase representativeness!

---

## 📐 **Geometry -> Graph**

Let V be all person/object tiles (every emoji above except spaces, tabular, newline or end-of-file characters).
Let d(u,v) be the **Manhattan shortest-path distance** on the map, where any person/object (except **FLOWER** and **ENTRANCE**), newline/end-of-file characters and any non-emoji character are obstacles and everything else (**FLOWER**, **ENTRANCE**, spaces, tabulation) is traversable.

#### Edge construction uses the radius R and three principles:

1. Nearest rule (baseline):
Each node u connects to all nodes v that achieve the minimum finite distance from u (ties allowed).

2. Radius augmentation (optional by dataset):
If the dataset wants “local density,” it may specify:
- “All person-or-objects <= R” -> then also connect u to every v with d(u,v) <= R.
If unspecified, only the Nearest rule applies (baseline).

3. Unicorn exception:
If a **UNICORN** exists, it connects to all elements (walls, entrance, people/objects).
(By default, only people/objects are matchable; see next section. Walls/entrance are not matchable, but the **UNICORN** can still “connect” for distance semantics or custom rule variants.).

---

## 📜 **Rules — Grammar & Semantics**

#### Always present:

- "JESTER DANCES WITH ALL": For every JESTER node j and any matchable node x, add edge (j, x) if reachable.
- "FLOWER ONLY DANCES WITH JESTER": Remove all FLOWER–(non-JESTER) edges; keep only FLOWER–JESTER edges if reachable.
- "UNICORN CONNECTS TO ALL AND DANCES WITH ANY": Ensure UNICORN has edges to every tile (including 🧱, 🏰, and everyone).
- In matching, only people/objects participate.

#### Negative constraints (zero or more, any order):

<ROLE_A> DOES NOT DANCE WITH <ROLE_B>

- Case-insensitive, spaces and underscores allowed in role names.
- Symmetric removal: remove all edges between any instance of ROLE_A and any instance of ROLE_B.

---

## 🎯 **Objective & Output**

For each dataset X (e.g., andorra.txt), produce a single integer:
- "X<TAB>INTEGER": where INTEGER = size of the maximum matching (number of vertices covered) in the final graph.
- In outputing multiple datasets at once, print one line per dataset:

```
amman	31
andalusia	415
angkor	88
ankara	1045
```

> [!NOTE]
> We count individuals (vertices matched), not pairs. (Equivalently, 2 * |matching|.)

---

## ✅ **Valid Solutions**
- Any algorithm that returns the **maximum** number possible of people dancing, given all the settings established above
- Heuristics/approximations are allowed for exploration, but the leaderboard (later) will privilege **exact results**.
- Implementations may be in any programming language.

---

## 🧪 **Minimal Example (toy)**

```
R = 3
🧱🧱🧱🧱🧱🧱🧱
🧱	🤴		👸🧱
🧱		🤹	  🧱
🧱		🛡️	  🧱
🧱🧱🧱🧱🧱🧱🧱
JESTER DANCES WITH ALL
FLOWER ONLY DANCES WITH JESTER
UNICORN CONNECTS TO ALL AND DANCES WITH ANY
KING DOES NOT DANCE WITH QUEEN
```

---

## 🧭 **Contributing Datasets**
- Please read CONSTRIBUTING.md
- Keep castle maps readable; ensure at least one line contains a 🧱 and that the required elements exist.
- Always include the three mandatory rules at the top of the rule block. And ensure that it starts exactly after the last (bottom-most) wall emoji (🧱).
- Validate with tools/validate_dataset.py.

---

## 📜 **License**

MIT (Standard): Mainly uses are teaching, forks, student/programmer submissions and fun!

