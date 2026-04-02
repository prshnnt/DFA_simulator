"""Animation Module - Smooth token movement and visual effects."""

import pygame
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple


class AnimationState(Enum):
    """State machine for animation control."""
    IDLE = auto()
    MOVING = auto()
    PAUSE = auto()
    FINISHED = auto()


@dataclass
class TokenAnimation:
    """Animation data for the moving token."""
    start_pos: Tuple[float, float]
    end_pos: Tuple[float, float]
    current_pos: Tuple[float, float]
    progress: float = 0.0
    duration_ms: int = 600
    elapsed_ms: int = 0

    def reset(self, start: Tuple[float, float], end: Tuple[float, float]) -> None:
        """Reset animation with new positions."""
        self.start_pos = start
        self.end_pos = end
        self.current_pos = start
        self.progress = 0.0
        self.elapsed_ms = 0


@dataclass
class PulseAnimation:
    """Pulse animation for state highlighting."""
    base_radius: float
    current_radius: float
    pulse_speed: float = 0.003
    pulse_amount: float = 0.0
    direction: int = 1

    def update(self, dt: float) -> None:
        """Update pulse animation."""
        self.pulse_amount += self.pulse_speed * dt * self.direction
        if self.pulse_amount > 0.2:
            self.direction = -1
        elif self.pulse_amount < 0.0:
            self.direction = 1
        self.current_radius = self.base_radius * (1.0 + self.pulse_amount)


@dataclass
class FadeAnimation:
    """Fade-in animation for result display."""
    alpha: int = 0
    target_alpha: int = 255
    fade_speed: float = 0.005
    is_active: bool = False

    def start(self) -> None:
        """Start fade-in animation."""
        self.alpha = 0
        self.is_active = True

    def update(self, dt: float) -> None:
        """Update fade animation."""
        if self.is_active and self.alpha < self.target_alpha:
            self.alpha = min(self.target_alpha, self.alpha + int(self.fade_speed * dt))


class Animator:
    """Manages all animations in the DFA simulator."""

    def __init__(self):
        self.state = AnimationState.IDLE
        self.token = TokenAnimation((0, 0), (0, 0), (0, 0))
        self.current_pulse = PulseAnimation(30, 30)
        self.result_fade = FadeAnimation()
        self.transition_highlight: Optional[tuple] = None
        self.pause_duration_ms: int = 200
        self.pause_elapsed_ms: int = 0
        self.active_edge: Optional[tuple] = None  # (from_state, to_state, symbol)

    def start_transition(self, start_pos: Tuple[float, float],
                         end_pos: Tuple[float, float],
                         duration_ms: int = 600) -> None:
        """Start token movement animation."""
        self.token.reset(start_pos, end_pos)
        self.token.duration_ms = duration_ms
        self.state = AnimationState.MOVING

    def start_pause(self, duration_ms: int = 200) -> None:
        """Start pause between transitions."""
        self.pause_duration_ms = duration_ms
        self.pause_elapsed_ms = 0
        self.state = AnimationState.PAUSE

    def start_result_animation(self) -> None:
        """Start the result fade-in animation."""
        self.result_fade.start()

    def set_active_edge(self, edge: Optional[tuple]) -> None:
        """Set the currently highlighted transition edge."""
        self.active_edge = edge

    def update(self, dt: float) -> None:
        """Update all animations. dt is delta time in milliseconds."""
        if self.state == AnimationState.MOVING:
            self.token.elapsed_ms += dt
            self.token.progress = min(1.0, self.token.elapsed_ms / self.token.duration_ms)

            # Apply easing (ease-in-out cubic)
            eased = self._ease_in_out_cubic(self.token.progress)

            # Linear interpolation for position
            sx, sy = self.token.start_pos
            ex, ey = self.token.end_pos
            self.token.current_pos = (
                sx + (ex - sx) * eased,
                sy + (ey - sy) * eased
            )

            if self.token.progress >= 1.0:
                self.state = AnimationState.IDLE

        elif self.state == AnimationState.PAUSE:
            self.pause_elapsed_ms += dt
            if self.pause_elapsed_ms >= self.pause_duration_ms:
                self.state = AnimationState.IDLE

        elif self.state == AnimationState.FINISHED:
            self.result_fade.update(dt)

        # Always update pulse animation when active
        if self.state in (AnimationState.MOVING, AnimationState.IDLE):
            self.current_pulse.update(dt)

    def _ease_in_out_cubic(self, t: float) -> float:
        """Smooth easing function for natural motion."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

    def is_moving(self) -> bool:
        """Check if token is currently moving."""
        return self.state == AnimationState.MOVING

    def is_paused(self) -> bool:
        """Check if in pause state."""
        return self.state == AnimationState.PAUSE

    def is_finished(self) -> bool:
        """Check if animation is in finished state."""
        return self.state == AnimationState.FINISHED

    def finish_simulation(self) -> None:
        """Mark simulation as finished and start result animation."""
        self.state = AnimationState.FINISHED
        self.result_fade.start()

    def reset(self) -> None:
        """Reset all animations to initial state."""
        self.state = AnimationState.IDLE
        self.token.progress = 0.0
        self.token.elapsed_ms = 0
        self.active_edge = None
        self.result_fade.is_active = False
        self.result_fade.alpha = 0
