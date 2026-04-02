"""Renderer Module - Pygame drawing for DFA visualization."""

import pygame
import math
from typing import Dict, Tuple, Optional, List
from dfa_engine import DFA


class Renderer:
    """Handles all pygame rendering for the DFA simulator."""

    # Color palette
    COLOR_BG = (25, 25, 35)  # Dark blue-gray
    COLOR_STATE = (50, 50, 65)  # State circle background
    COLOR_STATE_BORDER = (150, 150, 170)  # State circle border
    COLOR_TEXT = (255, 255, 255)  # White text
    COLOR_TRANSITION = (100, 100, 120)  # Transition arrows
    COLOR_TRANSITION_HIGHLIGHT = (255, 220, 50)  # Yellow glow
    COLOR_TOKEN = (100, 180, 255)  # Blue token
    COLOR_ACTIVE = (50, 150, 255)  # Active state blue
    COLOR_ACCEPTED = (50, 220, 100)  # Green for acceptance
    COLOR_REJECTED = (255, 80, 80)  # Red for rejection
    COLOR_INPUT_BOX = (40, 40, 55)
    COLOR_INPUT_TEXT = (200, 200, 200)
    COLOR_BUTTON = (60, 60, 80)
    COLOR_BUTTON_HOVER = (80, 80, 100)

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.state_positions: Dict[str, Tuple[float, float]] = {}
        self.state_radius = 35

    def set_state_positions(self, positions: Dict[str, Tuple[float, float]]) -> None:
        """Set the positions for each state."""
        self.state_positions = positions

    def get_state_position(self, state: str) -> Tuple[float, float]:
        """Get the center position of a state."""
        return self.state_positions.get(state, (0, 0))

    def clear(self) -> None:
        """Clear the screen with background color."""
        self.screen.fill(self.COLOR_BG)

    def draw_state(self, state: str, is_final: bool = False,
                   is_current: bool = False, is_start: bool = False,
                   pulse_radius: Optional[float] = None,
                   status_color: Optional[Tuple[int, int, int]] = None) -> None:
        """Draw a DFA state circle."""
        pos = self.state_positions.get(state)
        if not pos:
            return

        x, y = pos
        radius = pulse_radius if pulse_radius else self.state_radius

        # Determine border color
        if is_current and status_color:
            border_color = status_color
        elif is_current:
            border_color = self.COLOR_ACTIVE
        else:
            border_color = self.COLOR_STATE_BORDER

        # Draw state circle
        pygame.draw.circle(self.screen, self.COLOR_STATE, (int(x), int(y)), int(radius))
        pygame.draw.circle(self.screen, border_color, (int(x), int(y)), int(radius), 3)

        # Draw double circle for final states
        if is_final:
            inner_radius = int(radius * 0.7)
            pygame.draw.circle(self.screen, border_color, (int(x), int(y)), inner_radius, 2)

        # Draw state label
        text = self.font_medium.render(state, True, self.COLOR_TEXT)
        text_rect = text.get_rect(center=(int(x), int(y)))
        self.screen.blit(text, text_rect)

        # Draw start arrow
        if is_start:
            self._draw_start_arrow((x, y))

    def draw_start_arrow(self, state: str) -> None:
        """Draw incoming arrow for start state."""
        pos = self.state_positions.get(state)
        if pos:
            self._draw_start_arrow(pos)

    def _draw_start_arrow(self, pos: Tuple[float, float]) -> None:
        """Draw incoming arrow for start state."""
        x, y = pos
        arrow_start = (x - self.state_radius * 2.5, y)
        arrow_end = (x - self.state_radius, y)
        self._draw_arrow(arrow_start, arrow_end, self.COLOR_STATE_BORDER)

    def draw_transition(self, from_state: str, to_state: str, symbol: str,
                        is_highlighted: bool = False) -> None:
        """Draw a transition arrow between states."""
        from_pos = self.state_positions.get(from_state)
        to_pos = self.state_positions.get(to_state)

        if not from_pos or not to_pos:
            return

        # Determine if self-loop
        if from_state == to_state:
            self._draw_self_loop(from_pos, symbol, is_highlighted)
        else:
            self._draw_curved_arrow(from_pos, to_pos, symbol, is_highlighted)

    def _draw_curved_arrow(self, start: Tuple[float, float], end: Tuple[float, float],
                           symbol: str, is_highlighted: bool = False) -> None:
        """Draw a curved arrow between two states."""
        color = self.COLOR_TRANSITION_HIGHLIGHT if is_highlighted else self.COLOR_TRANSITION
        width = 4 if is_highlighted else 2

        # Calculate positions
        sx, sy = start
        ex, ey = end

        # Normalize direction
        dx, dy = ex - sx, ey - sy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            return

        # Offset to stop at circle edge
        offset = self.state_radius
        start_pos = (sx + dx / dist * offset, sy + dy / dist * offset)
        end_pos = (ex - dx / dist * offset, ey - dy / dist * offset)

        # Create curved path
        mid_x = (start_pos[0] + end_pos[0]) / 2
        mid_y = (start_pos[1] + end_pos[1]) / 2

        # Perpendicular offset for curve
        curve_height = 30
        curve_x = mid_x - (ey - sy) / dist * curve_height
        curve_y = mid_y + (ex - sx) / dist * curve_height

        # Draw curve using quadratic bezier approximation
        points = self._quadratic_bezier(start_pos, (curve_x, curve_y), end_pos, 20)
        if len(points) > 1:
            pygame.draw.lines(self.screen, color, False, points, width)

        # Draw arrowhead
        self._draw_arrowhead(points[-2], points[-1], color)

        # Draw symbol label at midpoint
        label_pos = (curve_x, curve_y - 10)
        text = self.font_small.render(symbol, True, color)
        text_rect = text.get_rect(center=(int(label_pos[0]), int(label_pos[1])))
        self.screen.blit(text, text_rect)

    def _draw_self_loop(self, pos: Tuple[float, float], symbol: str,
                        is_highlighted: bool = False) -> None:
        """Draw a self-loop arrow on a state."""
        color = self.COLOR_TRANSITION_HIGHLIGHT if is_highlighted else self.COLOR_TRANSITION
        width = 4 if is_highlighted else 2

        x, y = pos
        loop_radius = self.state_radius * 1.4  # Larger loop for visibility
        center = (x, y - loop_radius * 0.7)  # Push center up for more arc

        # Draw loop arc - wider arc for better visibility
        start_angle = math.pi * 0.15
        end_angle = math.pi * 1.85
        points = []
        for angle in [start_angle + (end_angle - start_angle) * i / 20
                      for i in range(21)]:
            px = center[0] + loop_radius * math.cos(angle)
            py = center[1] + loop_radius * math.sin(angle)
            points.append((px, py))

        pygame.draw.lines(self.screen, color, False, points, width)

        # Draw arrowhead
        if len(points) > 1:
            self._draw_arrowhead(points[-2], points[-1], color)

        # Draw symbol - positioned above the loop
        text = self.font_small.render(symbol, True, color)
        text_rect = text.get_rect(center=(int(x), int(y - loop_radius * 1.8)))
        self.screen.blit(text, text_rect)

    def _quadratic_bezier(self, p0: Tuple[float, float], p1: Tuple[float, float],
                          p2: Tuple[float, float], steps: int) -> List[Tuple[float, float]]:
        """Generate points along a quadratic bezier curve."""
        points = []
        for i in range(steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
            points.append((x, y))
        return points

    def _draw_arrow(self, start: Tuple[float, float], end: Tuple[float, float],
                    color: Tuple[int, int, int]) -> None:
        """Draw a straight arrow."""
        pygame.draw.line(self.screen, color, start, end, 2)
        self._draw_arrowhead(start, end, color)

    def _draw_arrowhead(self, start: Tuple[float, float], end: Tuple[float, float],
                        color: Tuple[int, int, int]) -> None:
        """Draw an arrowhead at the end point."""
        sx, sy = start
        ex, ey = end

        # Calculate arrowhead points
        angle = math.atan2(ey - sy, ex - sx)
        arrow_length = 12
        arrow_angle = math.pi / 6

        p1 = (ex - arrow_length * math.cos(angle - arrow_angle),
              ey - arrow_length * math.sin(angle - arrow_angle))
        p2 = (ex - arrow_length * math.cos(angle + arrow_angle),
              ey - arrow_length * math.sin(angle + arrow_angle))

        pygame.draw.polygon(self.screen, color, [end, p1, p2])

    def draw_token(self, position: Tuple[float, float], radius: float = 12) -> None:
        """Draw the animated token (dot) at given position."""
        x, y = position

        # Outer glow
        pygame.draw.circle(self.screen, (80, 140, 200), (int(x), int(y)), int(radius + 4))

        # Main token
        pygame.draw.circle(self.screen, self.COLOR_TOKEN, (int(x), int(y)), int(radius))

        # Inner highlight
        pygame.draw.circle(self.screen, (200, 230, 255),
                          (int(x - radius * 0.3), int(y - radius * 0.3)), int(radius * 0.4))

    def draw_input_box(self, rect: pygame.Rect, text: str,
                       is_active: bool = False) -> None:
        """Draw the input text box."""
        color = self.COLOR_INPUT_BOX
        border_color = self.COLOR_ACTIVE if is_active else self.COLOR_STATE_BORDER

        # Background
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, border_color, rect, 2)

        # Text
        text_surface = self.font_medium.render(text, True, self.COLOR_INPUT_TEXT)
        text_rect = text_surface.get_rect(midleft=(rect.x + 10, rect.centery))
        self.screen.blit(text_surface, text_rect)

    def draw_button(self, rect: pygame.Rect, label: str,
                    is_hovered: bool = False, is_disabled: bool = False) -> None:
        """Draw a button with label."""
        if is_disabled:
            color = (40, 40, 50)
            text_color = (100, 100, 100)
        elif is_hovered:
            color = self.COLOR_BUTTON_HOVER
            text_color = self.COLOR_TEXT
        else:
            color = self.COLOR_BUTTON
            text_color = self.COLOR_TEXT

        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        pygame.draw.rect(self.screen, self.COLOR_STATE_BORDER, rect, 2, border_radius=5)

        text = self.font_medium.render(label, True, text_color)
        text_rect = text.get_rect(center=rect.center)
        self.screen.blit(text, text_rect)

    def draw_status(self, text: str, color: Optional[Tuple[int, int, int]] = None,
                    alpha: int = 255) -> None:
        """Draw status text at top of screen."""
        if color is None:
            color = self.COLOR_TEXT

        text_surface = self.font_large.render(text, True, color)
        text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, 25))

        if alpha < 255:
            text_surface.set_alpha(alpha)

        self.screen.blit(text_surface, text_rect)

    def draw_result(self, accepted: bool, alpha: int = 255) -> None:
        """Draw the result display (Accepted/Rejected) at top center."""
        if accepted:
            text = "ACCEPTED"
            color = self.COLOR_ACCEPTED
        else:
            text = "REJECTED"
            color = self.COLOR_REJECTED

        text_surface = self.font_large.render(text, True, color)
        text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, 60))

        if alpha < 255:
            text_surface.set_alpha(alpha)

        self.screen.blit(text_surface, text_rect)

    def draw_current_symbol(self, symbol: str, index: int, total: int) -> None:
        """Display current input symbol being processed at top right."""
        text = f"Symbol: '{symbol}' ({index + 1}/{total})"
        text_surface = self.font_medium.render(text, True, self.COLOR_TEXT)
        text_rect = text_surface.get_rect(right=self.screen.get_width() - 20, top=15)
        self.screen.blit(text_surface, text_rect)

    def draw_all_transitions(self, dfa: DFA,
                             highlighted_edge: Optional[tuple] = None) -> None:
        """Draw all transitions for the DFA."""
        for (from_state, symbol), to_state in dfa.transitions.items():
            is_highlighted = (highlighted_edge and
                              highlighted_edge[0] == from_state and
                              highlighted_edge[2] == to_state)
            self.draw_transition(from_state, to_state, symbol, is_highlighted)
