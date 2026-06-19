"""DFA Visual Simulator.

An animated, interactive visualisation of a Deterministic Finite Automaton
(DFA). The user types a string made of symbols from the DFA's alphabet; the
simulator animates a token gliding between states along Bézier-curved
transitions and finally declares the string ACCEPTED or REJECTED.

The bundled example DFA accepts binary strings whose length is divisible by
3. See :mod:`main` (and ``docs/USAGE.md``) for details on replacing it with
a custom automaton.

The module is split into two layers:

* **Core** (``DFA``, ``SimState``, ``calc_positions``, ``create_binary_dfa``)
  – pure logic, free of pygame.  Fully unit-testable.
* **UI** (``Animator``, ``Renderer``, ``Button``, ``InputBox``,
  ``DFASimulator``) – depends on ``pygame`` and is responsible for drawing
  and event handling.
"""

from __future__ import annotations

import math
import sys
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

import pygame

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

#: Width of the pygame window in pixels.
SCREEN_WIDTH: int = 800

#: Height of the pygame window in pixels.
SCREEN_HEIGHT: int = 650

#: Target frames per second for the main loop.
FPS: int = 60

#: Radius (px) used when drawing state circles.
STATE_RADIUS: int = 35

#: Colour palette used by the renderer.  All values are ``(r, g, b)`` tuples.
COLORS: Dict[str, Tuple[int, int, int]] = {
    "bg":            (25, 25, 35),
    "state":         (50, 50, 65),
    "border":        (150, 150, 170),
    "text":          (255, 255, 255),
    "transition":    (100, 100, 120),
    "highlight":     (255, 220, 50),
    "token":         (100, 180, 255),
    "active":        (50, 150, 255),
    "accepted":      (50, 220, 100),
    "rejected":      (255, 80, 80),
    "input_bg":      (40, 40, 55),
    "button":        (60, 60, 80),
    "button_hover":  (80, 80, 100),
    "disabled":      (40, 40, 50),
}


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Mode(Enum):
    """Execution mode selected by the user via the **Mode** button."""

    #: Steps fire automatically after each transition animation finishes.
    AUTO = auto()
    #: The user must click **Step** to advance.
    STEP = auto()


class AnimState(Enum):
    """High-level state of the :class:`Animator`."""

    IDLE = auto()      #: Not currently animating; ready for the next step.
    MOVING = auto()    #: Token is gliding between two states.
    PAUSE = auto()     #: Brief pause after a transition finishes.
    FINISHED = auto()  #: Whole input consumed; show accept/reject banner.


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


class DFA:
    """A deterministic finite automaton.

    Stores the five components of a DFA: ``states``, ``alphabet``,
    ``transitions``, ``start_state`` and ``final_states``.  Transitions are
    represented as a dictionary keyed by ``(from_state, symbol)`` pairs
    mapping to a target state, which is exactly what ``get`` expects.
    """

    def __init__(self) -> None:
        #: Every state reachable from any transition (populated by :meth:`add`).
        self.states: Set[str] = set()
        #: Set of input symbols seen on any transition.
        self.alphabet: Set[str] = set()
        #: ``{(from_state, symbol): to_state}`` lookup table.
        self.transitions: Dict[Tuple[str, str], str] = {}
        #: The single designated start state.
        self.start_state: str = ""
        #: Set of accepting (final) states.
        self.final_states: Set[str] = set()

    def add(self, frm: str, sym: str, to: str) -> None:
        """Add a single transition ``frm --sym--> to``.

        Side-effects: ``frm`` and ``to`` are added to :attr:`states`, and
        ``sym`` is added to :attr:`alphabet`.
        """
        self.states.update([frm, to])
        self.alphabet.add(sym)
        self.transitions[(frm, sym)] = to

    def get(self, state: str, sym: str) -> Optional[str]:
        """Return the target state for ``(state, sym)`` or ``None`` if undefined."""
        return self.transitions.get((state, sym))

    def is_complete(self) -> bool:
        """Return ``True`` if every state has a transition for every symbol.

        A *complete* DFA never gets stuck on a defined input — useful for
        catching accidental partial definitions in tests.
        """
        return all(
            (s, a) in self.transitions for s in self.states for a in self.alphabet
        )


