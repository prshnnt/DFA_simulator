"""DFA Visual Simulator - Animated execution of Deterministic Finite Automata."""
import pygame, math
from enum import Enum, auto
from typing import Optional, Tuple, Dict, List, Set

SCREEN_WIDTH, SCREEN_HEIGHT, FPS, STATE_RADIUS = 800, 650, 60, 35
COLORS = {'bg': (25, 25, 35), 'state': (50, 50, 65), 'border': (150, 150, 170), 'text': (255, 255, 255), 'transition': (100, 100, 120), 'highlight': (255, 220, 50), 'token': (100, 180, 255), 'active': (50, 150, 255), 'accepted': (50, 220, 100), 'rejected': (255, 80, 80), 'input_bg': (40, 40, 55), 'button': (60, 60, 80), 'button_hover': (80, 80, 100), 'disabled': (40, 40, 50)}

class Mode(Enum): AUTO = auto(); STEP = auto()
class AnimState(Enum): IDLE = auto(); MOVING = auto(); PAUSE = auto(); FINISHED = auto()

#main daata struct
class DFA:
    def __init__(self):
        self.states: Set[str] = set()
        self.alphabet: Set[str] = set()
        self.transitions: Dict[Tuple[str, str], str] = {}
        self.start_state: str = ""
        self.final_states: Set[str] = set()
    def add(self, frm: str, sym: str, to: str) -> None:
        self.states.update([frm, to]); self.alphabet.add(sym); self.transitions[(frm, sym)] = to
    def get(self, state: str, sym: str) -> Optional[str]:
        return self.transitions.get((state, sym))

class SimState:
    def __init__(self, dfa: DFA): self.dfa = dfa; self.reset()
    def reset(self) -> None:
        self.current_state = self.dfa.start_state; self.input_string = ""; self.current_index = 0; self.is_running = False; self.is_finished = False; self.accepted = False
    def start(self, input_string: str) -> bool:
        if not all(c in self.dfa.alphabet for c in input_string): return False
        self.input_string = input_string; self.current_state = self.dfa.start_state; self.current_index = 0; self.is_running = True; self.is_finished = False; return True
    def step(self) -> Optional[Tuple[str, str, str]]:
        if not self.is_running or self.current_index >= len(self.input_string):
            self.is_running = False; self.is_finished = True; self.accepted = self.current_state in self.dfa.final_states; return None
        sym = self.input_string[self.current_index]; prev = self.current_state; nxt = self.dfa.get(self.current_state, sym)
        if nxt is None: self.is_running = False; self.is_finished = True; self.accepted = False; return None
        self.current_state = nxt; self.current_index += 1; return (prev, sym, self.current_state)

class Button:
    def __init__(self, x: int, y: int, w: int, h: int, label: str):
        self.rect = pygame.Rect(x, y, w, h); self.label = label; self.disabled = False
    def contains(self, pos: Tuple[int, int]) -> bool: return not self.disabled and self.rect.collidepoint(pos)
    def hovered(self, pos: Tuple[int, int]) -> bool: return self.contains(pos)

class InputBox:
    def __init__(self, x: int, y: int, w: int, h: int, alphabet: Set[str] = None):
        self.rect = pygame.Rect(x, y, w, h); self.text = ""; self.active = False; self.alphabet = alphabet or set()
    def handle_click(self, pos: Tuple[int, int]) -> bool: self.active = self.rect.collidepoint(pos); return self.active
    def handle_text(self, char: str) -> bool:
        if self.active and char.lower() in self.alphabet: self.text += char; return True
        return False
    def handle_backspace(self) -> bool:
        if self.active and self.text: self.text = self.text[:-1]; return True
        return False
    def clear(self) -> None: self.text = ""; self.active = False

