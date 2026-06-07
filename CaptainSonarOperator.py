import marimo

__generated_with = "0.23.9"
app = marimo.App(width="full")

with app.setup(hide_code=True):
    import marimo as mo
    import numpy as np
    import pandas as pd
    import altair as alt
    import anywidget
    import traitlets


@app.class_definition(hide_code=True)
class MapEditorWidget(anywidget.AnyWidget):
    _esm = """
    function render({ model, el }) {
        const GRID = 15;
        const CELL = 30;
        const GAP  = 2;

        let painting = false;
        let paintVal = 1;

        function cellColor(v) { return v ? "#1e293b" : "#bfdbfe"; }
        function cellBorder(v) { return v ? "#475569" : "#93c5fd"; }

        function toggleCell(idx) {
            const flat = model.get("islands_flat").slice();
            flat[idx] = paintVal;
            model.set("islands_flat", flat);
            model.save_changes();
        }

        function draw() {
            const islands = model.get("islands_flat");
            el.innerHTML = "";

            const wrap = document.createElement("div");
            wrap.style.cssText = [
                "display:inline-block",
                "background:#0f172a",
                "padding:10px",
                "border-radius:10px",
                "user-select:none",
            ].join(";");

            // Column headers
            const hdr = document.createElement("div");
            hdr.style.cssText = `display:flex;gap:${GAP}px;margin-left:${CELL+GAP}px;margin-bottom:${GAP}px;`;
            for (let c = 0; c < GRID; c++) {
                const lbl = document.createElement("div");
                lbl.style.cssText = `width:${CELL}px;text-align:center;font-size:10px;color:#64748b;font-family:monospace;`;
                lbl.textContent = c + 1;
                hdr.appendChild(lbl);
            }
            wrap.appendChild(hdr);

            for (let r = 0; r < GRID; r++) {
                const rowDiv = document.createElement("div");
                rowDiv.style.cssText = `display:flex;gap:${GAP}px;margin-bottom:${GAP}px;`;

                // Row label
                const rlbl = document.createElement("div");
                rlbl.style.cssText = `width:${CELL}px;text-align:right;padding-right:4px;font-size:10px;color:#64748b;font-family:monospace;line-height:${CELL}px;`;
                rlbl.textContent = r + 1;
                rowDiv.appendChild(rlbl);

                for (let c = 0; c < GRID; c++) {
                    const idx = r * GRID + c;
                    const v   = islands[idx];

                    // Sector boundary — thicker gap every 5 cells
                    const cell = document.createElement("div");
                    const leftBorder  = (c > 0 && c % 5 === 0) ? "border-left:3px solid #f59e0b;" : "";
                    const topBorder   = (r > 0 && r % 5 === 0) ? "border-top:3px solid #f59e0b;"  : "";
                    cell.style.cssText = [
                        `width:${CELL}px`, `height:${CELL}px`,
                        `background:${cellColor(v)}`,
                        `border:1px solid ${cellBorder(v)}`,
                        "border-radius:3px",
                        "cursor:pointer",
                        "transition:background .08s",
                        leftBorder, topBorder,
                    ].join(";");

                    cell.addEventListener("mousedown", (e) => {
                        e.preventDefault();
                        painting = true;
                        paintVal = v ? 0 : 1;
                        toggleCell(idx);
                    });
                    cell.addEventListener("mouseenter", () => {
                        if (painting) toggleCell(idx);
                    });
                    cell.addEventListener("mouseover", () => {
                        const cur = model.get("islands_flat")[idx];
                        cell.style.background = cur
                            ? "#334155"
                            : "#93c5fd";
                    });
                    cell.addEventListener("mouseout", () => {
                        const cur = model.get("islands_flat")[idx];
                        cell.style.background = cellColor(cur);
                    });

                    rowDiv.appendChild(cell);
                }
                wrap.appendChild(rowDiv);
            }

            document.addEventListener("mouseup", () => { painting = false; }, { once: false });
            el.appendChild(wrap);
        }

        model.on("change:islands_flat", draw);
        draw();
    }
    export default { render };
    """

    islands_flat = traitlets.List([0] * 225).tag(sync=True)


@app.cell(hide_code=True)
def _map_editor():
    _DEFAULT = [
        (1, 3), (3, 1),
        (0, 6), (2, 8), (4, 7),
        (1, 12), (3, 11),
        (6, 2), (8, 4),
        (5, 7), (7, 5), (9, 8),
        (6, 13), (8, 11),
        (11, 1), (13, 3),
        (10, 6), (12, 8), (14, 5),
        (11, 12), (13, 10),
    ]
    _flat = [0] * 225
    for _r, _c in _DEFAULT:
        _flat[_r * 15 + _c] = 1

    map_editor = mo.ui.anywidget(MapEditorWidget(islands_flat=_flat))

    mo.vstack([
        mo.md("## 🗺️ Map Editor\nClick or drag to toggle islands (dark = island, blue = water). Amber lines are sector boundaries."),
        map_editor,
    ])
    return (map_editor,)


