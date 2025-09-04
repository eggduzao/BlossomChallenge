# -*- coding: utf-8 -*-
"""
Castle-to-Matching graph builder for Blossom (single file).

- Input format:
  <map rows of UTF-8 text with 🧱 walls (and 🏰 optional), people as emojis>
  <last wall row>
  <rules... one per line>
    JESTER DANCES WITH ALL
    KING DOES NOT DANCE WITH QUEEN
    QUEEN DOES NOT DANCE WITH PRINCESS
    ...

- Graph construction:
  1) Parse grid; collect all PERSON tiles (any emoji we recognize, or any non-wall printable char).
  2) Compute 4-neighbor BFS shortest-path distances between all pairs (walls block).
  3) For each person i, find min_j dist(i,j) and connect i↔j if dist(i,j) == min_i (ties allowed, symmetricized).
  4) Apply rules:
     - "JESTER DANCES WITH ALL": connect every JESTER to all others (unless no path).
     - "<ROLE_A> DOES NOT DANCE WITH <ROLE_B>": remove edges between all such role pairs.
  5) Emit adjacency matrix (0/1), node list, roles, positions.

Author: your Honeybun 😘
"""

from collections import deque, defaultdict
import re
import sys

# ---------------------------
# Configurable Lexicon
# ---------------------------

WALL_EMOJIS = {"🧱", "#"}
ENTRANCE_EMOJIS = {"🏰"}  # treated as floor, not a person

# Canonical roles we’ll use in rules
CANON_ROLES = {
    "KING", "QUEEN", "PRINCE", "PRINCESS",
    "CHIEF", "MAID", "COUNSELOR",
    "ELITE", "KNIGHT",
    "BOURGEOISIE", "PROLETARIAT",
    "JESTER"
}

# Emoji → fixed role, or “family” with quotas/suffix roles
# For ambiguous royals, we assign the first to KING/QUEEN, rest to PRINCE/PRINCESS.
# Extend / override as you like.
DEFAULT_EMOJI_ROLE_MAP = {
    # Royals (shared emojis)
    "🤴": ("ROYAL_MALE_FAMILY",),   # KING (first), then PRINCE
    "👸": ("ROYAL_FEMALE_FAMILY",), # QUEEN (first), then PRINCESS

    # Distinct roles
    "🛡️": "CHIEF",            # King's Army Knight's Chief Commander
    "👩‍🍳": "MAID",           # Queen's maid
    "👨‍🎓": "COUNSELOR",      # King's counselor
    "🤹": "JESTER",           # any number
    "⚔️": "ELITE",            # Elite knight (you can also map other knight emoji)
    "🧑‍🌾": "PROLETARIAT",
    "🎩": "BOURGEOISIE",      # bourgeois vibe
    # Add more if you plan to use other symbols:
    "🗡️": "KNIGHT",           # generic knight
    "🧝‍♀️": "ELITE",         # if you used elves as elite knights in demos
}

# Quotas for ambiguous families
ROYAL_QUOTAS = {
    "KING": 1,     # first 🤴
    "QUEEN": 1,    # first 👸
}

# ---------------------------
# Core builder
# ---------------------------

class AdjacencyMatrix:
    def __init__(self, matrix, nodes, roles, positions, index_by_id):
        """
        matrix: NxN list of 0/1 ints
        nodes:  list of display ids (e.g., '🤴#1', '👸#1', '⚔️#3')
        roles:  list of canonical role strings (KING, PRINCE, ...)
        positions: list of (row, col) integers
        index_by_id: dict from node id -> index
        """
        self.matrix = matrix
        self.nodes = nodes
        self.roles = roles
        self.positions = positions
        self.index_by_id = index_by_id

    def to_edge_list(self):
        edges = []
        n = len(self.matrix)
        for i in range(n):
            for j in range(i+1, n):
                if self.matrix[i][j]:
                    edges.append((i, j))
        return edges