class Animator:
    def __init__(self):
        self.state = AnimState.IDLE; self.token_pos = (0.0, 0.0); self.token_start = (0.0, 0.0); self.token_end = (0.0, 0.0)
        self.token_progress = 0.0; self.token_elapsed = 0; self.token_duration = 600; self.pulse_amount = 0.0; self.pulse_dir = 1
        self.result_alpha = 0; self.active_edge: Optional[Tuple[str, str, str]] = None; self.pause_elapsed = 0
    def reset(self) -> None:
        self.state = AnimState.IDLE; self.token_progress = 0.0; self.token_elapsed = 0; self.active_edge = None; self.result_alpha = 0
    def start_transition(self, start: Tuple[float, float], end: Tuple[float, float], duration: int = 600) -> None:
        self.token_start = start; self.token_end = end; self.token_pos = start; self.token_progress = 0.0; self.token_elapsed = 0; self.token_duration = duration; self.state = AnimState.MOVING
    def start_pause(self, duration: int = 200) -> None: self.pause_elapsed = 0; self.state = AnimState.PAUSE
    def finish(self) -> None: self.state = AnimState.FINISHED; self.result_alpha = 0
    def update(self, dt: float) -> None:
        if self.state == AnimState.MOVING:
            self.token_elapsed += dt; self.token_progress = min(1.0, self.token_elapsed / self.token_duration)
            t = 4 * self.token_progress ** 3 if self.token_progress < 0.5 else 1 - ((-2 * self.token_progress + 2) ** 3) / 2
            sx, sy = self.token_start; ex, ey = self.token_end
            self.token_pos = (sx + (ex - sx) * t, sy + (ey - sy) * t)
            if self.token_progress >= 1.0: self.state = AnimState.IDLE
        elif self.state == AnimState.PAUSE:
            self.pause_elapsed += dt
            if self.pause_elapsed >= 200: self.state = AnimState.IDLE
        elif self.state == AnimState.FINISHED and self.result_alpha < 255:
            self.result_alpha = min(255, self.result_alpha + int(0.005 * dt))
        self.pulse_amount += 0.003 * dt * self.pulse_dir
        if self.pulse_amount > 0.2: self.pulse_dir = -1
        elif self.pulse_amount < 0.0: self.pulse_dir = 1