@app.cell(hide_code=True)
def _constants(map_editor):
    GRID_SIZE = 15

    SECTORS = {
        1: (0, 0),  2: (0, 5),  3: (0, 10),
        4: (5, 0),  5: (5, 5),  6: (5, 10),
        7: (10, 0), 8: (10, 5), 9: (10, 10),
    }

    _flat = map_editor.value["islands_flat"]
    ISLANDS = frozenset(
        (r, c)
        for r in range(GRID_SIZE)
        for c in range(GRID_SIZE)
        if _flat[r * GRID_SIZE + c]
    )

    DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
    CHARGES = {"torpedo": 3, "mine": 3, "drone": 4, "sonar": 4, "silence": 6}
    return CHARGES, GRID_SIZE, ISLANDS, SECTORS


@app.cell(hide_code=True)
def _state():
    get_moves,   set_moves   = mo.state([])
    get_archive, set_archive = mo.state([])
    return get_archive, get_moves, set_archive, set_moves


@app.cell(hide_code=True)
def _models():
    from dataclasses import dataclass
    from typing import Optional

    @dataclass(frozen=True)
    class Event:
        type: str
        dir: Optional[str] = None
        name: Optional[str] = None
        target_r: Optional[int] = None
        target_c: Optional[int] = None
        sector: Optional[int] = None
        result: Optional[bool] = None

    @dataclass(frozen=True)
    class PathBranch:
        fork_id: int
        generation: int
        rx: int
        ry: int
        visited_relative: frozenset
        valid_starts: frozenset

    @dataclass(frozen=True)
    class MapContext:
        grid_size: int
        islands: frozenset
        sectors: dict

    return Event, MapContext, PathBranch


@app.cell(hide_code=True)
def _filters(MapContext):
    def filter_valid_starts(starts: frozenset, rx: int, ry: int, ctx: MapContext) -> frozenset:
        """Keep starting positions where the relative offset lands on a valid water cell."""
        gs = ctx.grid_size
        return frozenset(
            (r0, c0) for r0, c0 in starts
            if 0 <= r0 - ry < gs
            and 0 <= c0 + rx < gs
            and (r0 - ry, c0 + rx) not in ctx.islands
        )

    def filter_torpedo_range(starts: frozenset, rx: int, ry: int,
                              target_r: int, target_c: int) -> frozenset:
        """Keep starting positions where current absolute position is within Manhattan 4."""
        return frozenset(
            (r0, c0) for r0, c0 in starts
            if abs((r0 - ry) - target_r) + abs((c0 + rx) - target_c) <= 4
        )

    def carry_forward(branches: list, sector, ctx: MapContext) -> frozenset:
        """Union branch valid_starts to absolute positions; apply sector as a soft mask."""
        abs_pos = frozenset(
            (r0 - b.ry, c0 + b.rx)
            for b in branches
            for r0, c0 in b.valid_starts
        )
        if sector is not None and sector in ctx.sectors:
            sr, sc = ctx.sectors[sector]
            sector_cells = frozenset(
                (r, c) for r in range(sr, sr + 5) for c in range(sc, sc + 5)
                if (r, c) not in ctx.islands
            )
            filtered = abs_pos & sector_cells
            if filtered:
                abs_pos = filtered
        return abs_pos

    def filter_row_hit(starts: frozenset, rx: int, ry: int, row: int, hit: bool) -> frozenset:
        """Keep positions where absolute row matches hit (True=yes, False=no). Soft mask."""
        result = frozenset((r0, c0) for r0, c0 in starts if ((r0 - ry) == row) == hit)
        return result if result else starts

    def filter_col_hit(starts: frozenset, rx: int, ry: int, col: int, hit: bool) -> frozenset:
        """Keep positions where absolute col matches hit. Soft mask."""
        result = frozenset((r0, c0) for r0, c0 in starts if ((c0 + rx) == col) == hit)
        return result if result else starts

    def filter_sector_hit(starts: frozenset, rx: int, ry: int,
                           sector: int, ctx: MapContext, hit: bool) -> frozenset:
        """Keep positions where absolute cell is inside sector, matching hit. Soft mask."""
        if sector not in ctx.sectors:
            return starts
        sr, sc = ctx.sectors[sector]
        def _in(r0, c0):
            r, c = r0 - ry, c0 + rx
            return sr <= r < sr + 5 and sc <= c < sc + 5
        result = frozenset((r0, c0) for r0, c0 in starts if _in(r0, c0) == hit)
        return result if result else starts

    return carry_forward, filter_torpedo_range, filter_valid_starts