class SimState:
    """Single-step execution engine for a :class:`DFA`.

    Decoupled from animation: callers feed symbols in one at a time via
    :meth:`step` and inspect :attr:`accepted` once :attr:`is_finished` flips
    to ``True``.
    """

    def __init__(self, dfa: DFA) -> None:
        self.dfa: DFA = dfa
        self.reset()

    def reset(self) -> None:
        """Return the simulator to its initial state (start state, no input)."""
        self.current_state: str = self.dfa.start_state
        self.input_string: str = ""
        self.current_index: int = 0
        self.is_running: bool = False
        self.is_finished: bool = False
        self.accepted: bool = False

    def start(self, input_string: str) -> bool:
        """Begin consuming ``input_string``.

        The empty string is always accepted by any DFA whose start state is
        final.  Non-empty strings are accepted only if every character
        belongs to :attr:`DFA.alphabet`.

        Returns ``True`` on success, ``False`` if any character is not in
        the DFA's alphabet.
        """
        if not all(c in self.dfa.alphabet for c in input_string):
            return False
        self.input_string = input_string
        self.current_state = self.dfa.start_state
        self.current_index = 0
        self.is_running = True
        self.is_finished = False
        self.accepted = False
        return True

    def is_empty_string(self) -> bool:
        """Return ``True`` iff the input string is the empty string."""
        return self.input_string == ""

    def step(self) -> Optional[Tuple[str, str, str]]:
        """Advance one transition.

        Returns ``(prev_state, symbol, next_state)`` on a successful step, or
        ``None`` if the simulation has finished (either the input was fully
        consumed or no outgoing transition exists for the next symbol).
        """
        if not self.is_running or self.current_index >= len(self.input_string):
            self.is_running = False
            self.is_finished = True
            self.accepted = self.current_state in self.dfa.final_states
            return None
        sym = self.input_string[self.current_index]
        prev = self.current_state
        nxt = self.dfa.get(self.current_state, sym)
        if nxt is None:
            self.is_running = False
            self.is_finished = True
            self.accepted = False
            return None
        self.current_state = nxt
        self.current_index += 1
        return (prev, sym, self.current_state)


# ---------------------------------------------------------------------------
# UI primitives
# ---------------------------------------------------------------------------


class Button:
    """A rectangular, optionally disabled button with a text label.

    Only left-clicks inside an enabled button are considered a hit.
    """

    def __init__(self, x: int, y: int, w: int, h: int, label: str) -> None:
        self.rect: pygame.Rect = pygame.Rect(x, y, w, h)
        self.label: str = label
        self.disabled: bool = False

    def contains(self, pos: Tuple[int, int]) -> bool:
        """Return ``True`` if the mouse position is inside this enabled button."""
        return not self.disabled and self.rect.collidepoint(pos)

    def hovered(self, pos: Tuple[int, int]) -> bool:
        """Alias for :meth:`contains` – the button is "hovered" iff hit-testable."""
        return self.contains(pos)


class InputBox:
    """Single-line text input that only accepts characters from an alphabet.

    Used for entering the DFA's input string.
    """

    def __init__(self, x: int, y: int, w: int, h: int, alphabet: Optional[Set[str]] = None) -> None:
        self.rect: pygame.Rect = pygame.Rect(x, y, w, h)
        self.text: str = ""
        self.active: bool = False
        #: If empty, every character is accepted.  Otherwise only those in this set.
        self.alphabet: Set[str] = set(alphabet) if alphabet else set()

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """Activate the box if ``pos`` is inside it, deactivate otherwise.

        Returns the new ``active`` state.
        """
        self.active = self.rect.collidepoint(pos)
        return self.active

    def handle_text(self, char: str) -> bool:
        """Append ``char`` if it is allowed.  Returns ``True`` if accepted."""
        if self.active and (not self.alphabet or char.lower() in self.alphabet):
            self.text += char
            return True
        return False

    def handle_backspace(self) -> bool:
        """Delete the trailing character if any.  Returns ``True`` on change."""
        if self.active and self.text:
            self.text = self.text[:-1]
            return True
        return False

    def clear(self) -> None:
        """Empty the box and deactivate it."""
        self.text = ""
        self.active = False


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------