class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen; self.fonts = (pygame.font.Font(None, 36), pygame.font.Font(None, 24), pygame.font.Font(None, 18)); self.state_positions: Dict[str, Tuple[float, float]] = {}
    def set_positions(self, positions: Dict[str, Tuple[float, float]]) -> None: self.state_positions = positions
    def get_pos(self, state: str) -> Tuple[float, float]: return self.state_positions.get(state, (0, 0))
    def clear(self) -> None: self.screen.fill(COLORS['bg'])
    def draw_state(self, state: str, is_final: bool, is_current: bool, is_start: bool, pulse_radius: Optional[float], status_color: Optional[Tuple[int, int, int]]) -> None:
        pos = self.state_positions.get(state)
        if not pos: return
        x, y = pos; r = pulse_radius if pulse_radius else STATE_RADIUS
        border = status_color if is_current and status_color else (COLORS['active'] if is_current else COLORS['border'])
        pygame.draw.circle(self.screen, COLORS['state'], (int(x), int(y)), int(r))
        pygame.draw.circle(self.screen, border, (int(x), int(y)), int(r), 3)
        if is_final: pygame.draw.circle(self.screen, border, (int(x), int(y)), int(r * 0.7), 2)
        txt = self.fonts[1].render(state, True, COLORS['text']); self.screen.blit(txt, txt.get_rect(center=(int(x), int(y))))
        if is_start: self._draw_arrow((x - STATE_RADIUS * 2.5, y), (x - STATE_RADIUS, y), COLORS['border'])
    def draw_transitions(self, dfa: DFA, highlighted: Optional[Tuple[str, str, str]]) -> None:
        for (frm, sym), to in dfa.transitions.items():
            is_hl = highlighted and highlighted[0] == frm and highlighted[2] == to; self._draw_transition(frm, to, sym, is_hl)
    def _draw_transition(self, frm: str, to: str, sym: str, highlighted: bool) -> None:
        fp, tp = self.get_pos(frm), self.get_pos(to)
        if not fp or not tp: return
        if frm == to: self._draw_self_loop(fp, sym, highlighted)
        else: self._draw_curved_arrow(fp, tp, sym, highlighted)
    def _draw_curved_arrow(self, start: Tuple[float, float], end: Tuple[float, float], sym: str, highlighted: bool) -> None:
        color = COLORS['highlight'] if highlighted else COLORS['transition']; width = 4 if highlighted else 2
        sx, sy = start; ex, ey = end; dx, dy = ex - sx, ey - sy; dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0: return
        off = STATE_RADIUS; sp = (sx + dx / dist * off, sy + dy / dist * off); ep = (ex - dx / dist * off, ey - dy / dist * off)
        mx, my = (sp[0] + ep[0]) / 2, (sp[1] + ep[1]) / 2; cx, cy = mx - (ey - sy) / dist * 30, my + (ex - sx) / dist * 30
        pts = self._bezier(sp, (cx, cy), ep, 20)
        if len(pts) > 1: pygame.draw.lines(self.screen, color, False, pts, width); self._draw_arrowhead(pts[-2], pts[-1], color)
        txt = self.fonts[2].render(sym, True, color); self.screen.blit(txt, txt.get_rect(center=(int(cx), int(cy - 10))))
    def _draw_self_loop(self, pos: Tuple[float, float], sym: str, highlighted: bool) -> None:
        color = COLORS['highlight'] if highlighted else COLORS['transition']; width = 4 if highlighted else 2
        x, y = pos; r = STATE_RADIUS * 1.4; cx, cy = x, y - r * 0.7; pts = []
        for i in range(21): t = math.pi * 0.15 + (math.pi * 1.7) * i / 20; pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
        pygame.draw.lines(self.screen, color, False, pts, width); self._draw_arrowhead(pts[-2], pts[-1], color)
        txt = self.fonts[2].render(sym, True, color); self.screen.blit(txt, txt.get_rect(center=(int(x), int(y - r * 1.8))))
    def _bezier(self, p0, p1, p2, steps) -> List[Tuple[float, float]]:
        pts = []
        for i in range(steps + 1):
            t = i / steps; x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]; y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
            pts.append((x, y))
        return pts
    def _draw_arrow(self, start: Tuple[float, float], end: Tuple[float, float], color: Tuple[int, int, int]) -> None:
        pygame.draw.line(self.screen, color, start, end, 2); self._draw_arrowhead(start, end, color)
    def _draw_arrowhead(self, start: Tuple[float, float], end: Tuple[float, float], color: Tuple[int, int, int]) -> None:
        sx, sy = start; ex, ey = end; angle = math.atan2(ey - sy, ex - sx); al, aa = 12, math.pi / 6
        p1 = (ex - al * math.cos(angle - aa), ey - al * math.sin(angle - aa)); p2 = (ex - al * math.cos(angle + aa), ey - al * math.sin(angle + aa))
        pygame.draw.polygon(self.screen, color, [end, p1, p2])
    def draw_token(self, pos: Tuple[float, float]) -> None:
        x, y = pos; pygame.draw.circle(self.screen, (80, 140, 200), (int(x), int(y)), 16)
        pygame.draw.circle(self.screen, COLORS['token'], (int(x), int(y)), 12)
        pygame.draw.circle(self.screen, (200, 230, 255), (int(x - 3.6), int(y - 3.6)), 4.8)
    def draw_input_box(self, rect: pygame.Rect, text: str, active: bool) -> None:
        pygame.draw.rect(self.screen, COLORS['input_bg'], rect); pygame.draw.rect(self.screen, COLORS['active'] if active else COLORS['border'], rect, 2)
        txt = self.fonts[1].render(text, True, COLORS['text']); self.screen.blit(txt, txt.get_rect(midleft=(rect.x + 10, rect.centery)))
    def draw_button(self, rect: pygame.Rect, label: str, hovered: bool, disabled: bool = False) -> None:
        if disabled: bg, tc = COLORS['disabled'], (100, 100, 100)
        elif hovered: bg, tc = COLORS['button_hover'], COLORS['text']
        else: bg, tc = COLORS['button'], COLORS['text']
        pygame.draw.rect(self.screen, bg, rect, border_radius=5); pygame.draw.rect(self.screen, COLORS['border'], rect, 2, border_radius=5)
        txt = self.fonts[1].render(label, True, tc); self.screen.blit(txt, txt.get_rect(center=rect.center))
    def draw_status(self, text: str) -> None:
        txt = self.fonts[0].render(text, True, COLORS['text']); self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, 25)))
    def draw_result(self, accepted: bool, alpha: int) -> None:
        text, color = ("ACCEPTED", COLORS['accepted']) if accepted else ("REJECTED", COLORS['rejected'])
        txt = self.fonts[0].render(text, True, color)
        if alpha < 255: txt.set_alpha(alpha)
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, 60)))
    def draw_symbol(self, sym: str, idx: int, total: int) -> None:
        txt = self.fonts[1].render(f"Symbol: '{sym}' ({idx + 1}/{total})", True, COLORS['text']); self.screen.blit(txt, txt.get_rect(right=SCREEN_WIDTH - 20, top=15))