@app.cell(hide_code=True)
def _reducer(
    MapContext,
    PathBranch,
    filter_torpedo_range,
    filter_valid_starts,
):
    _VV   = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
    _ICON = {"torpedo": "🎯", "mine": "💣", "sonar": "📡", "drone": "🚁", "silence": "🤫"}

    def process_event(branches: list, event, ctx: MapContext, fid: list, step: int):
        """Reduce one event over the current branch list.

        Returns (new_branches, node_records, edge_records, mine_dict, path_error).
        fid    — mutable [int] fork-ID counter, shared across an entire life.
        mine_dict — {(abs_r, abs_c): weight}; non-empty only for mine events.
        """
        nodes, edges, mine_dict, err = [], [], {}, None

        match event.type:
            case "move":
                dx, dy = _VV[event.dir]
                new_branches = []
                for b in branches:
                    nrx, nry = b.rx + dx, b.ry + dy
                    if (nrx, nry) in b.visited_relative:
                        if b.fork_id == 0:
                            err = f"Step {step} ({event.dir}): main path crosses itself. Undo."
                        continue
                    nstarts = filter_valid_starts(b.valid_starts, nrx, nry, ctx)
                    if not nstarts:
                        if b.fork_id == 0:
                            err = f"Step {step} ({event.dir}): no valid map positions remain. Undo."
                        continue
                    edges.append({"x1": b.rx, "y1": b.ry, "x2": nrx, "y2": nry,
                                  "fork_id": str(b.fork_id)})
                    nodes.append({"x": nrx, "y": nry, "step": step,
                                  "fork_id": str(b.fork_id), "generation": str(b.generation), "ability": ""})
                    new_branches.append(PathBranch(
                        b.fork_id, b.generation, nrx, nry,
                        b.visited_relative | {(nrx, nry)}, nstarts,
                    ))
                branches = new_branches

            case "fire":
                match event.name:
                    case "silence":
                        new_branches = []
                        for b in branches:
                            fid[0] += 1; sf = fid[0]
                            nodes.append({"x": b.rx, "y": b.ry, "step": step,
                                          "fork_id": str(sf), "generation": str(b.generation + 1), "ability": "🤫"})
                            new_branches.append(PathBranch(sf, b.generation + 1, b.rx, b.ry, b.visited_relative, b.valid_starts))
                            for _sd, (sdx, sdy) in _VV.items():
                                for dist in range(1, 5):
                                    path = [(b.rx + sdx * d, b.ry + sdy * d) for d in range(1, dist + 1)]
                                    if any(cell in b.visited_relative for cell in path):
                                        break
                                    nrx, nry = path[-1]
                                    nstarts = frozenset(
                                        (r0, c0) for r0, c0 in b.valid_starts
                                        if all(
                                            0 <= r0 - pry < ctx.grid_size
                                            and 0 <= c0 + prx < ctx.grid_size
                                            and (r0 - pry, c0 + prx) not in ctx.islands
                                            for prx, pry in path
                                        )
                                    )
                                    if not nstarts:
                                        break
                                    fid[0] += 1; sf = fid[0]
                                    edges.append({"x1": b.rx, "y1": b.ry, "x2": nrx, "y2": nry, "fork_id": str(sf)})
                                    nodes.append({"x": nrx, "y": nry, "step": step,
                                                  "fork_id": str(sf), "generation": str(b.generation + 1), "ability": "🤫"})
                                    new_branches.append(PathBranch(
                                        sf, b.generation + 1, nrx, nry,
                                        b.visited_relative | set(path), nstarts,
                                    ))
                        branches = new_branches

                    case "torpedo":
                        new_branches = []
                        for b in branches:
                            if event.target_r is not None and event.target_c is not None:
                                nstarts = filter_torpedo_range(b.valid_starts, b.rx, b.ry,
                                                               event.target_r, event.target_c)
                                new_branches.append(PathBranch(
                                    b.fork_id, b.generation, b.rx, b.ry,
                                    b.visited_relative, nstarts if nstarts else b.valid_starts,
                                ))
                            else:
                                new_branches.append(b)
                            nodes.append({"x": b.rx, "y": b.ry, "step": step,
                                          "fork_id": str(b.fork_id), "generation": str(b.generation),
                                          "ability": _ICON["torpedo"]})
                        branches = new_branches

                    case "mine":
                        for b in branches:
                            for r0, c0 in b.valid_starts:
                                k = (r0 - b.ry, c0 + b.rx)
                                mine_dict[k] = mine_dict.get(k, 0) + 1.0
                            nodes.append({"x": b.rx, "y": b.ry, "step": step,
                                          "fork_id": str(b.fork_id), "generation": str(b.generation),
                                          "ability": _ICON["mine"]})

                    case _:
                        icon = _ICON.get(event.name, event.name.capitalize())
                        for b in branches:
                            nodes.append({"x": b.rx, "y": b.ry, "step": step,
                                          "fork_id": str(b.fork_id), "generation": str(b.generation),
                                          "ability": icon})

            case "feedback":
                new_branches = []
                for b in branches:
                    if event.name == "sonar":
                        icon = _ICON["sonar"]
                        if event.target_r is not None:
                            raw = frozenset(
                                (r0, c0) for r0, c0 in b.valid_starts
                                if ((r0 - b.ry) == event.target_r) == event.result
                            )
                            label = f"Sonar row {event.target_r + 1}"
                        elif event.target_c is not None:
                            raw = frozenset(
                                (r0, c0) for r0, c0 in b.valid_starts
                                if ((c0 + b.rx) == event.target_c) == event.result
                            )
                            label = f"Sonar col {event.target_c + 1}"
                        else:
                            raw, label = b.valid_starts, ""
                    else:  # drone
                        icon = _ICON["drone"]
                        if event.sector is not None and event.sector in ctx.sectors:
                            sr, sc = ctx.sectors[event.sector]
                            raw = frozenset(
                                (r0, c0) for r0, c0 in b.valid_starts
                                if (sr <= r0 - b.ry < sr + 5 and sc <= c0 + b.rx < sc + 5) == event.result
                            )
                            label = f"Drone sector {event.sector}"
                        else:
                            raw, label = b.valid_starts, ""
                    if raw:
                        nstarts = raw
                    else:
                        nstarts = b.valid_starts
                        if label and not err:
                            hit_str = "yes" if event.result else "no"
                            err = f"Step {step}: {label} = {hit_str} contradicts known positions — constraint ignored."
                    nodes.append({"x": b.rx, "y": b.ry, "step": step,
                                  "fork_id": str(b.fork_id), "generation": str(b.generation), "ability": icon})
                    new_branches.append(PathBranch(b.fork_id, b.generation, b.rx, b.ry, b.visited_relative, nstarts))
                branches = new_branches

        return branches, nodes, edges, mine_dict, err

    return (process_event,)