class CastleGraphBuilder:
    RULE_JESTER_ALL = re.compile(r"^\s*JESTER\s+DANCES\s+WITH\s+ALL\s*$", re.I)
    RULE_NEG = re.compile(r"^\s*([A-Z]+)\s+DOES\s+NOT\s+DANCE\s+WITH\s+([A-Z]+)\s*$", re.I)

    def __init__(self,
                 wall_emojis=None,
                 entrance_emojis=None,
                 emoji_role_map=None,
                 royal_quotas=None):
        self.wall_emojis = set(wall_emojis or WALL_EMOJIS)
        self.entrance_emojis = set(entrance_emojis or ENTRANCE_EMOJIS)
        self.emoji_role_map = dict(DEFAULT_EMOJI_ROLE_MAP)
        if emoji_role_map:
            self.emoji_role_map.update(emoji_role_map)
        self.royal_quotas = dict(ROYAL_QUOTAS)
        if royal_quotas:
            self.royal_quotas.update(royal_quotas)

    # ---------- parsing ----------

    def parse_text(self, text):
        """
        Split into map_lines and rule_lines.
        We assume rules start immediately AFTER the last line that contains at least one wall emoji.
        """
        lines = [ln.rstrip("\n") for ln in text.splitlines()]
        last_wall_idx = -1
        for i, ln in enumerate(lines):
            if any(w in ln for w in self.wall_emojis):
                last_wall_idx = i
        if last_wall_idx == -1:
            raise ValueError("No wall line found: ensure your map has 🧱 rows.")

        map_lines = lines[:last_wall_idx+1]
        rule_lines = [ln for ln in lines[last_wall_idx+1:] if ln.strip()]

        # Normalize map to rectangular grid (right-pad with spaces)
        width = max(len(ln) for ln in map_lines) if map_lines else 0
        grid = [ln.ljust(width) for ln in map_lines]

        return grid, rule_lines

    # ---------- role assignment ----------

    def assign_roles(self, grid):
        """
        Scan grid, collect persons with (row, col), emoji, assigned role, and stable node ids.
        Handle royal quotas (KING/QUEEN first, then PRINCE/PRINCESS).
        """
        persons = []  # list of dicts: {id, emoji, role, row, col}
        counters = defaultdict(int)
        king_left = self.royal_quotas.get("KING", 0)
        queen_left = self.royal_quotas.get("QUEEN", 0)

        H, W = len(grid), (len(grid[0]) if grid else 0)

        # Iterate by grapheme cluster is hard; we rely on codepoints here.
        # Practical approach: treat any non-space, non-wall, non-entrance char that’s in emoji_role_map
        # as a person tile. (If you want to accept ANY non-wall glyph as person, add a fallback below.)
        for r in range(H):
            row = grid[r]
            c = 0
            while c < len(row):
                ch = row[c]
                # Some emojis are multi-codepoint; we try the longest matches in the map
                # Sort keys by length desc to catch multi-char emojis first
                matched = None
                for emj in sorted(self.emoji_role_map.keys(), key=len, reverse=True):
                    if row.startswith(emj, c):
                        matched = emj
                        break

                tile = None
                if matched:
                    tile = matched
                    advance = len(matched)
                else:
                    tile = ch
                    advance = 1

                if tile in self.wall_emojis or tile in self.entrance_emojis:
                    c += advance
                    continue

                role = None
                if tile in self.emoji_role_map:
                    spec = self.emoji_role_map[tile]
                    if isinstance(spec, tuple) and spec and spec[0] == "ROYAL_MALE_FAMILY":
                        if king_left > 0:
                            role = "KING"; king_left -= 1
                        else:
                            role = "PRINCE"
                    elif isinstance(spec, tuple) and spec and spec[0] == "ROYAL_FEMALE_FAMILY":
                        if queen_left > 0:
                            role = "QUEEN"; queen_left -= 1
                        else:
                            role = "PRINCESS"
                    else:
                        role = spec
                else:
                    # Fallback: treat unknown non-wall printable as generic KNIGHT
                    if tile.strip():
                        role = "KNIGHT"

                if role:
                    counters[(tile, role)] += 1
                    node_id = f"{tile}#{counters[(tile, role)]}"
                    persons.append({
                        "id": node_id,
                        "emoji": tile,
                        "role": role if role in CANON_ROLES else role.upper(),
                        "row": r,
                        "col": c
                    })

                c += advance

        return persons, (H, W)

    # ---------- grid BFS distances ----------

    def _neighbors(self, r, c, H, W):
        if r > 0:       yield r-1, c
        if r+1 < H:     yield r+1, c
        if c > 0:       yield r, c-1
        if c+1 < W:     yield r, c+1

    def _passable(self, ch):
        return (ch not in self.wall_emojis)

    def all_pairs_shortest_paths(self, grid, persons):
        """
        BFS from each person tile to get shortest 4-neighbor path lengths (Manhattan-with-walls).
        We allow passing through any non-wall tile (including other persons and 🏰).
        """
        H, W = len(grid), (len(grid[0]) if grid else 0)
        # Precompute passability grid
        passable = [[self._passable(grid[r][c]) for c in range(W)] for r in range(H)]

        # Map from (r,c) to person index
        pos_to_idx = {(p["row"], p["col"]): i for i, p in enumerate(persons)}
        N = len(persons)
        dist = [[float("inf")] * N for _ in range(N)]

        for i, p in enumerate(persons):
            sr, sc = p["row"], p["col"]
            dgrid = [[-1]*W for _ in range(H)]
            q = deque()
            dgrid[sr][sc] = 0
            q.append((sr, sc))
            # BFS
            while q:
                r, c = q.popleft()
                for nr, nc in self._neighbors(r, c, H, W):
                    if passable[nr][nc] and dgrid[nr][nc] == -1:
                        dgrid[nr][nc] = dgrid[r][c] + 1
                        q.append((nr, nc))
            # Extract distances to other persons
            for j, pj in enumerate(persons):
                dr = dgrid[pj["row"]][pj["col"]]
                if dr >= 0:
                    dist[i][j] = dr

        # Diagonal distance can be 0 (self); the user noted "diagonal is 2" earlier meaning
        # L1 distance of diagonals, but for nodes we only care pairwise distances; self stays inf/0.
        return dist

    # ---------- nearest-neighbor graph ----------

    def connect_nearest(self, dist):
        """
        For each node, connect to all nodes at its minimum positive finite distance.
        Then symmetrize (i↔j if either direction connected).
        """
        N = len(dist)
        adj = [[0]*N for _ in range(N)]
        # Directed nearest
        for i in range(N):
            min_d = float("inf")
            for j in range(N):
                if i == j: continue
                if dist[i][j] < min_d:
                    min_d = dist[i][j]
            if min_d == float("inf"):  # isolated
                continue
            for j in range(N):
                if i != j and dist[i][j] == min_d:
                    adj[i][j] = 1
        # Symmetrize
        for i in range(N):
            for j in range(i+1, N):
                if adj[i][j] or adj[j][i]:
                    adj[i][j] = adj[j][i] = 1
        return adj

    # ---------- rule parsing & application ----------

    def parse_rules(self, rule_lines):
        """
        Returns:
          jester_all: bool
          neg_pairs: set of (ROLE_A, ROLE_B) with A<=B lexicographically for symmetry
        """
        jester_all = False
        neg_pairs = set()
        for ln in rule_lines:
            if self.RULE_JESTER_ALL.match(ln):
                jester_all = True
                continue
            m = self.RULE_NEG.match(ln)
            if m:
                a, b = m.group(1).upper(), m.group(2).upper()
                if a not in CANON_ROLES or b not in CANON_ROLES:
                    # Ignore unknown roles rather than failing
                    continue
                key = tuple(sorted((a, b)))
                neg_pairs.add(key)
        return jester_all, neg_pairs

    def apply_rules(self, adj, persons, dist, jester_all, neg_pairs):
        """
        - If jester_all: connect every JESTER to every other node (only if reachable).
        - Remove edges matching neg role pairs (symmetric).
        """
        N = len(adj)

        # Jester connects to all (but keep it logical: only if a finite path exists)
        if jester_all:
            j_idxs = [i for i, p in enumerate(persons) if p["role"] == "JESTER"]
            for i in j_idxs:
                for j in range(N):
                    if i == j: continue
                    if dist[i][j] < float("inf"):
                        adj[i][j] = adj[j][i] = 1

        # Negative role pruning
        role_to_indices = defaultdict(list)
        for i, p in enumerate(persons):
            role_to_indices[p["role"]].append(i)

        for (ra, rb) in neg_pairs:
            for i in role_to_indices.get(ra, []):
                for j in role_to_indices.get(rb, []):
                    adj[i][j] = adj[j][i] = 0

        return adj

    # ---------- pipeline ----------

    def build(self, text):
        grid, rule_lines = self.parse_text(text)
        persons, (H, W) = self.assign_roles(grid)
        if not persons:
            raise ValueError("No persons detected on the map. Place some emojis!")

        dist = self.all_pairs_shortest_paths(grid, persons)
        adj = self.connect_nearest(dist)
        jester_all, neg_pairs = self.parse_rules(rule_lines)
        adj = self.apply_rules(adj, persons, dist, jester_all, neg_pairs)

        # finalize
        nodes = [p["id"] for p in persons]
        roles = [p["role"] for p in persons]
        positions = [(p["row"], p["col"]) for p in persons]
        idx = {p["id"]: i for i, p in enumerate(persons)}
        return AdjacencyMatrix(adj, nodes, roles, positions, idx)

                                                                  



# ---------------------------
# Minimal CLI demo
# ---------------------------

def _demo():
    sample = """\
🧱🧱🧱🧱🧱🧱
🧱 🤴 👸   🧱
🧱   🤹    🧱
🧱  🛡️     🧱
🧱🧱🧱🧱🧱🧱
JESTER DANCES WITH ALL
KING DOES NOT DANCE WITH QUEEN
"""
    builder = CastleGraphBuilder()
    G = builder.build(sample)
    print("Nodes:", list(zip(G.nodes, G.roles, G.positions)))
    print("Adjacency:")
    for row in G.matrix:
        print(" ".join(map(str, row)))
    print("Edges:", G.to_edge_list())

if __name__ == "__main__":
    if sys.stdin.isatty():
        _demo()
    else:
        text = sys.stdin.read()
        builder = CastleGraphBuilder()
        G = builder.build(text)
        print("NODES")
        for i, (nid, role, pos) in enumerate(zip(G.nodes, G.roles, G.positions)):
            print(f"{i}\t{nid}\t{role}\t{pos}")
        print("MATRIX")
        for row in G.matrix:
            print(",".join(map(str, row)))