class Animator:
    """Visual state machine driving the token and the result fade-in.

    Three timelines are tracked independently:

    * Token motion (cubic ease-in-out between two positions)
    * Pulse amount (sine-like oscillation on the active state's radius)
    * Result banner alpha (linear fade-in once the simulation finishes)
    """

    #: Default token travel time, in milliseconds.
    DEFAULT_DURATION_MS: int = 600
    #: Default post-transition pause, in milliseconds.
    DEFAULT_PAUSE_MS: int = 200
    #: Frame-time (ms) it takes the result banner to reach full opacity.
    RESULT_FADE_MS: int = 500

    def __init__(self) -> None:
        self.state: AnimState = AnimState.IDLE
        self.token_pos: Tuple[float, float] = (0.0, 0.0)
        self.token_start: Tuple[float, float] = (0.0, 0.0)
        self.token_end: Tuple[float, float] = (0.0, 0.0)
        self.token_progress: float = 0.0
        self.token_elapsed: float = 0.0
        self.token_duration: int = self.DEFAULT_DURATION_MS
        self.pulse_amount: float = 0.0
        self.pulse_dir: int = 1
        self.result_alpha: int = 0
        #: ``(from, to, symbol)`` describing the edge currently being highlighted.
        self.active_edge: Optional[Tuple[str, str, str]] = None
        self.pause_elapsed: float = 0.0

    def reset(self) -> None:
        """Cancel any in-progress animation and clear visual state."""
        self.state = AnimState.IDLE
        self.token_progress = 0.0
        self.token_elapsed = 0.0
        self.active_edge = None
        self.result_alpha = 0
        self.pause_elapsed = 0.0

    def start_transition(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        duration: int = DEFAULT_DURATION_MS,
    ) -> None:
        """Begin animating the token from ``start`` to ``end``."""
        self.token_start = start
        self.token_end = end
        self.token_pos = start
        self.token_progress = 0.0
        self.token_elapsed = 0.0
        self.token_duration = duration
        self.state = AnimState.MOVING

    def start_pause(self, duration: int = DEFAULT_PAUSE_MS) -> None:
        """Enter a brief idle pause – not currently invoked but kept for symmetry."""
        self.pause_elapsed = 0.0
        self.state = AnimState.PAUSE

    def finish(self) -> None:
        """Mark the simulation as finished and start the result fade-in."""
        self.state = AnimState.FINISHED
        self.result_alpha = 0

    def update(self, dt: float) -> None:
        """Advance all timelines by ``dt`` milliseconds."""
        if self.state == AnimState.MOVING:
            self.token_elapsed += dt
            self.token_progress = min(1.0, self.token_elapsed / self.token_duration)
            # Cubic ease-in-out: slow start, fast middle, slow end.
            t = (
                4 * self.token_progress ** 3
                if self.token_progress < 0.5
                else 1 - ((-2 * self.token_progress + 2) ** 3) / 2
            )
            sx, sy = self.token_start
            ex, ey = self.token_end
            self.token_pos = (sx + (ex - sx) * t, sy + (ey - sy) * t)
            if self.token_progress >= 1.0:
                self.state = AnimState.IDLE
        elif self.state == AnimState.PAUSE:
            self.pause_elapsed += dt
            if self.pause_elapsed >= self.DEFAULT_PAUSE_MS:
                self.state = AnimState.IDLE
        elif self.state == AnimState.FINISHED and self.result_alpha < 255:
            # Linear fade – 0.5 alpha per ms means ~500 ms total.
            self.result_alpha = min(255, self.result_alpha + int(0.5 * dt))

        # Pulse oscillation (kept running in every state so the active state
        # always breathes once we are in a simulation).
        self.pulse_amount += 0.003 * dt * self.pulse_dir
        if self.pulse_amount > 0.2:
            self.pulse_dir = -1
        elif self.pulse_amount < 0.0:
            self.pulse_dir = 1


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class Renderer:
    """All drawing routines.

    The renderer is stateless apart from a font cache and a layout cache; it
    never mutates any input data structure.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen: pygame.Surface = screen
        #: Three font sizes: large (status), medium (UI), small (edge labels).
        self.fonts: Tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font] = (
            _safe_font(36),
            _safe_font(24),
            _safe_font(18),
        )
        #: ``{state_name: (x, y)}`` – populated by :meth:`set_positions`.
        self.state_positions: Dict[str, Tuple[float, float]] = {}

    def set_positions(self, positions: Dict[str, Tuple[float, float]]) -> None:
        """Update the cached state layout used by every draw routine."""
        self.state_positions = positions

    def get_pos(self, state: str) -> Tuple[float, float]:
        """Return the cached position of ``state`` or ``(0, 0)`` if unknown."""
        return self.state_positions.get(state, (0, 0))

    def clear(self) -> None:
        """Fill the screen with the background colour."""
        self.screen.fill(COLORS["bg"])

    def draw_state(
        self,
        state: str,
        is_final: bool,
        is_current: bool,
        is_start: bool,
        pulse_radius: Optional[float],
        status_color: Optional[Tuple[int, int, int]],
    ) -> None:
        """Render a single state circle with optional pulse and accept ring."""
        pos = self.state_positions.get(state)
        if not pos:
            return
        x, y = pos
        r = pulse_radius if pulse_radius else STATE_RADIUS
        border = status_color if is_current and status_color else (
            COLORS["active"] if is_current else COLORS["border"]
        )
        pygame.draw.circle(self.screen, COLORS["state"], (int(x), int(y)), int(r))
        pygame.draw.circle(self.screen, border, (int(x), int(y)), int(r), 3)
        if is_final:
            pygame.draw.circle(self.screen, border, (int(x), int(y)), int(r * 0.7), 2)
        txt = self.fonts[1].render(state, True, COLORS["text"])
        self.screen.blit(txt, txt.get_rect(center=(int(x), int(y))))
        if is_start:
            self._draw_arrow(
                (x - STATE_RADIUS * 2.5, y),
                (x - STATE_RADIUS, y),
                COLORS["border"],
            )

    def draw_transitions(self, dfa: DFA, highlighted: Optional[Tuple[str, str, str]]) -> None:
        """Draw every transition in ``dfa``, highlighting ``highlighted`` if present."""
        for (frm, sym), to in dfa.transitions.items():
            is_hl = bool(highlighted and highlighted[0] == frm and highlighted[2] == to)
            self._draw_transition(frm, to, sym, is_hl)

    def _draw_transition(self, frm: str, to: str, sym: str, highlighted: bool) -> None:
        """Route a transition to either the curved-arrow or self-loop helper."""
        fp, tp = self.get_pos(frm), self.get_pos(to)
        if not fp or not tp:
            return
        if frm == to:
            self._draw_self_loop(fp, sym, highlighted)
        else:
            self._draw_curved_arrow(fp, tp, sym, highlighted)

    def _draw_curved_arrow(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        sym: str,
        highlighted: bool,
    ) -> None:
        """Draw a Bézier-curved arrow with a midpoint label."""
        color = COLORS["highlight"] if highlighted else COLORS["transition"]
        width = 4 if highlighted else 2
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        off = STATE_RADIUS
        sp = (sx + dx / dist * off, sy + dy / dist * off)
        ep = (ex - dx / dist * off, ey - dy / dist * off)
        mx, my = (sp[0] + ep[0]) / 2, (sp[1] + ep[1]) / 2
        # Perpendicular control point – same offset for both x and y gives a
        # visually consistent bow regardless of edge orientation.
        cx = mx - (ey - sy) / dist * 30
        cy = my + (ex - sx) / dist * 30
        pts = _bezier(sp, (cx, cy), ep, 20)
        if len(pts) > 1:
            pygame.draw.lines(self.screen, color, False, pts, width)
            self._draw_arrowhead(pts[-2], pts[-1], color)
        txt = self.fonts[2].render(sym, True, color)
        self.screen.blit(txt, txt.get_rect(center=(int(cx), int(cy - 10))))

    def _draw_self_loop(
        self,
        pos: Tuple[float, float],
        sym: str,
        highlighted: bool,
    ) -> None:
        """Draw a circular self-loop with a label above the state."""
        color = COLORS["highlight"] if highlighted else COLORS["transition"]
        width = 4 if highlighted else 2
        x, y = pos
        r = STATE_RADIUS * 1.4
        cx, cy = x, y - r * 0.7
        pts: List[Tuple[float, float]] = []
        for i in range(21):
            t = math.pi * 0.15 + (math.pi * 1.7) * i / 20
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
        pygame.draw.lines(self.screen, color, False, pts, width)
        self._draw_arrowhead(pts[-2], pts[-1], color)
        txt = self.fonts[2].render(sym, True, color)
        self.screen.blit(txt, txt.get_rect(center=(int(x), int(y - r * 1.8))))

    def draw_token(self, pos: Tuple[float, float]) -> None:
        """Render the moving token as three concentric circles for depth."""
        x, y = pos
        pygame.draw.circle(self.screen, (80, 140, 200), (int(x), int(y)), 16)
        pygame.draw.circle(self.screen, COLORS["token"], (int(x), int(y)), 12)
        pygame.draw.circle(self.screen, (200, 230, 255), (int(x - 3.6), int(y - 3.6)), 4.8)

    def draw_input_box(self, rect: pygame.Rect, text: str, active: bool) -> None:
        """Draw the input rectangle and its current text (left-aligned)."""
        pygame.draw.rect(self.screen, COLORS["input_bg"], rect)
        pygame.draw.rect(
            self.screen,
            COLORS["active"] if active else COLORS["border"],
            rect,
            2,
        )
        txt = self.fonts[1].render(text, True, COLORS["text"])
        self.screen.blit(txt, txt.get_rect(midleft=(rect.x + 10, rect.centery)))

    def draw_button(
        self,
        rect: pygame.Rect,
        label: str,
        hovered: bool,
        disabled: bool = False,
    ) -> None:
        """Draw a button with disabled / hover / normal colour variants."""
        if disabled:
            bg, tc = COLORS["disabled"], (100, 100, 100)
        elif hovered:
            bg, tc = COLORS["button_hover"], COLORS["text"]
        else:
            bg, tc = COLORS["button"], COLORS["text"]
        pygame.draw.rect(self.screen, bg, rect, border_radius=5)
        pygame.draw.rect(self.screen, COLORS["border"], rect, 2, border_radius=5)
        txt = self.fonts[1].render(label, True, tc)
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def draw_status(self, text: str) -> None:
        """Render the centred status string at the top of the screen."""
        txt = self.fonts[0].render(text, True, COLORS["text"])
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, 25)))

    def draw_result(self, accepted: bool, alpha: int) -> None:
        """Render the ACCEPTED / REJECTED banner, honouring the fade-in alpha."""
        text, color = ("ACCEPTED", COLORS["accepted"]) if accepted else ("REJECTED", COLORS["rejected"])
        txt = self.fonts[0].render(text, True, color)
        if alpha < 255:
            txt.set_alpha(alpha)
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, 60)))

    def draw_symbol(self, sym: str, idx: int, total: int) -> None:
        """Render the right-aligned "Symbol: 'x' (n/N)" counter."""
        txt = self.fonts[1].render(
            f"Symbol: '{sym}' ({idx + 1}/{total})", True, COLORS["text"]
        )
        self.screen.blit(txt, txt.get_rect(right=SCREEN_WIDTH - 20, top=15))


# ---------------------------------------------------------------------------
# Pure helpers (module-level so they are easy to unit-test)
# ---------------------------------------------------------------------------


def _bezier(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    steps: int,
) -> List[Tuple[float, float]]:
    """Return ``steps + 1`` sample points along a quadratic Bézier curve."""
    pts: List[Tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def _safe_font(size: int) -> pygame.font.Font:
    """Return ``pygame.font.SysFont(None, size)`` or a fallback default font.

    Some headless / minimal pygame builds refuse ``None`` as the font name;
    swallowing that and trying the default font keeps the app from crashing
    on unusual platforms.
    """
    try:
        return pygame.font.SysFont(None, size)
    except Exception:
        return pygame.font.Font(None, size)


def calc_positions(
    states: List[str], cx: float, cy: float, r: float = 150
) -> Dict[str, Tuple[float, float]]:
    """Arrange ``states`` evenly around a circle of radius ``r``.

    Special-cases the empty list, single state, and two-state layouts so the
    output looks sensible at very small sizes.
    """
    n = len(states)
    if n == 0:
        return {}
    if n == 1:
        return {states[0]: (cx, cy)}
    if n == 2:
        return {states[0]: (cx - 100, cy), states[1]: (cx + 100, cy)}
    return {
        states[i]: (
            cx + r * math.cos(2 * math.pi * i / n - math.pi / 2),
            cy + r * math.sin(2 * math.pi * i / n - math.pi / 2),
        )
        for i in range(n)
    }


def create_binary_dfa() -> DFA:
    """Build the bundled example DFA: accepts binary strings of length ≡ 0 (mod 3)."""
    dfa = DFA()
    dfa.start_state = "q0"
    dfa.final_states = {"q0"}
    dfa.add("q0", "0", "q1")
    dfa.add("q0", "1", "q0")
    dfa.add("q1", "0", "q1")
    dfa.add("q1", "1", "q2")
    dfa.add("q2", "0", "q1")
    dfa.add("q2", "1", "q0")
    return dfa


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


class DFASimulator:
    """Top-level controller: pygame window, event loop, and glue logic.

    Construction initialises pygame and lays out the UI chrome.  Call
    :meth:`run` to enter the main loop.
    """

    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()
        try:
            self.screen: pygame.Surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as exc:
            # Most commonly: no available display in a headless environment.
            print(f"Failed to open display: {exc}", file=sys.stderr)
            raise SystemExit(1)
        pygame.display.set_caption("DFA Visual Simulator")
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.dfa: DFA = create_binary_dfa()
        self.sim: SimState = SimState(self.dfa)
        self.renderer: Renderer = Renderer(self.screen)
        self.animator: Animator = Animator()
        iw, ih = 300, 40
        self.input_box: InputBox = InputBox(
            (SCREEN_WIDTH - iw) // 2, SCREEN_HEIGHT - 120, iw, ih, self.dfa.alphabet
        )
        bw, by = 100, SCREEN_HEIGHT - 60
        self.start_btn: Button = Button(SCREEN_WIDTH // 2 - bw - 10, by, bw, 40, "Start")
        self.reset_btn: Button = Button(SCREEN_WIDTH // 2 + 10, by, bw, 40, "Reset")
        self.mode_btn: Button = Button(20, by, 120, 40, "Mode: Auto")
        self.step_btn: Button = Button(SCREEN_WIDTH // 2 - 50, by + 50, 100, 35, "Step")
        self.speed_btn: Button = Button(SCREEN_WIDTH - 140, by, 120, 40, "Speed: 1.0x")
        self.mode: Mode = Mode.AUTO
        #: Multiplier applied to the Animator's per-step ``dt`` in Auto mode.
        #: 1.0 = default, 2.0 = twice as fast, 0.5 = half speed.
        self.speed_multiplier: float = 1.0
        self.state_positions: Dict[str, Tuple[float, float]] = calc_positions(
            list(self.dfa.states), SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30
        )
        self.renderer.set_positions(self.state_positions)
        self.running: bool = True

    def run(self) -> None:
        """Run the main loop until the user closes the window."""
        try:
            while self.running:
                dt = self.clock.tick(FPS)
                self.handle_events()
                self.update(dt)
                self.render()
                pygame.display.flip()
        finally:
            pygame.quit()

    def handle_events(self) -> None:
        """Drain the pygame event queue and update internal state accordingly."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                self.input_box.handle_click(pos)
                if self.start_btn.contains(pos):
                    self.start_sim()
                elif self.reset_btn.contains(pos):
                    self.reset_sim()
                elif self.mode_btn.contains(pos):
                    self.mode = Mode.STEP if self.mode == Mode.AUTO else Mode.AUTO
                    self.mode_btn.label = f"Mode: {self.mode.name.capitalize()}"
                    self.reset_sim()
                elif self.speed_btn.contains(pos):
                    self._cycle_speed()
                elif self.step_btn.contains(pos) and not self.step_btn.disabled:
                    self.step_sim()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.input_box.handle_backspace()
                elif event.key == pygame.K_RETURN and not self.start_btn.disabled:
                    self.start_sim()
                elif event.unicode and self.input_box.active:
                    self.input_box.handle_text(event.unicode)

    def start_sim(self) -> None:
        """Kick off a simulation using the current input box text (if non-empty)."""
        txt = self.input_box.text
        if not txt:
            return
        if not self.sim.start(txt):
            # Input contained an alphabet violation – the InputBox should
            # already have prevented this, but guard anyway.
            return
        self.start_btn.disabled = True
        self.step_btn.disabled = True
        self.animator.reset()
        if self.mode == Mode.AUTO:
            self.do_step()

    def reset_sim(self) -> None:
        """Return the simulator to its just-started state."""
        self.sim.reset()
        self.animator.reset()
        self.start_btn.disabled = False
        self.step_btn.disabled = self.mode == Mode.AUTO
        self.update_step_btn()

    def step_sim(self) -> None:
        """Advance by one transition – only valid in STEP mode when idle."""
        if self.mode == Mode.STEP and self.animator.state != AnimState.MOVING:
            self.do_step()

    def clear_input(self) -> None:
        """Clear the input box and reset the simulation without touching the DFA."""
        self.input_box.clear()
        self.reset_sim()

    def do_step(self) -> None:
        """Perform one transition: update ``SimState`` and prime the animator."""
        if not self.sim.is_running:
            return
        result = self.sim.step()
        if result is None:
            self.animator.finish()
            self.start_btn.disabled = False
        else:
            frm, sym, to = result
            self.animator.active_edge = (frm, to, sym)
            self.animator.start_transition(
                self.renderer.get_pos(frm), self.renderer.get_pos(to)
            )

    def update(self, dt: float) -> None:
        """Per-frame state update: advance animations and queue auto-steps."""
        # Scale delta-time by the current speed multiplier in Auto mode so
        # that animations play faster or slower without changing the loop.
        scaled_dt = dt * self.speed_multiplier if self.mode == Mode.AUTO else dt
        self.animator.update(scaled_dt)
        if (
            self.animator.state == AnimState.IDLE
            and self.sim.is_running
            and self.mode == Mode.AUTO
        ):
            self.do_step()
        self.update_step_btn()

    def _cycle_speed(self) -> None:
        """Advance the speed multiplier through ``{0.5, 1.0, 2.0, 4.0}``."""
        steps = (0.5, 1.0, 2.0, 4.0)
        idx = min(range(len(steps)), key=lambda i: abs(steps[i] - self.speed_multiplier))
        self.speed_multiplier = steps[(idx + 1) % len(steps)]
        self.speed_btn.label = f"Speed: {self.speed_multiplier:g}x"

    def update_step_btn(self) -> None:
        """Refresh the Step button's disabled flag based on current state."""
        if self.mode == Mode.STEP:
            self.step_btn.disabled = not (
                self.sim.is_running and self.animator.state != AnimState.MOVING
            )

    def render(self) -> None:
        """Draw a single frame to the back buffer."""
        self.renderer.clear()
        if self.sim.is_finished:
            status = "Simulation Complete"
        elif self.sim.is_running:
            status = f"Processing: {self.sim.input_string}"
        else:
            status = "Enter input string (0s and 1s)"
        self.renderer.draw_status(status)
        self.renderer.draw_transitions(self.dfa, self.animator.active_edge)
        for state in self.dfa.states:
            is_final = state in self.dfa.final_states
            is_current = state == self.sim.current_state
            is_start = state == self.dfa.start_state
            status_color: Optional[Tuple[int, int, int]] = None
            pulse_radius: Optional[float] = None
            if is_current:
                if self.sim.is_finished:
                    status_color = COLORS["accepted"] if self.sim.accepted else COLORS["rejected"]
                else:
                    status_color = COLORS["active"]
                    pulse_radius = STATE_RADIUS * (1.0 + self.animator.pulse_amount)
            self.renderer.draw_state(state, is_final, is_current, is_start, pulse_radius, status_color)
        if self.animator.state == AnimState.MOVING:
            self.renderer.draw_token(self.animator.token_pos)
        if self.sim.is_running and self.sim.input_string:
            idx = min(self.sim.current_index, len(self.sim.input_string) - 1)
            self.renderer.draw_symbol(
                self.sim.input_string[idx], idx, len(self.sim.input_string)
            )
        if self.animator.state == AnimState.FINISHED:
            self.renderer.draw_result(self.sim.accepted, self.animator.result_alpha)
        mouse = pygame.mouse.get_pos()
        self.renderer.draw_input_box(self.input_box.rect, self.input_box.text, self.input_box.active)
        self.renderer.draw_button(self.start_btn.rect, self.start_btn.label, self.start_btn.hovered(mouse), self.start_btn.disabled)
        self.renderer.draw_button(self.reset_btn.rect, self.reset_btn.label, self.reset_btn.hovered(mouse))
        self.renderer.draw_button(self.mode_btn.rect, self.mode_btn.label, self.mode_btn.hovered(mouse))
        self.renderer.draw_button(self.speed_btn.rect, self.speed_btn.label, self.speed_btn.hovered(mouse))
        if self.mode == Mode.STEP:
            self.renderer.draw_button(self.step_btn.rect, self.step_btn.label, self.step_btn.hovered(mouse), self.step_btn.disabled)


def main() -> int:
    """Entry point.  Returns the process exit code."""
    try:
        DFASimulator().run()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 – top-level safety net.
        print(f"Unhandled error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())