@app.cell(hide_code=True)
def _projections(PathBranch):
    def branches_to_pos_heatmap(branches: list, grid_size: int):
        pos_weights = {}
        for b in branches:
            for r0, c0 in b.valid_starts:
                k = (r0 - b.ry, c0 + b.rx)
                pos_weights[k] = pos_weights.get(k, 0) + 1.0
        hm = np.zeros((grid_size, grid_size))
        total = sum(pos_weights.values())
        if total > 0:
            for (r, c), w in pos_weights.items():
                hm[r, c] = w / total
        return hm

    def mine_dict_to_heatmap(mine_raw):
        mx = mine_raw.max()
        return mine_raw / mx if mx > 0 else mine_raw

    def records_to_dataframes(nodes: list, edges: list, branches: list):
        """Apply sole-survivor merge and dead-fork filter; return (nodes_df, edges_df)."""
        if len(branches) == 1 and branches[0].fork_id != 0:
            sole = str(branches[0].fork_id)
            for n in nodes:
                if str(n["fork_id"]) == sole:
                    n["fork_id"] = "0"
            for e in edges:
                if str(e["fork_id"]) == sole:
                    e["fork_id"] = "0"
            b0 = branches[0]
            branches = [PathBranch(0, b0.generation, b0.rx, b0.ry, b0.visited_relative, b0.valid_starts)]

        alive = {str(b.fork_id) for b in branches} | {"0"}
        nf = [n for n in nodes if str(n["fork_id"]) in alive]
        ef = [e for e in edges if str(e["fork_id"]) in alive]
        nodes_df = pd.DataFrame(nf) if nf else pd.DataFrame(columns=["x", "y", "step", "fork_id", "generation", "ability"])
        edges_df = pd.DataFrame(ef) if ef else pd.DataFrame(columns=["x1", "y1", "x2", "y2", "fork_id"])
        return nodes_df, edges_df

    return branches_to_pos_heatmap, mine_dict_to_heatmap, records_to_dataframes