def calc_positions(states: List[str], cx: float, cy: float, r: float = 150) -> Dict[str, Tuple[float, float]]:
    n = len(states)
    if n == 0: return {}
    if n == 1: return {states[0]: (cx, cy)}
    if n == 2: return {states[0]: (cx - 100, cy), states[1]: (cx + 100, cy)}
    return {states[i]: (cx + r * math.cos(2 * math.pi * i / n - math.pi / 2), cy + r * math.sin(2 * math.pi * i / n - math.pi / 2)) for i in range(n)}

def create_binary_dfa() -> DFA:
    dfa = DFA(); dfa.start_state = "q0"; dfa.final_states = {"q0"}
    dfa.add("q0", "0", "q1"); dfa.add("q0", "1", "q0"); dfa.add("q1", "0", "q1"); dfa.add("q1", "1", "q2"); dfa.add("q2", "0", "q1"); dfa.add("q2", "1", "q0"); return dfa

class DFASimulator:
    def __init__(self):
        pygame.init(); self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)); pygame.display.set_caption("DFA Visual Simulator"); self.clock = pygame.time.Clock()
        self.dfa = create_binary_dfa(); self.sim = SimState(self.dfa); self.renderer = Renderer(self.screen); self.animator = Animator()
        iw, ih = 300, 40; self.input_box = InputBox((SCREEN_WIDTH - iw) // 2, SCREEN_HEIGHT - 120, iw, ih, self.dfa.alphabet); bw, by = 100, SCREEN_HEIGHT - 60
        self.start_btn = Button(SCREEN_WIDTH // 2 - bw - 10, by, bw, 40, "Start"); self.reset_btn = Button(SCREEN_WIDTH // 2 + 10, by, bw, 40, "Reset")
        self.mode_btn = Button(20, by, 120, 40, "Mode: Auto"); self.step_btn = Button(SCREEN_WIDTH // 2 - 50, by + 50, 100, 35, "Step"); self.mode = Mode.AUTO
        self.state_positions = calc_positions(list(self.dfa.states), SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30); self.renderer.set_positions(self.state_positions); self.running = True
    def run(self):
        while self.running: dt = self.clock.tick(FPS); self.handle_events(); self.update(dt); self.render(); pygame.display.flip()
        pygame.quit()
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False; return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos(); self.input_box.handle_click(pos)
                if self.start_btn.contains(pos): self.start_sim()
                elif self.reset_btn.contains(pos): self.reset_sim()
                elif self.mode_btn.contains(pos):
                    self.mode = Mode.STEP if self.mode == Mode.AUTO else Mode.AUTO; self.mode_btn.label = f"Mode: {self.mode.name.capitalize()}"; self.reset_sim()
                elif self.step_btn.contains(pos) and not self.step_btn.disabled: self.step_sim()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE: self.input_box.handle_backspace()
                elif event.key == pygame.K_RETURN and not self.start_btn.disabled: self.start_sim()
                elif event.unicode and self.input_box.active: self.input_box.handle_text(event.unicode)
    def start_sim(self):
        txt = self.input_box.text
        if not txt: return
        if self.sim.start(txt):
            self.start_btn.disabled = True; self.step_btn.disabled = True; self.animator.reset()
            if self.mode == Mode.AUTO: self.do_step()
    def reset_sim(self):
        self.sim.reset(); self.animator.reset(); self.start_btn.disabled = False; self.step_btn.disabled = self.mode == Mode.AUTO; self.update_step_btn()
    def step_sim(self):
        if self.mode == Mode.STEP and self.animator.state != AnimState.MOVING: self.do_step()
    def do_step(self):
        if not self.sim.is_running: return
        result = self.sim.step()
        if result is None: self.animator.finish(); self.start_btn.disabled = False
        else: frm, sym, to = result; self.animator.active_edge = (frm, to, sym); self.animator.start_transition(self.renderer.get_pos(frm), self.renderer.get_pos(to))
    def update(self, dt: float):
        self.animator.update(dt)
        if self.animator.state == AnimState.IDLE and self.sim.is_running and self.mode == Mode.AUTO: self.do_step()
        self.update_step_btn()
    def update_step_btn(self):
        if self.mode == Mode.STEP: self.step_btn.disabled = not (self.sim.is_running and self.animator.state != AnimState.MOVING)
    def render(self):
        self.renderer.clear()
        status = "Simulation Complete" if self.sim.is_finished else (f"Processing: {self.sim.input_string}" if self.sim.is_running else "Enter input string (0s and 1s)")
        self.renderer.draw_status(status); self.renderer.draw_transitions(self.dfa, self.animator.active_edge)
        for state in self.dfa.states:
            is_final, is_current, is_start = state in self.dfa.final_states, state == self.sim.current_state, state == self.dfa.start_state
            status_color, pulse_radius = None, None
            if is_current:
                if self.sim.is_finished: status_color = COLORS['accepted'] if self.sim.accepted else COLORS['rejected']
                else: status_color = COLORS['active']; pulse_radius = STATE_RADIUS * (1.0 + self.animator.pulse_amount)
            self.renderer.draw_state(state, is_final, is_current, is_start, pulse_radius, status_color)
        if self.animator.state == AnimState.MOVING: self.renderer.draw_token(self.animator.token_pos)
        if self.sim.is_running and self.sim.input_string:
            idx = min(self.sim.current_index, len(self.sim.input_string) - 1); self.renderer.draw_symbol(self.sim.input_string[idx], idx, len(self.sim.input_string))
        if self.animator.state == AnimState.FINISHED: self.renderer.draw_result(self.sim.accepted, self.animator.result_alpha)
        self.renderer.draw_input_box(self.input_box.rect, self.input_box.text, self.input_box.active)
        self.renderer.draw_button(self.start_btn.rect, self.start_btn.label, self.start_btn.hovered(pygame.mouse.get_pos()), self.start_btn.disabled)
        self.renderer.draw_button(self.reset_btn.rect, self.reset_btn.label, self.reset_btn.hovered(pygame.mouse.get_pos()))
        self.renderer.draw_button(self.mode_btn.rect, self.mode_btn.label, self.mode_btn.hovered(pygame.mouse.get_pos()))
        if self.mode == Mode.STEP: self.renderer.draw_button(self.step_btn.rect, self.step_btn.label, self.step_btn.hovered(pygame.mouse.get_pos()), self.step_btn.disabled)

if __name__ == "__main__": DFASimulator().run()