@app.cell(hide_code=True)
def _pipeline(
    Event,
    GRID_SIZE,
    ISLANDS,
    MapContext,
    PathBranch,
    SECTORS,
    branches_to_pos_heatmap,
    carry_forward,
    get_archive,
    get_moves,
    mine_dict_to_heatmap,
    process_event,
    records_to_dataframes,
):
    def _to_event(d: dict) -> Event:
        return Event(
            type=d["type"],
            dir=d.get("dir"),
            name=d.get("name"),
            target_r=d.get("target_r"),
            target_c=d.get("target_c"),
            sector=d.get("sector"),
        )

    _ctx = MapContext(grid_size=GRID_SIZE, islands=ISLANDS, sectors=SECTORS)
    _all_water = frozenset(
        (r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
        if (r, c) not in ISLANDS
    )
    _mine_raw = np.zeros((GRID_SIZE, GRID_SIZE))
    _carried  = _all_water

    # ── Archived lives: carry valid_starts forward across surface events ──────
    for _life in get_archive():
        _evts = [_to_event(d) for d in _life["moves"]]
        _lb   = [PathBranch(0, 0, 0, 0, frozenset([(0, 0)]), _carried)]
        _fid  = [0]
        for _si, _ev in enumerate(_evts, 1):
            _lb, _, _, _mc, _ = process_event(_lb, _ev, _ctx, _fid, _si)
            for (r, c), w in _mc.items():
                _mine_raw[r, c] += w
        if _lb:
            _sec = _evts[-1].sector if _evts and _evts[-1].type == "surface" else None
            _carried = carry_forward(_lb, _sec, _ctx)

    # ── Current life ──────────────────────────────────────────────────────────
    _evts     = [_to_event(d) for d in get_moves()]
    _branches = [PathBranch(0, 0, 0, 0, frozenset([(0, 0)]), _carried)]
    _fid      = [0]
    _nodes    = [{"x": 0, "y": 0, "step": 0, "fork_id": "0", "generation": "0", "ability": ""}]
    _edges    = []
    path_error = None

    for _si, _ev in enumerate(_evts, 1):
        _branches, _nn, _ne, _mc, _err = process_event(_branches, _ev, _ctx, _fid, _si)
        _nodes.extend(_nn)
        _edges.extend(_ne)
        for (r, c), w in _mc.items():
            _mine_raw[r, c] += w
        if _err:
            path_error = _err

    # ── Projections ───────────────────────────────────────────────────────────
    pos_heatmap  = branches_to_pos_heatmap(_branches, GRID_SIZE)
    mine_heatmap = mine_dict_to_heatmap(_mine_raw)
    nodes_df, edges_df = records_to_dataframes(_nodes, _edges, _branches)
    return edges_df, mine_heatmap, nodes_df, path_error, pos_heatmap


@app.cell(hide_code=True)
def _controls():
    mo.md(r"""
    # 🔭 Operator Tracker

    Log each enemy move with **N/S/E/W** and check any ability charged that turn.
    **Surface** archives the current life and resets the heatmap for the next.
    """)
    return


@app.cell(hide_code=True)
def _ui(get_archive, get_moves, set_archive, set_moves):
    # Define number inputs first so closures below can read .value at click time
    torpedo_row    = mo.ui.number(start=1, stop=15, step=1, label="R:")
    torpedo_col    = mo.ui.number(start=1, stop=15, step=1, label="C:")
    surface_sector = mo.ui.number(start=1, stop=9,  step=1, label="Sec:")

    # Sonar feedback (2 row/col hints)
    sonar_type_1 = mo.ui.dropdown(options={"row": "Row", "col": "Col"}, value="row", label="")
    sonar_val_1  = mo.ui.number(start=1, stop=15, step=1, label="")
    sonar_hit_1  = mo.ui.switch(label="Hit?", value=True)
    sonar_type_2 = mo.ui.dropdown(options={"row": "Row", "col": "Col"}, value="col", label="")
    sonar_val_2  = mo.ui.number(start=1, stop=15, step=1, label="")
    sonar_hit_2  = mo.ui.switch(label="Hit?", value=True)

    # Drone feedback (1 sector hint)
    drone_sector = mo.ui.number(start=1, stop=9, step=1, label="Sec:")
    drone_hit    = mo.ui.switch(label="Hit?", value=True)

    def _do_surf(_):
        sec = int(surface_sector.value)
        archived_moves = list(get_moves()) + [{"type": "surface", "sector": sec}]
        set_archive(get_archive() + [{"moves": archived_moves}])
        set_moves([])

    def _do_torpedo(_):
        tr = int(torpedo_row.value) - 1   # 1-based → 0-based
        tc = int(torpedo_col.value) - 1
        set_moves(get_moves() + [{"type": "fire", "name": "torpedo", "target_r": tr, "target_c": tc}])

    def _do_sonar(_):
        evs = []
        for t, v, h in [
            (sonar_type_1.value, int(sonar_val_1.value), bool(sonar_hit_1.value)),
            (sonar_type_2.value, int(sonar_val_2.value), bool(sonar_hit_2.value)),
        ]:
            if t == "row":
                evs.append({"type": "feedback", "name": "sonar", "target_r": v - 1, "result": h})
            else:
                evs.append({"type": "feedback", "name": "sonar", "target_c": v - 1, "result": h})
        set_moves(get_moves() + evs)

    def _do_drone(_):
        set_moves(get_moves() + [{"type": "feedback", "name": "drone",
                                   "sector": int(drone_sector.value), "result": bool(drone_hit.value)}])

    btn_N = mo.ui.button(label="⬆ N", on_click=lambda _: set_moves(get_moves() + [{"type": "move", "dir": "N"}]))
    btn_S = mo.ui.button(label="⬇ S", on_click=lambda _: set_moves(get_moves() + [{"type": "move", "dir": "S"}]))
    btn_E = mo.ui.button(label="➡ E", on_click=lambda _: set_moves(get_moves() + [{"type": "move", "dir": "E"}]))
    btn_W = mo.ui.button(label="⬅ W", on_click=lambda _: set_moves(get_moves() + [{"type": "move", "dir": "W"}]))

    # Ability Buttons
    btn_torpedo = mo.ui.button(label="🎯 Torpedo", kind="danger",  on_click=_do_torpedo)
    btn_mine    = mo.ui.button(label="💣 Mine ",    kind="danger",  on_click=lambda _: set_moves(get_moves() + [{"type": "fire", "name": "mine"}]))
    btn_silence = mo.ui.button(label="🤫 Silence", kind="warn",    on_click=lambda _: set_moves(get_moves() + [{"type": "fire", "name": "silence"}]))
    btn_sonar   = mo.ui.button(label="📡  Sonar ",   kind="neutral", on_click=lambda _: set_moves(get_moves() + [{"type": "fire", "name": "sonar"}]))
    btn_drone   = mo.ui.button(label="🚁  Drone ",   kind="neutral", on_click=lambda _: set_moves(get_moves() + [{"type": "fire", "name": "drone"}]))

    # Action Buttons
    btn_surface  = mo.ui.button(label="🏄 Surface",    kind="warn",    on_click=_do_surf)
    btn_undo     = mo.ui.button(label="↩ Undo",         kind="neutral", on_click=lambda _: set_moves(get_moves()[:-1]) if get_moves() else None)
    btn_reset    = mo.ui.button(label="🔄 Full Reset",  kind="danger",  on_click=lambda _: (set_moves([]), set_archive([])))
    btn_log_sonar = mo.ui.button(label="Log", kind="neutral", on_click=_do_sonar)
    btn_log_drone = mo.ui.button(label="Log", kind="neutral", on_click=_do_drone)

    # Apply styles inline during grouping so the base elements retain their pristine `.value` bindings
    torpedo_group = mo.hstack(
        [
            btn_torpedo, 
            torpedo_col.style(max_width="55px", padding="4px", text_align="center"), 
            torpedo_row.style(max_width="55px", padding="4px", text_align="center")
        ], 
        gap="1", 
        align="center"
    )

    surface_group = mo.vstack(
        [
            btn_surface, 
            surface_sector.style(max_width="55px", padding="4px", text_align="center")
        ], 
        gap="0.2", 
        align="center"
    )

    # Build the Arrow Key D-pad layout
    arrow_keys = mo.vstack(
        [
            mo.hstack([btn_N], justify="center"),
            mo.hstack([btn_W, btn_S, btn_E], gap="0.4 ", justify="center")
        ],
        gap="0.4"
    )

    # Flattened layout for abilities, using the dynamically styled torpedo_group
    ability_groups = mo.hstack(
        [
            torpedo_group, 
            mo.md("&nbsp;&nbsp;**|**&nbsp;&nbsp;"),
            btn_mine,
            mo.md("&nbsp;&nbsp;**|**&nbsp;&nbsp;"),  # Visual divider
            btn_silence,
            mo.md("&nbsp;&nbsp;**|**&nbsp;&nbsp;"),  # Visual divider
            btn_sonar, 
            btn_drone
        ],
        gap="0.5",      
        justify="center",
        align="center"
    )

    sonar_group = mo.hstack(
        [
            mo.md("**📡 Sonar:**"),
            mo.vstack([ 
                sonar_type_1.style(min_width="70px"),
                sonar_val_1.style(max_width="55px", padding="4px", text_align="center"),
                sonar_hit_1,
            ]),
            mo.md("**·**"),
            mo.vstack([
                sonar_type_2.style(min_width="70px"),
                sonar_val_2.style(max_width="55px", padding="4px", text_align="center"),
                sonar_hit_2,
            ]),
            btn_log_sonar
        ],
        gap="0.5",
        align="center",
    )

    drone_group = mo.hstack(
        [
            mo.md("**🚁 Drone:**"),
            mo.vstack([
                drone_sector.style(max_width="55px", padding="4px", text_align="center"),
                drone_hit,
            ]),
            btn_log_drone,
        ],
        gap="0.5",
        align="center",
    )

    # Bottom layout, using the dynamically styled surface_group
    bottom_actions = mo.hstack(
        [surface_group, btn_undo, btn_reset, mo.md("**|**"), sonar_group, mo.md("**|**"), drone_group],
        gap="2",
        justify="center",
        align="center",
    )

    mo.vstack([
        mo.md("**Move** (enemy announces direction):"),
        arrow_keys,
        mo.md("**Ability fired** (replaces or accompanies move):"),
        ability_groups,
        mo.md("---"),
        bottom_actions,
    ], align="center")
    return


@app.cell(hide_code=True)
def _visualise(
    GRID_SIZE,
    ISLANDS,
    SECTORS,
    edges_df,
    mine_heatmap,
    nodes_df,
    path_error,
    pos_heatmap,
    show_blast,
    show_mine,
    show_sub,
):
    # ── Heatmap chart ──────────────────────────────────────────────────────────
    _rows = []
    for _r in range(GRID_SIZE):
        for _c in range(GRID_SIZE):
            _isl = int((_r, _c) in ISLANDS)
            _rows.append({
                "x1": _c, "x2": _c + 1,
                "y1": _r, "y2": _r + 1,
                "cx": _c + 0.5, "cy": _r + 0.5,
                "is_island": _isl,
                "sub_prob":  float(pos_heatmap[_r, _c]) * (1 - _isl),
                "mine_prob": float(mine_heatmap[_r, _c]) * (1 - _isl),
            })
    _df = pd.DataFrame(_rows)

    if show_blast.value:
        _blast = np.zeros((GRID_SIZE, GRID_SIZE))
        for _r2 in range(GRID_SIZE):
            for _c2 in range(GRID_SIZE):
                if mine_heatmap[_r2, _c2] > 0:
                    for _dr in range(-1, 2):
                        for _dc in range(-1, 2):
                            _nr2, _nc2 = _r2 + _dr, _c2 + _dc
                            if 0 <= _nr2 < GRID_SIZE and 0 <= _nc2 < GRID_SIZE:
                                _blast[_nr2, _nc2] = max(_blast[_nr2, _nc2], mine_heatmap[_r2, _c2] * 0.5)
        _bmax = _blast.max()
        if _bmax > 0:
            _blast /= _bmax
        for _i, _row in _df.iterrows():
            _r2, _c2 = int(_row["cy"] - 0.5), int(_row["cx"] - 0.5)
            _df.at[_i, "blast_prob"] = float(_blast[_r2, _c2]) * (1 - _row["is_island"])
    else:
        _df["blast_prob"] = 0.0

    _yscale = alt.Scale(domain=[GRID_SIZE, 0])
    _xscale = alt.Scale(domain=[0, GRID_SIZE])

    def _rect(df, color, opacity_field=None, opacity_val=1, legend_title=None):
        enc = dict(
            x=alt.X("x1:Q", scale=_xscale, axis=None),
            x2="x2:Q",
            y=alt.Y("y2:Q", scale=_yscale, axis=None),
            y2="y1:Q",
        )
        if color is None and opacity_field:
            enc["color"] = alt.Color(
                f"{opacity_field}:Q",
                scale=alt.Scale(scheme="oranges" if "sub" in opacity_field else "reds"),
                legend=alt.Legend(title=legend_title or opacity_field),
            )
            enc["opacity"] = alt.Opacity(
                f"{opacity_field}:Q",
                scale=alt.Scale(range=[0.15, 0.92]),
                legend=None,
            )
            return alt.Chart(df).mark_rect().encode(**enc)
        return alt.Chart(df).mark_rect(color=color, opacity=opacity_val).encode(**enc)

    _water   = _rect(_df[_df["is_island"] == 0], "#dbeafe", opacity_val=1.0)
    _islands = _rect(_df[_df["is_island"] == 1], "#1e293b", opacity_val=1.0)
    _hdiv = (
        alt.Chart(pd.DataFrame({"y": [5.0, 10.0]}))
        .mark_rule(color="#334155", strokeWidth=2.5, strokeDash=[5, 3])
        .encode(y=alt.Y("y:Q", scale=_yscale, axis=None))
    )
    _vdiv = (
        alt.Chart(pd.DataFrame({"x": [5.0, 10.0]}))
        .mark_rule(color="#334155", strokeWidth=2.5, strokeDash=[5, 3])
        .encode(x=alt.X("x:Q", scale=_xscale, axis=None))
    )
    _sec_df = pd.DataFrame([
        {"cx": c0 + 2.5, "cy": r0 + 2.5, "label": str(s)}
        for s, (r0, c0) in SECTORS.items()
    ])
    _sec_labels = (
        alt.Chart(_sec_df)
        .mark_text(fontSize=26, fontWeight="bold", opacity=0.18, color="#0f172a")
        .encode(
            x=alt.X("cx:Q", scale=_xscale, axis=None),
            y=alt.Y("cy:Q", scale=_yscale, axis=None),
            text="label:N",
        )
    )
    _col_lbl = (
        alt.Chart(pd.DataFrame({
            "x": [c + 0.5 for c in range(GRID_SIZE)],
            "label": [str(c + 1) for c in range(GRID_SIZE)],
        }))
        .mark_text(fontSize=7, color="#64748b")
        .encode(x=alt.X("x:Q", scale=_xscale, axis=None), y=alt.value(4), text="label:N")
    )
    _row_lbl = (
        alt.Chart(pd.DataFrame({
            "y": [r + 0.5 for r in range(GRID_SIZE)],
            "label": [str(r + 1) for r in range(GRID_SIZE)],
        }))
        .mark_text(fontSize=7, color="#64748b")
        .encode(x=alt.value(4), y=alt.Y("y:Q", scale=_yscale, axis=None), text="label:N")
    )

    _layers = [_water, _islands]
    if show_sub.value:
        _sub_df = _df[_df["sub_prob"] > 0.001]
        if not _sub_df.empty:
            _layers.append(_rect(_sub_df, None, opacity_field="sub_prob", legend_title="Sub probability"))
    if show_mine.value:
        _mine_df = _df[_df["mine_prob"] > 0.001]
        if not _mine_df.empty:
            _layers.append(_rect(_mine_df, None, opacity_field="mine_prob", legend_title="Mine probability"))
    if show_blast.value:
        _blast_df = _df[_df["blast_prob"] > 0.001]
        if not _blast_df.empty:
            _layers.append(
                alt.Chart(_blast_df).mark_rect(opacity=0.3).encode(
                    x=alt.X("x1:Q", scale=_xscale, axis=None), x2="x2:Q",
                    y=alt.Y("y2:Q", scale=_yscale, axis=None), y2="y1:Q",
                    color=alt.Color("blast_prob:Q",
                                    scale=alt.Scale(scheme="orangeRed"),
                                    legend=alt.Legend(title="Blast radius")),
                )
            )
    _layers += [_hdiv, _vdiv, _sec_labels, _col_lbl, _row_lbl]

    heatmap_chart = (
        alt.layer(*_layers)
        .properties(
            width=450, height=450,
            title=alt.TitleParams("🔭 Enemy Submarine Tracker", fontSize=15, anchor="start"),
        )
        .configure_view(stroke="#334155", strokeWidth=3)
    )

    # ── Path Validator chart ───────────────────────────────────────────────────
    _fork_shapes = ["circle", "square", "diamond", "cross", "triangle-up", "triangle-down", "triangle-right", "triangle-left"]

    _edge_layer = (
        alt.Chart(edges_df)
        .mark_rule(strokeWidth=1.5, opacity=0.55)
        .encode(
            x=alt.X("x1:Q", title="← W  |  E →"),
            y=alt.Y("y1:Q", title="↓ S  |  N ↑"),
            x2="x2:Q",
            y2="y2:Q",
            color=alt.Color("fork_id:N", legend=None),
        )
    )
    _node_layer = (
        alt.Chart(nodes_df)
        .mark_point(filled=True, size=180)
        .encode(
            x=alt.X("x:Q", title="← W  |  E →"),
            y=alt.Y("y:Q", title="↓ S  |  N ↑"),
            color=alt.Color("fork_id:N", legend=None),
            shape=alt.Shape(
                "fork_id:N",
                scale=alt.Scale(range=_fork_shapes),
                legend=None,
            ),
            tooltip=["step:Q", "fork_id:N", "generation:N", "ability:N"],
        )
    )
    _lbl_nodes = nodes_df[nodes_df["ability"] != ""]
    _label_layer = (
        alt.Chart(_lbl_nodes)
        .mark_text(dy=-12, fontSize=11)
        .encode(
            x=alt.X("x:Q"),
            y=alt.Y("y:Q"),
            text=alt.Text("ability:N"),
        )
    )

    path_chart = (
        alt.layer(_edge_layer, _node_layer, _label_layer)
        .properties(
            width=450, height=450,
            title=alt.TitleParams("🧭 Path Validator (Relative Shape)", fontSize=15, anchor="start"),
        )
        .interactive()
    )
    _viz_rows = []
    if path_error:
        _viz_rows.append(mo.callout(mo.md(f"**⚠️ Path error:** {path_error}"), kind="danger"))
    _viz_rows.append(mo.hstack([heatmap_chart, path_chart], justify="start", gap="2 "))
    mo.vstack(_viz_rows, gap="0.75 ")
    return


@app.cell(hide_code=True)
def _layer_toggles():
    show_sub   = mo.ui.switch(label="Sub heatmap",  value=True)
    show_mine  = mo.ui.switch(label="Mine heatmap", value=True)
    show_blast = mo.ui.switch(label="Blast radii",  value=False)

    mo.hstack(
        [mo.md("**Layers:**"), show_sub, show_mine, show_blast],
        gap="1.5 ", align="center",
    )
    return show_blast, show_mine, show_sub


@app.cell(hide_code=True)
def _energy_dashboard(CHARGES, get_archive, get_moves):
    _all_entries = list(get_moves())
    for _life in get_archive():
        _all_entries.extend(_life["moves"])

    # Moves = events that generate 1 energy each (movement + silence both cost a turn)
    _total_moves = sum(
        1 for e in _all_entries
        if e["type"] == "move" or (e["type"] == "fire" and e["name"] == "silence")
    )

    # Each fired ability costs its charge cost from the pool
    _fire_events = [e for e in _all_entries if e["type"] == "fire"]
    _energy_spent = sum(CHARGES[e["name"]] for e in _fire_events)
    _pool = _total_moves - _energy_spent

    # Times each system was fired
    _fired = {ab: sum(1 for e in _fire_events if e["name"] == ab) for ab in CHARGES}

    # Per-system table
    _rows = []
    for ab, cost in CHARGES.items():
        possible = cost <= _pool
        _rows.append({
            "System":    ab.capitalize(),
            "Cost":      cost,
            "Fired":     _fired[ab],
            "Possible?": "⚠️ Yes" if possible else "❌ No",
        })

    # Enumerate all subsets of systems that fit in the  aining pool
    _sys = list(CHARGES.items())
    _combos = []
    for mask in range(1, 1 << len(_sys)):
        combo_cost = sum(_sys[i][1] for i in range(len(_sys)) if mask & (1 << i))
        if combo_cost <= _pool:
            names = " + ".join(_sys[i][0].capitalize() for i in range(len(_sys)) if mask & (1 << i))
            _combos.append((combo_cost, names))
    _combos.sort(key=lambda x: -x[0])
    _combo_lines = "\n".join(f"- **{n}** (costs {c})" for c, n in _combos[:6]) or "*None possible yet*"

    mo.vstack([
        mo.callout(
            mo.md(
                f"**⚡ Energy pool: {_pool}** "
                f"({_total_moves} movement turns − {_energy_spent} spent on abilities)"
            ),
            kind="info" if _pool > 0 else ("warn" if _pool == 0 else "danger"),
        ),
        mo.md("### Per-system threat"),
        mo.ui.table(pd.DataFrame(_rows), selection=None),
        mo.md(f"### Possible ready combinations\n{_combo_lines}"),
    ])
    return


@app.cell(hide_code=True)
def _move_log(get_archive, get_moves):
    _moves   = get_moves()
    _archive = get_archive()
    _life    = len(_archive) + 1

    _ICONS = {"torpedo": "🎯", "mine": "💣", "sonar": "📡", "drone": "🚁", "silence": "🤫"}

    _log = []
    for i, e in enumerate(_moves):
        if e["type"] == "move":
            _log.append({"#": i + 1, "Event": f"Move {e['dir']}", "Detail": ""})
        elif e["type"] == "surface":
            _log.append({"#": i + 1, "Event": "🏄 Surface", "Detail": f"Sector {e.get('sector', '?')}"})
        elif e["type"] == "feedback":
            _hit = "✓ yes" if e.get("result") else "✗ no"
            if e["name"] == "sonar":
                if "target_r" in e:
                    _detail = f"Row {e['target_r'] + 1} — {_hit}"
                else:
                    _detail = f"Col {e['target_c'] + 1} — {_hit}"
                _log.append({"#": i + 1, "Event": "📡 Sonar result", "Detail": _detail})
            else:
                _log.append({"#": i + 1, "Event": "🚁 Drone result", "Detail": f"Sector {e.get('sector', '?')} — {_hit}"})
        else:
            icon = _ICONS.get(e["name"], e["name"])
            _detail = f"→ ({e['target_r'] + 1},{e['target_c'] + 1})" if e["name"] == "torpedo" and "target_r" in e else ""
            _log.append({"#": i + 1, "Event": f"{icon} {e['name'].capitalize()} fired", "Detail": _detail})

    _df_log = pd.DataFrame(_log) if _log else pd.DataFrame(columns=["#", "Event", "Detail"])

    mo.vstack([
        mo.md(f"### 📋 Event Log — Life {_life} | {len(_moves)} events"),
        mo.ui.table(_df_log, selection=None) if _log else mo.md("*No events yet.*"),
    ])
    return


if __name__ == "__main__":
    app.run()
