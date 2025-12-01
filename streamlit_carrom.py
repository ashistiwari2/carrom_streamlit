# """
# Streamlit launcher for the Pygame "Carrom: Algebraic (Striker)" game.

# How this works
# - This single-file Streamlit app embeds the full pygame game source as
#   a string and writes it to a temporary file when you press Play.
# - It then launches the game as a separate Python subprocess. The pygame
#   window will open on the machine running the Streamlit server (usually
#   your local computer when developing).
# - You can Stop the running game which will terminate the subprocess.

# Run:
#     pip install streamlit pygame
#     streamlit run carrom_streamlit_app.py

# Note:
# - The game runs as a regular pygame window; it is not rendered inside the
#   browser. This approach is the simplest way to "play" the existing
#   pygame code from a Streamlit UI.
# """

# import streamlit as st
# import subprocess
# import sys
# import tempfile
# import os
# import threading
# import time

# # ========== The full pygame game source (kept as a raw string) ==========
# # The original game script is embedded below. When Play is pressed the
# # app writes this to a temp file and runs it with the same Python
# # interpreter used for Streamlit (sys.executable).
# GAME_SCRIPT = r"""
# import pygame
# import random
# import math
# import sys
# import time

# # ---------- Base configuration ----------
# BASE_BOARD_W, BASE_BOARD_H = 1000, 700
# BASE_LEFT_PANEL_W = 260
# BASE_PIECE_R = 18
# BASE_STRIKER_R = 20
# BASE_POCKET_R = 36
# BASE_BOARD_PADDING = 80
# FRICTION = 0.9945
# MIN_VEL = 0.05
# MAX_STRIKE_POWER = 20.0
# FONT_NAME = None

# # Derived globals (set in main)
# BOARD_W = BASE_BOARD_W
# BOARD_H = BASE_BOARD_H
# LEFT_PANEL_W = BASE_LEFT_PANEL_W
# PIECE_RADIUS = BASE_PIECE_R
# STRIKER_RADIUS = BASE_STRIKER_R
# POCKET_RADIUS = BASE_POCKET_R
# BOARD_PADDING = BASE_BOARD_PADDING

# # ---------- Helpers ----------
# def clamp(v, a, b):
#     return max(a, min(b, v))

# def dist(a, b):
#     return math.hypot(a[0]-b[0], a[1]-b[1])

# def resolve_collision(a_pos, a_vel, a_mass, b_pos, b_vel, b_mass):
#     dx = b_pos[0] - a_pos[0]
#     dy = b_pos[1] - a_pos[1]
#     d = math.hypot(dx, dy)
#     if d == 0:
#         jitter = 1e-3
#         return [a_vel[0]+jitter, a_vel[1]], [b_vel[0]-jitter, b_vel[1]]
#     nx = dx / d
#     ny = dy / d
#     rvx = a_vel[0] - b_vel[0]
#     rvy = a_vel[1] - b_vel[1]
#     vel_along = rvx * nx + rvy * ny
#     if vel_along > 0:
#         return [a_vel[0], a_vel[1]], [b_vel[0], b_vel[1]]
#     e = 0.92
#     j = -(1 + e) * vel_along
#     j /= (1 / a_mass) + (1 / b_mass)
#     ix = j * nx
#     iy = j * ny
#     new_a_vx = a_vel[0] + ix / a_mass
#     new_a_vy = a_vel[1] + iy / a_mass
#     new_b_vx = b_vel[0] - ix / b_mass
#     new_b_vy = b_vel[1] - iy / b_mass
#     separation_impulse = 0.06
#     new_a_vx += -nx * separation_impulse
#     new_a_vy += -ny * separation_impulse
#     new_b_vx += nx * separation_impulse
#     new_b_vy += ny * separation_impulse
#     return [new_a_vx, new_a_vy], [new_b_vx, new_b_vy]

# # ---------- Expression generator ----------
# def make_piece_expr(x, forced_value=None):
#     if forced_value is None:
#         choice = random.choice(['x2+c', 'x2', 'x+c', 'const', 'minus'])
#         if choice == 'x2+c':
#             c = random.randint(-5, 10)
#             display = f"x² + {c}"
#             value = x * x + c
#         elif choice == 'x2':
#             display = "x²"
#             value = x * x
#         elif choice == 'x+c':
#             c = random.randint(-10, 20)
#             display = f"x + {c}"
#             value = x + c
#         elif choice == 'minus':
#             c = random.randint(-20, -10)
#             display = f"{-c}"
#             value = -c
#         else:
#             const = random.randint(0, 15)
#             display = f"{const}"
#             value = const
#         return display, value

#     fv = int(forced_value)
#     c = fv - (x * x)
#     if -12 <= c <= 20:
#         display = f"x² + {c}" if c != 0 else "x²"
#         return display, fv
#     c = fv - x
#     if -30 <= c <= 30:
#         display = f"x + {c}" if c != 0 else "x"
#         return display, fv
#     return f"{fv}", fv

# # ---------- Ball & Striker ----------
# class Ball:
#     def __init__(self, id_, color, expr, value, pos, radius=None, mass=1.0):
#         self.id = id_
#         self.color = color
#         self.expr = expr
#         self.value = int(value)
#         self.pos = [float(pos[0]), float(pos[1])]
#         self.vel = [0.0, 0.0]
#         self.radius = radius if radius is not None else PIECE_RADIUS
#         self.mass = mass
#         self.pocketed = False
#         self.scored = False

#     def update(self):
#         if self.pocketed:
#             return
#         self.pos[0] += self.vel[0]
#         self.pos[1] += self.vel[1]
#         self.vel[0] *= FRICTION
#         self.vel[1] *= FRICTION
#         if abs(self.vel[0]) < MIN_VEL:
#             self.vel[0] = 0.0
#         if abs(self.vel[1]) < MIN_VEL:
#             self.vel[1] = 0.0
#         minx = LEFT_PANEL_W + BOARD_PADDING + self.radius
#         maxx = LEFT_PANEL_W + BOARD_W - BOARD_PADDING - self.radius
#         miny = BOARD_PADDING + self.radius
#         maxy = BOARD_H - BOARD_PADDING - self.radius
#         if self.pos[0] < minx:
#             self.pos[0] = minx
#             self.vel[0] *= -0.6
#         if self.pos[0] > maxx:
#             self.pos[0] = maxx
#             self.vel[0] *= -0.6
#         if self.pos[1] < miny:
#             self.pos[1] = miny
#             self.vel[1] *= -0.6
#         if self.pos[1] > maxy:
#             self.pos[1] = maxy
#             self.vel[1] *= -0.6

#     def is_moving(self):
#         return (abs(self.vel[0]) > 0) or (abs(self.vel[1]) > 0)

#     def draw(self, surf, font):
#         if self.pocketed:
#             return
#         if self.color == 'red':
#             bg = (200, 40, 40); fg = (255, 230, 230)
#         else:
#             bg = (30, 30, 30); fg = (230, 230, 230)
#         pygame.draw.circle(surf, bg, (int(self.pos[0]), int(self.pos[1])), self.radius)
#         pygame.draw.circle(surf, (180, 180, 180), (int(self.pos[0]), int(self.pos[1])), self.radius, 2)
#         short = self.expr if len(self.expr) <= 12 else self.expr[:12] + '...'
#         lbl = font.render(short, True, fg)
#         surf.blit(lbl, (self.pos[0] - lbl.get_width()/2, self.pos[1] - lbl.get_height()/2))

# class Striker(Ball):
#     def __init__(self, pos):
#         super().__init__('S', 'striker', 'striker', 0, pos, radius=STRIKER_RADIUS, mass=1.6)
#         self.ready = True

#     def draw(self, surf, font):
#         if self.pocketed:
#             return
#         bg = (240, 240, 240); fg = (10, 10, 10)
#         pygame.draw.circle(surf, bg, (int(self.pos[0]), int(self.pos[1])), self.radius)
#         pygame.draw.circle(surf, (120, 120, 120), (int(self.pos[0]), int(self.pos[1])), self.radius, 2)

# # ---------- Confetti ----------
# class Confetti:
#     def __init__(self, x, y, vx, vy, color, lifetime=2.0):
#         self.x = x; self.y = y
#         self.vx = vx; self.vy = vy
#         self.color = color
#         self.lifetime = lifetime
#         self.age = 0.0
#         self.size = random.randint(3,7)
#     def update(self, dt):
#         self.age += dt
#         self.x += self.vx
#         self.y += self.vy
#         self.vy += 0.15
#         self.vx *= 0.998
#         self.vy *= 0.998
#     def draw(self, surf):
#         if self.age < self.lifetime:
#             alpha = int(255 * (1 - (self.age / self.lifetime)))
#             s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
#             s.fill((*self.color, alpha))
#             surf.blit(s, (int(self.x), int(self.y)))

# # ---------- Utility to craft piece values ----------
# def make_values_with_target(total_pieces, target_y):
#     if total_pieces <= 0:
#         return []
#     pieces = []
#     if target_y <= 0:
#         for _ in range(total_pieces):
#             pieces.append(random.randint(1, 8))
#         return pieces
#     max_k = min(6, total_pieces, max(2, target_y))
#     k = random.randint(2, max_k)
#     if k >= target_y:
#         parts = [1] * target_y
#         parts = parts[:k]
#         while sum(parts) < target_y:
#             parts[-1] += 1
#     else:
#         cuts = sorted(random.sample(range(1, target_y), k-1))
#         parts = []
#         prev = 0
#         for c in cuts:
#             parts.append(c - prev)
#             prev = c
#         parts.append(target_y - prev)
#     pieces.extend(parts)
#     while len(pieces) < total_pieces:
#         pieces.append(random.randint(1, 8))
#     pieces = [max(1, int(p)) for p in pieces[:total_pieces]]
#     random.shuffle(pieces)
#     return pieces

# # ---------- Game ----------
# class Game:
#     def __init__(self, screen, clock, font):
#         self.screen = screen
#         self.clock = clock
#         self.font = font
#         self.reset()

#     def reset(self):
#         try:
#             #s = input('Enter integer x (blank for random 1-6): ').strip()
#             self.x = random.randint(1, 6) 
#             #if s == '' else int(s)
#         except Exception:
#             self.x = random.randint(1, 6)
#         try:
#             #s = input('Enter target y (blank for random 30-120): ').strip()
#             self.y = random.randint(30, 120) 
#             #if s == '' else int(s)
#         except Exception:
#             self.y = random.randint(30, 120)
#         try:
#             #s = input('Player 1 name (blank -> Player 1): ').strip()
#             self.p1 = s or 'Player 1'
#             #s = input('Player 2 name (blank -> Player 2): ').strip()
#             self.p2 = s or 'Player 2'
#         except Exception:
#             self.p1, self.p2 = 'Player 1', 'Player 2'

#         self.message = f'Left-drag to position striker; Right-drag to aim & shoot. x={self.x} target={self.y} (R reset)'

#         # pieces (19 black pieces + 1 queen)
#         self.balls = []
#         center_x = LEFT_PANEL_W + BOARD_W//2
#         center_y = BOARD_H//2

#         black_count = 19
#         black_values = make_values_with_target(black_count, self.y)

#         for i in range(black_count):
#             forced_val = black_values[i]
#             display_expr, val = make_piece_expr(self.x, forced_value=forced_val)
#             pos = (center_x + random.randint(-70, 70), center_y + random.randint(-70, 70))
#             b = Ball(display_expr, 'black', display_expr, val, pos, radius=int(max(10, PIECE_RADIUS * 0.95)))
#             self.balls.append(b)

#         display_q = ""
#         queen = Ball(display_q, 'red', display_q, 0, (center_x + random.randint(-30, 30), center_y + random.randint(-30, 30)), radius=int(max(10, PIECE_RADIUS * 0.98)))
#         self.balls.append(queen)

#         self.pockets = [
#             (LEFT_PANEL_W + BOARD_PADDING, BOARD_PADDING),
#             (LEFT_PANEL_W + BOARD_W - BOARD_PADDING, BOARD_PADDING),
#             (LEFT_PANEL_W + BOARD_PADDING, BOARD_H - BOARD_PADDING),
#             (LEFT_PANEL_W + BOARD_W - BOARD_PADDING, BOARD_H - BOARD_PADDING)
#         ]

#         striker_x = LEFT_PANEL_W + BOARD_W//2
#         striker_y = BOARD_H - BOARD_PADDING - 40
#         self.striker = Striker((striker_x, striker_y))
#         self.striker.radius = int(max(12, STRIKER_RADIUS * 1.0))
#         self.striker.pos = [striker_x, striker_y]
#         self.striker.vel = [0.0, 0.0]
#         self.striker.ready = True

#         self.current = 0
#         self.scores = [0, 0]
#         self.winner = None

#         self.queen_holder = None
#         self.queen_pending = False

#         self.pocketed_this_shot = []
#         self.shot_active = False
#         self.turn_shot_taken = False

#         self.awaiting_cover_bonus = False
#         self.cover_candidate_ball = None
#         self.cover_candidate_player = None

#         self.repositioning = False
#         self.aiming = False
#         self.aim_now = (0,0)
#         self.aim_start = (0,0)

#         self.confetti = []
#         self.win_anim_start = None

#     def all_stopped(self):
#         if self.striker.is_moving():
#             return False
#         for b in self.balls:
#             if not b.pocketed and b.is_moving():
#                 return False
#         return True

#     def current_player_name(self):
#         return self.p1 if self.current == 0 else self.p2

#     def find_queen_ball(self):
#         for b in self.balls:
#             if b.color == 'red':
#                 return b
#         return None

#     def respawn_queen_to_center(self):
#         q = self.find_queen_ball()
#         if not q:
#             return
#         q.pocketed = False
#         q.scored = False
#         center_x = LEFT_PANEL_W + BOARD_W//2
#         center_y = BOARD_H//2
#         q.pos = [center_x + random.randint(-30,30), center_y + random.randint(-30,30)]
#         q.vel = [0.0, 0.0]

#     # New: reset only a specific player's score if they exceed the target
#     def _reset_player_if_over_target(self, player):
#         if self.scores[player] > self.y:
#             name = self.p1 if player == 0 else self.p2
#             self.scores[player] = 0
#             self.message = f"{name} exceeded the target {self.y}; their score was reset to 0."
#             # brief feedback pause (non-blocking visual), keep game running
#             pygame.display.flip()
#             time.sleep(0.45)
#             # do not reset pieces or other player's score

#     # ---- Input handlers ----
#     def handle_mouse_down(self, pos, button):
#         if self.winner or self.awaiting_cover_bonus:
#             return
#         mx, my = pos
#         if not self.striker.ready or not self.all_stopped():
#             return
#         if dist((mx, my), self.striker.pos) <= self.striker.radius + 8:
#             if button == 1:
#                 self.repositioning = True
#             elif button == 3:
#                 self.aiming = True
#                 self.aim_start = (mx, my)
#                 self.aim_now = (mx, my)

#     def handle_mouse_up(self, pos, button):
#         if button == 1 and self.repositioning:
#             self.repositioning = False
#             return
#         shift_and_left = (button == 1) and (pygame.key.get_mods() & pygame.KMOD_SHIFT)
#         if (button == 3 and self.aiming) or (shift_and_left and self.aiming):
#             sx, sy = self.striker.pos
#             ax, ay = self.aim_now
#             dx = ax - sx
#             dy = ay - sy
#             mag = math.hypot(dx, dy)
#             self.aiming = False
#             if mag == 0:
#                 return
#             power = mag / 8.0
#             power = clamp(power, 0, MAX_STRIKE_POWER)
#             nx = dx / mag
#             ny = dy / mag
#             if power > 0.05:
#                 self.striker.vel[0] = nx * power
#                 self.striker.vel[1] = ny * power
#                 self.striker.ready = False
#                 self.turn_shot_taken = True
#                 self.pocketed_this_shot = []
#                 self.shot_active = True
#                 self.message = f'{self.current_player_name()} struck (power {power:.1f})'

#     def handle_mouse_motion(self, pos):
#         mx, my = pos
#         if self.repositioning:
#             left_limit = LEFT_PANEL_W + BOARD_PADDING + self.striker.radius
#             right_limit = LEFT_PANEL_W + BOARD_W - BOARD_PADDING - self.striker.radius
#             self.striker.pos[0] = clamp(mx, left_limit, right_limit)
#             baseline_y = BOARD_H - BOARD_PADDING - 40
#             self.striker.pos[1] = baseline_y

#         right_pressed = pygame.mouse.get_pressed()[2]
#         shift_left_pressed = pygame.mouse.get_pressed()[0] and (pygame.key.get_mods() & pygame.KMOD_SHIFT)
#         if (right_pressed or shift_left_pressed):
#             if not self.aiming and dist((mx, my), self.striker.pos) <= self.striker.radius + 40 and self.striker.ready and self.all_stopped():
#                 self.aiming = True
#                 self.aim_start = (mx, my)
#                 self.aim_now = (mx, my)
#         if self.aiming:
#             mx = clamp(mx, LEFT_PANEL_W + BOARD_PADDING, LEFT_PANEL_W + BOARD_W - BOARD_PADDING)
#             my = clamp(my, BOARD_PADDING, BOARD_H - BOARD_PADDING)
#             self.aim_now = (mx, my)

#     def update_physics(self):
#         for b in self.balls:
#             b.update()
#         self.striker.update()

#         objs = [b for b in self.balls if not b.pocketed]
#         for i in range(len(objs)):
#             a = objs[i]
#             for j in range(i+1, len(objs)):
#                 b = objs[j]
#                 dx = b.pos[0] - a.pos[0]
#                 dy = b.pos[1] - a.pos[1]
#                 d = math.hypot(dx, dy)
#                 if d == 0:
#                     continue
#                 overlap = a.radius + b.radius - d
#                 if overlap > 0:
#                     nx = dx / d
#                     ny = dy / d
#                     push = overlap + 0.8
#                     a.pos[0] -= nx * (push * (b.mass / (a.mass + b.mass)))
#                     a.pos[1] -= ny * (push * (b.mass / (a.mass + b.mass)))
#                     b.pos[0] += nx * (push * (a.mass / (a.mass + b.mass)))
#                     b.pos[1] += ny * (push * (a.mass / (a.mass + b.mass)))
#                     a_v_new, b_v_new = resolve_collision(a.pos, a.vel, a.mass, b.pos, b.vel, b.mass)
#                     a.vel = [a_v_new[0], a_v_new[1]]
#                     b.vel = [b_v_new[0], b_v_new[1]]

#         for b in [b for b in self.balls if not b.pocketed]:
#             dx = b.pos[0] - self.striker.pos[0]
#             dy = b.pos[1] - self.striker.pos[1]
#             d = math.hypot(dx, dy)
#             if d == 0:
#                 continue
#             overlap = b.radius + self.striker.radius - d
#             if overlap > 0:
#                 nx = dx / d
#                 ny = dy / d
#                 push = overlap + 0.9
#                 b.pos[0] += nx * (push * (self.striker.mass / (b.mass + self.striker.mass)))
#                 b.pos[1] += ny * (push * (self.striker.mass / (b.mass + self.striker.mass)))
#                 self.striker.pos[0] -= nx * (push * (b.mass / (b.mass + self.striker.mass)))
#                 self.striker.pos[1] -= ny * (push * (b.mass / (b.mass + self.striker.mass)))
#                 sv, bv = resolve_collision(self.striker.pos, self.striker.vel, self.striker.mass, b.pos, b.vel, b.mass)
#                 self.striker.vel = [sv[0], sv[1]]
#                 b.vel = [bv[0], bv[1]]

#         for b in self.balls:
#             if b.pocketed:
#                 continue
#             for pk in self.pockets:
#                 if dist(b.pos, pk) <= POCKET_RADIUS:
#                     b.pocketed = True
#                     b.vel = [0.0, 0.0]
#                     if self.shot_active:
#                         self.pocketed_this_shot.append(b)

#         for pk in self.pockets:
#             if dist(self.striker.pos, pk) <= POCKET_RADIUS:
#                 if not self.striker.pocketed:
#                     self.striker.pocketed = True
#                     self.striker.vel = [0.0, 0.0]

#     def process_scoring(self):
#         for b in self.pocketed_this_shot:
#             if b.color == 'red' and self.queen_holder is None:
#                 self.queen_holder = self.current
#                 self.queen_pending = True
#                 b.scored = True
#                 self.message = f"{self.current_player_name()} pocketed QUEEN (must cover during possession)."

#         if self.queen_pending and self.queen_holder == self.current:
#             for b in self.pocketed_this_shot:
#                 if b.color == 'black' and not b.scored:
#                     self.cover_candidate_ball = b
#                     self.cover_candidate_player = self.current
#                     self.awaiting_cover_bonus = True
#                     max_bonus = max(1, b.value - 1)
#                     self.message = (f"{self.current_player_name()} pocketed {b.id} (value {b.value}). "
#                                     f"Choose bonus 1..{max_bonus} to cover QUEEN (press 1..).")
#                     return

#     def resolve_shot_results(self):
#         if not self.shot_active:
#             return
#         player = self.current
#         any_piece_pocketed = any(b for b in self.pocketed_this_shot if b.color in ('black','red'))

#         if self.striker.pocketed and any_piece_pocketed:
#             total_values = sum(b.value for b in self.pocketed_this_shot if b.color == 'black')
#             self.scores[player] += total_values
#             self.scores[player] -= 5
#             for b in self.pocketed_this_shot:
#                 b.scored = True
#             self.message = f"Foul: striker+pieces. +{total_values} and -5. Total={self.scores[player]}"
#             if self.queen_pending and self.queen_holder == player:
#                 self.respawn_queen_to_center()
#                 self.queen_holder = None
#                 self.queen_pending = False
#             # reset only offending player's score if it exceeded target
#             self._reset_player_if_over_target(player)
#             if self.scores[0] <= self.y and self.scores[1] <= self.y:
#                 self.end_turn_after_shot()
#             return

#         if self.striker.pocketed and not any_piece_pocketed:
#             self.scores[player] -= 5
#             self.message = f"Foul: striker pocketed. -5. Total={self.scores[player]}"
#             if self.queen_pending and self.queen_holder == player:
#                 self.respawn_queen_to_center()
#                 self.queen_holder = None
#                 self.queen_pending = False
#             self._reset_player_if_over_target(player)
#             if self.scores[0] <= self.y and self.scores[1] <= self.y:
#                 self.end_turn_after_shot()
#             return

#         if any_piece_pocketed and not self.striker.pocketed:
#             awarded = 0
#             for b in self.pocketed_this_shot:
#                 if b.color == 'black' and not b.scored:
#                     b.scored = True
#                     self.scores[player] += b.value
#                     awarded += b.value
#             self.message = f"{self.current_player_name()} pocketed pieces -> +{awarded}. Total={self.scores[player]}"
#             self._reset_player_if_over_target(player)
#             if self.scores[player] > self.y:
#                 # player's own score was reset; do not continue as continuing shot for award
#                 return
#             self.shot_active = False
#             self.pocketed_this_shot = []
#             self.turn_shot_taken = False
#             self.striker.ready = not self.striker.pocketed
#             return

#         if (not any_piece_pocketed) and (not self.striker.pocketed):
#             if self.queen_pending and self.queen_holder == player:
#                 self.respawn_queen_to_center()
#                 self.queen_holder = None
#                 self.queen_pending = False
#                 self.message = f"{self.current_player_name()} missed; QUEEN returned to board."
#             else:
#                 self.message = f"{self.current_player_name()} missed."
#             self.end_turn_after_shot()
#             return

#         self.shot_active = False
#         self.pocketed_this_shot = []
#         self.turn_shot_taken = False
#         self.striker.ready = not self.striker.pocketed

#     def end_turn_after_shot(self):
#         self.shot_active = False
#         self.pocketed_this_shot = []
#         self.turn_shot_taken = False
#         self.current = 1 - self.current
#         self.striker.pocketed = False
#         self.striker.pos = [LEFT_PANEL_W + BOARD_W//2, BOARD_H - BOARD_PADDING - 40]
#         self.striker.vel = [0.0, 0.0]
#         self.striker.ready = True
#         self.message += f"  Turn: {self.current_player_name()}"

#     def choose_cover_bonus(self, key):
#         if not self.awaiting_cover_bonus or self.cover_candidate_ball is None:
#             return
#         map_keys = {pygame.K_1:1, pygame.K_2:2, pygame.K_3:3, pygame.K_4:4, pygame.K_5:5,
#                     pygame.K_6:6, pygame.K_7:7, pygame.K_8:8, pygame.K_9:9}
#         if key not in map_keys:
#             return
#         chosen = map_keys[key]
#         b = self.cover_candidate_ball
#         max_bonus = max(1, b.value - 1)
#         if chosen < 1 or chosen > max_bonus:
#             self.message = f"Invalid choice. Choose 1..{max_bonus}."
#             return
#         player = self.cover_candidate_player
#         total_award = b.value + chosen
#         b.scored = True
#         self.queen_pending = False
#         self.queen_holder = None
#         self.awaiting_cover_bonus = False
#         self.cover_candidate_ball = None
#         self.cover_candidate_player = None
#         self.scores[player] += total_award
#         self.message = f"{self.p1 if player==0 else self.p2} covered QUEEN: +{b.value} + bonus {chosen} => +{total_award}. Total={self.scores[player]}"
#         self._reset_player_if_over_target(player)

#     def start_win_animation(self, winner_name):
#         self.win_anim_start = time.time()
#         cx = LEFT_PANEL_W + BOARD_W//2
#         cy = BOARD_H//3
#         colors = [(255,80,80), (80,200,120), (80,160,255), (255,220,80)]
#         for _ in range(140):
#             angle = random.random() * math.pi * 2
#             speed = random.uniform(1.5, 6.5)
#             vx = math.cos(angle) * speed
#             vy = math.sin(angle) * speed - 2.0
#             color = random.choice(colors)
#             self.confetti.append(Confetti(cx + random.randint(-20,20), cy + random.randint(-10,10), vx, vy, color, lifetime=3.0))

#     def update_win_animation(self):
#         dt = self.clock.get_time() / 1000.0
#         for c in self.confetti:
#             c.update(dt)
#         self.confetti = [c for c in self.confetti if c.age < c.lifetime]

#     def update(self):
#         if self.winner:
#             self.update_win_animation()
#             return
#         self.update_physics()
#         self.process_scoring()
#         if self.awaiting_cover_bonus:
#             return
#         if self.shot_active and self.all_stopped():
#             self.resolve_shot_results()
#         if self.striker.pocketed and self.all_stopped() and not self.shot_active:
#             self.scores[self.current] -= 5
#             self.message = f"Foul: striker pocketed outside shot. -5. Turn switches."
#             self._reset_player_if_over_target(self.current)
#             if self.scores[0] <= self.y and self.scores[1] <= self.y:
#                 self.end_turn_after_shot()
#         if all(b.pocketed or b.scored for b in self.balls) and not self.winner and not self.awaiting_cover_bonus:
#             d0 = abs(self.scores[0] - self.y)
#             d1 = abs(self.scores[1] - self.y)
#             if d0 < d1:
#                 self.winner = 0
#             elif d1 < d0:
#                 self.winner = 1
#             else:
#                 if self.scores[0] > self.scores[1]:
#                     self.winner = 0
#                 elif self.scores[1] > self.scores[0]:
#                     self.winner = 1
#                 else:
#                     self.winner = None
#             if self.winner is not None:
#                 self.message = f"All pieces pocketed. {self.p1 if self.winner==0 else self.p2} is closest to {self.y} and wins."
#                 self.start_win_animation(self.p1 if self.winner==0 else self.p2)
#             else:
#                 self.message = "All pieces pocketed. It's a draw."

#     def draw_left_panel(self, surf):
#         pygame.draw.rect(surf, (18,18,18), (0, 0, LEFT_PANEL_W, BOARD_H))
#         title = pygame.font.SysFont(FONT_NAME, 22).render("Algebraic Carrom", True, (250,250,250))
#         surf.blit(title, (14, 10))
#         y = 44
#         fbig = pygame.font.SysFont(FONT_NAME, 18)
#         p1 = fbig.render(f"{self.p1}", True, (240,240,240))
#         s1 = fbig.render(f"{self.scores[0]}", True, (200,200,200))
#         surf.blit(p1, (14, y)); surf.blit(s1, (14, y+24))
#         y += 56
#         p2 = fbig.render(f"{self.p2}", True, (240,240,240))
#         s2 = fbig.render(f"{self.scores[1]}", True, (200,200,200))
#         surf.blit(p2, (14, y)); surf.blit(s2, (14, y+24))
#         y += 56
#         small = pygame.font.SysFont(FONT_NAME, 14)
#         surf.blit(small.render("Controls:", True, (220,220,180)), (14, y))
#         surf.blit(small.render("- Left-drag striker horizontally to place", True, (200,200,180)), (14, y+18))
#         surf.blit(small.render("- Right-drag from striker to aim & release to shoot", True, (200,200,180)), (14, y+36))
#         surf.blit(small.render("- Alternatively: hold Shift + left-drag to aim", True, (200,200,180)), (14, y+54))
#         y += 92
#         targ = small.render(f"Target y = {self.y}", True, (220,220,180))
#         xs = small.render(f"x = {self.x}", True, (220,220,180))
#         surf.blit(targ, (14, y)); surf.blit(xs, (14, y+18))
#         y += 46
#         turntxt = small.render(f"Turn: {self.current_player_name()}", True, (255,255,255))
#         surf.blit(turntxt, (14, y))
#         y += 30
#         qtxt = small.render("Queen:", True, (200,200,200))
#         surf.blit(qtxt, (14, y))
#         qstate = "None"
#         if self.queen_holder is not None and self.queen_pending:
#             qstate = f"held by {self.p1 if self.queen_holder==0 else self.p2}"
#         elif not self.queen_pending:
#             qstate = "free"
#         surf.blit(small.render(qstate, True, (220,220,180)), (14, y+18))
#         y += 48
#         msg_lines = wrap_text(self.message, 28)
#         for i, line in enumerate(msg_lines[:6]):
#             surf.blit(small.render(line, True, (200,200,180)), (14, y + i*16))

#     def draw(self):
#         s = self.screen
#         s.fill((50,150,90))
#         self.draw_left_panel(s)
#         board_x = LEFT_PANEL_W
#         pygame.draw.rect(s, (20,90,50), (board_x + BOARD_PADDING-20, BOARD_PADDING-20, BOARD_W - 2*(BOARD_PADDING-20), BOARD_H - 2*(BOARD_PADDING-20)))
#         for pk in self.pockets:
#             pygame.draw.circle(s, (10,10,10), (int(pk[0]), int(pk[1])), POCKET_RADIUS)
#         for b in self.balls:
#             b.draw(s, self.font)
#         self.striker.draw(s, self.font)
#         if self.aiming:
#             sx, sy = self.striker.pos
#             ax, ay = self.aim_now
#             pygame.draw.line(s, (255,255,255), (sx, sy), (ax, ay), 2)
#             power = math.hypot(sx-ax, sy-ay)/8.0
#             ptxt = self.font.render(f'Power {power:.1f}', True, (255,255,255))
#             s.blit(ptxt, (ax+10, ay+10))
#         if self.awaiting_cover_bonus and self.cover_candidate_ball is not None:
#             overlay = pygame.Surface((LEFT_PANEL_W + BOARD_W, BOARD_H), pygame.SRCALPHA)
#             overlay.fill((0,0,0,160))
#             s.blit(overlay, (0,0))
#             b = self.cover_candidate_ball
#             max_bonus = max(1, b.value - 1)
#             big = pygame.font.SysFont(FONT_NAME, 26).render(f"Choose bonus 1..{max_bonus} to cover QUEEN (press 1..)", True, (255,255,200))
#             s.blit(big, (LEFT_PANEL_W + BOARD_W//2 - big.get_width()//2, BOARD_H//2 - 20))
#         if self.winner is not None:
#             overlay = pygame.Surface((LEFT_PANEL_W + BOARD_W, BOARD_H), pygame.SRCALPHA)
#             overlay.fill((0,0,0,130))
#             s.blit(overlay, (0,0))
#             bigfont = pygame.font.SysFont(FONT_NAME, 48)
#             winner_name = self.p1 if self.winner==0 else self.p2
#             big = bigfont.render(f"Congratulations, {winner_name}!", True, (255,240,200))
#             s.blit(big, (LEFT_PANEL_W + BOARD_W//2 - big.get_width()//2, BOARD_H//3 - 40))
#             for c in self.confetti:
#                 c.draw(s)

#     def handle_key(self, key):
#         if key == pygame.K_r:
#             self.reset()
#         if self.awaiting_cover_bonus:
#             self.choose_cover_bonus(key)

# # ---------- Utility ----------
# def wrap_text(text, cols):
#     words = text.split()
#     lines = []
#     cur = ""
#     for w in words:
#         if len(cur) + len(w) + 1 > cols:
#             lines.append(cur)
#             cur = w
#         else:
#             cur = cur + (" " if cur else "") + w
#     if cur:
#         lines.append(cur)
#     return lines

# # ---------- main loop ----------
# def main():
#     global BOARD_W, BOARD_H, LEFT_PANEL_W, PIECE_RADIUS, STRIKER_RADIUS, POCKET_RADIUS, BOARD_PADDING

#     pygame.init()
#     info = pygame.display.Info()
#     screen_w, screen_h = info.current_w, info.current_h

#     max_board_w = min(1200, screen_w - 300)
#     max_board_h = min(800, screen_h - 200)
#     BOARD_W = min(BASE_BOARD_W, max_board_w)
#     BOARD_H = min(BASE_BOARD_H, max_board_h)
#     LEFT_PANEL_W = BASE_LEFT_PANEL_W

#     scale = BOARD_W / BASE_BOARD_W
#     PIECE_RADIUS = max(10, int(BASE_PIECE_R * scale * 1.05))
#     STRIKER_RADIUS = max(12, int(BASE_STRIKER_R * scale * 1.1))
#     POCKET_RADIUS = max(24, int(BASE_POCKET_R * scale * 1.15))
#     BOARD_PADDING = max(40, int(BASE_BOARD_PADDING * scale * 0.9))

#     total_w = LEFT_PANEL_W + BOARD_W
#     total_h = BOARD_H

#     screen = pygame.display.set_mode((total_w, total_h))
#     pygame.display.set_caption('Carrom: Algebraic (Striker) - full')

#     clock = pygame.time.Clock()
#     font = pygame.font.SysFont(FONT_NAME, max(14, int(18 * scale)))

#     game = Game(screen, clock, font)
#     running = True

#     while running:
#         for event in pygame.event.get():
#             if event.type == pygame.QUIT:
#                 running = False
#             elif event.type == pygame.MOUSEBUTTONDOWN:
#                 game.handle_mouse_down(event.pos, event.button)
#             elif event.type == pygame.MOUSEBUTTONUP:
#                 game.handle_mouse_up(event.pos, event.button)
#             elif event.type == pygame.MOUSEMOTION:
#                 game.handle_mouse_motion(event.pos)
#             elif event.type == pygame.KEYDOWN:
#                 if event.key == pygame.K_ESCAPE:
#                     running = False
#                 else:
#                     game.handle_key(event.key)

#         game.update()
#         game.draw()
#         pygame.display.flip()
#         clock.tick(60)

#         if game.winner is not None and game.win_anim_start is None:
#             game.start_win_animation(game.p1 if game.winner==0 else game.p2)

#     pygame.quit()
#     print('\nThanks for playing!')

# if __name__ == '__main__':
#     main()

# """

# # ---------------- Streamlit UI ----------------
# st.set_page_config(page_title="Carrom: Algebraic — Streamlit Launcher", layout="wide")
# st.title("Carrom: Algebraic — Streamlit launcher")

# with st.sidebar:
#     st.header("Game parameters")
#     x_input = st.text_input("x (integer, blank -> random 1-6)", value="")
#     y_input = st.text_input("target y (integer, blank -> random 30-120)", value="")
#     p1 = st.text_input("Player 1 name", value="Player 1")
#     p2 = st.text_input("Player 2 name", value="Player 2")
#     autosave_script = st.checkbox("Save generated game script to current directory", value=False)
#     st.markdown("---")
#     st.markdown("**Controls**: Left-drag to reposition striker; Right-drag to aim & shoot. Hold Shift + left-drag to aim. Press R to reset game.")

# # Session state for process handle and temp file path
# if 'game_proc' not in st.session_state:
#     st.session_state['game_proc'] = None
# if 'script_path' not in st.session_state:
#     st.session_state['script_path'] = None
# if 'log_path' not in st.session_state:
#     st.session_state['log_path'] = None

# col1, col2 = st.columns([1,1])

# with col1:
#     if st.button("Play"):
#         if st.session_state['game_proc'] is not None and st.session_state['game_proc'].poll() is None:
#             st.warning("Game already running. Stop it first if you want to restart with new parameters.")
#         else:
#             # Prepare script contents: insert parameter passing into the script
#             script_content = GAME_SCRIPT
#             # Simple substitution: write small header that sets defaults from args/env
#             header = f"""
# # Auto-generated header inserted by launcher
# import sys
# # allow passing x, y, p1, p2 via sys.argv
# try:
#     _x = '' if len(sys.argv) < 2 else sys.argv[1]
# except Exception:
#     _x = ''
# try:
#     _y = '' if len(sys.argv) < 3 else sys.argv[2]
# except Exception:
#     _y = ''
# try:
#     _p1 = 'Player 1' if len(sys.argv) < 4 else sys.argv[3]
# except Exception:
#     _p1 = 'Player 1'
# try:
#     _p2 = 'Player 2' if len(sys.argv) < 5 else sys.argv[4]
# except Exception:
#     _p2 = 'Player 2'
# # Make these available for the game script """
            
#             full_script = header + "\n" + script_content
            
#             # Write script to temp file
#             if autosave_script:
#                 target_path = os.path.abspath("carrom_pygame_temp.py")
#             else:
#                 fd, target_path = tempfile.mkstemp(prefix="carrom_", suffix=".py")
#                 os.close(fd)
#             with open(target_path, 'w', encoding='utf-8') as f:
#                 f.write(full_script)

#             st.session_state['script_path'] = target_path
#             # Optional log file
#             log_fd, log_path = tempfile.mkstemp(prefix="carrom_log_", suffix=".txt")
#             os.close(log_fd)
#             st.session_state['log_path'] = log_path

#             # Build argv
#             argv = [sys.executable, target_path]
#             if x_input.strip() != '':
#                 argv.append(x_input.strip())
#             if y_input.strip() != '':
#                 argv.append(y_input.strip())
#             argv.append(p1)
#             argv.append(p2)

#             # Start subprocess
#             try:
#                 logf = open(log_path, 'wb')
#                 proc = subprocess.Popen(argv, stdout=logf, stderr=subprocess.STDOUT)
#                 st.session_state['game_proc'] = proc
#                 st.success(f"Game started (PID {proc.pid}). A pygame window should open on the machine running Streamlit.")
#             except Exception as e:
#                 st.error(f"Failed to launch game: {e}")

# with col2:
#     if st.button("Stop"):
#         proc = st.session_state.get('game_proc')
#         if proc is None:
#             st.info("No game process found.")
#         else:
#             if proc.poll() is None:
#                 try:
#                     proc.terminate()
#                     time.sleep(0.2)
#                     if proc.poll() is None:
#                         proc.kill()
#                     st.session_state['game_proc'] = None
#                     st.success("Game process terminated.")
#                 except Exception as e:
#                     st.error(f"Error terminating process: {e}")
#             else:
#                 st.info("Game already exited.")

# st.markdown("---")

# # Status / logs
# proc = st.session_state.get('game_proc')
# if proc is None:
#     st.info("Game is not running.")
# else:
#     if proc.poll() is None:
#         st.success(f"Game running (PID {proc.pid})")
#     else:
#         st.warning(f"Game process exited with return code {proc.returncode}")

# if st.session_state.get('log_path'):
#     if st.button("Show latest logs"):
#         try:
#             with open(st.session_state['log_path'], 'r', encoding='utf-8', errors='ignore') as f:
#                 txt = f.read()[-20000:]
#             st.code(txt)
#         except Exception as e:
#             st.error(f"Could not read log file: {e}")

# st.markdown("---")
# st.caption("When you finish, press Stop and then close the pygame window. If you used autosave, a file named carrom_pygame_temp.py will be left in this directory.")

# # Small helper: if the Streamlit server is stopped/ restarted ensure child process is terminated.

# def _cleanup_child_processes():
#     proc = st.session_state.get('game_proc')
#     if proc is not None and proc.poll() is None:
#         try:
#             proc.terminate()
#             time.sleep(0.1)
#             if proc.poll() is None:
#                 proc.kill()
#         except Exception:
#             pass

# # Register cleanup on session end - best-effort
# # st.experimental_singleton.clear()
import streamlit as st
import random
import math
import time
from PIL import Image, ImageDraw, ImageFont

# ---------- Configuration ----------
BASE_BOARD_W, BASE_BOARD_H = 800, 560 # Slightly smaller for web view
BASE_LEFT_PANEL_W = 0 # Removing panel, moving info to sidebar
BASE_PIECE_R = 14
BASE_STRIKER_R = 18
BASE_POCKET_R = 30
BASE_BOARD_PADDING = 60
FRICTION = 0.99
MIN_VEL = 0.1
MAX_STRIKE_POWER = 20.0

# Scale factors for drawing
SCALE = 1.0 

# ---------- Logic Helpers (Unchanged Logic) ----------
def clamp(v, a, b):
    return max(a, min(b, v))

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def resolve_collision(a_pos, a_vel, a_mass, b_pos, b_vel, b_mass):
    dx = b_pos[0] - a_pos[0]
    dy = b_pos[1] - a_pos[1]
    d = math.hypot(dx, dy)
    if d == 0:
        jitter = 1e-3
        return [a_vel[0]+jitter, a_vel[1]], [b_vel[0]-jitter, b_vel[1]]
    nx = dx / d
    ny = dy / d
    rvx = a_vel[0] - b_vel[0]
    rvy = a_vel[1] - b_vel[1]
    vel_along = rvx * nx + rvy * ny
    if vel_along > 0:
        return [a_vel[0], a_vel[1]], [b_vel[0], b_vel[1]]
    e = 0.92
    j = -(1 + e) * vel_along
    j /= (1 / a_mass) + (1 / b_mass)
    ix = j * nx
    iy = j * ny
    new_a_vx = a_vel[0] + ix / a_mass
    new_a_vy = a_vel[1] + iy / a_mass
    new_b_vx = b_vel[0] - ix / b_mass
    new_b_vy = b_vel[1] - iy / b_mass
    separation_impulse = 0.06
    new_a_vx += -nx * separation_impulse
    new_a_vy += -ny * separation_impulse
    new_b_vx += nx * separation_impulse
    new_b_vy += ny * separation_impulse
    return [new_a_vx, new_a_vy], [new_b_vx, new_b_vy]

def make_piece_expr(x, forced_value=None):
    if forced_value is None:
        choice = random.choice(['x2+c', 'x2', 'x+c', 'const', 'minus'])
        if choice == 'x2+c':
            c = random.randint(-5, 10)
            display = f"x² + {c}"
            value = x * x + c
        elif choice == 'x2':
            display = "x²"
            value = x * x
        elif choice == 'x+c':
            c = random.randint(-10, 20)
            display = f"x + {c}"
            value = x + c
        elif choice == 'minus':
            c = random.randint(-20, -10)
            display = f"{-c}"
            value = -c
        else:
            const = random.randint(0, 15)
            display = f"{const}"
            value = const
        return display, value

    fv = int(forced_value)
    c = fv - (x * x)
    if -12 <= c <= 20:
        display = f"x² + {c}" if c != 0 else "x²"
        return display, fv
    c = fv - x
    if -30 <= c <= 30:
        display = f"x + {c}" if c != 0 else "x"
        return display, fv
    return f"{fv}", fv

def make_values_with_target(total_pieces, target_y):
    if total_pieces <= 0: return []
    pieces = []
    if target_y <= 0:
        return [random.randint(1, 8) for _ in range(total_pieces)]
    max_k = min(6, total_pieces, max(2, target_y))
    k = random.randint(2, max_k)
    if k >= target_y:
        parts = [1] * target_y
        parts = parts[:k]
        while sum(parts) < target_y: parts[-1] += 1
    else:
        cuts = sorted(random.sample(range(1, target_y), k-1))
        parts = []
        prev = 0
        for c in cuts:
            parts.append(c - prev)
            prev = c
        parts.append(target_y - prev)
    pieces.extend(parts)
    while len(pieces) < total_pieces:
        pieces.append(random.randint(1, 8))
    pieces = [max(1, int(p)) for p in pieces[:total_pieces]]
    random.shuffle(pieces)
    return pieces

# ---------- Classes (Logic Only, Drawing separate) ----------
class Ball:
    def __init__(self, id_, color, expr, value, pos, radius=None, mass=1.0):
        self.id = id_
        self.color = color
        self.expr = expr
        self.value = int(value)
        self.pos = [float(pos[0]), float(pos[1])]
        self.vel = [0.0, 0.0]
        self.radius = radius if radius is not None else BASE_PIECE_R
        self.mass = mass
        self.pocketed = False
        self.scored = False

    def update(self):
        if self.pocketed: return
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        self.vel[0] *= FRICTION
        self.vel[1] *= FRICTION
        if abs(self.vel[0]) < MIN_VEL: self.vel[0] = 0.0
        if abs(self.vel[1]) < MIN_VEL: self.vel[1] = 0.0
        
        # Bounds
        minx = BASE_BOARD_PADDING + self.radius
        maxx = BASE_BOARD_W - BASE_BOARD_PADDING - self.radius
        miny = BASE_BOARD_PADDING + self.radius
        maxy = BASE_BOARD_H - BASE_BOARD_PADDING - self.radius
        
        if self.pos[0] < minx:
            self.pos[0] = minx; self.vel[0] *= -0.6
        if self.pos[0] > maxx:
            self.pos[0] = maxx; self.vel[0] *= -0.6
        if self.pos[1] < miny:
            self.pos[1] = miny; self.vel[1] *= -0.6
        if self.pos[1] > maxy:
            self.pos[1] = maxy; self.vel[1] *= -0.6

    def is_moving(self):
        return (abs(self.vel[0]) > 0) or (abs(self.vel[1]) > 0)

class GameState:
    def __init__(self):
        self.balls = []
        self.pockets = []
        self.striker = None
        self.x = 0
        self.y = 0
        self.p1 = "Player 1"
        self.p2 = "Player 2"
        self.current = 0
        self.scores = [0, 0]
        self.winner = None
        self.message = "Welcome! Use controls to play."
        self.queen_holder = None
        self.queen_pending = False
        self.pocketed_this_shot = []
        self.awaiting_cover_bonus = False
        self.cover_candidate_ball = None
        self.cover_candidate_player = None
        
        # Initialize board
        self.pockets = [
            (BASE_BOARD_PADDING, BASE_BOARD_PADDING),
            (BASE_BOARD_W - BASE_BOARD_PADDING, BASE_BOARD_PADDING),
            (BASE_BOARD_PADDING, BASE_BOARD_H - BASE_BOARD_PADDING),
            (BASE_BOARD_W - BASE_BOARD_PADDING, BASE_BOARD_H - BASE_BOARD_PADDING)
        ]

    def setup_new_game(self, x_val, y_val, p1_name, p2_name):
        self.x = x_val
        self.y = y_val
        self.p1 = p1_name if p1_name else "Player 1"
        self.p2 = p2_name if p2_name else "Player 2"
        self.scores = [0, 0]
        self.current = 0
        self.winner = None
        self.balls = []
        
        center_x = BASE_BOARD_W // 2
        center_y = BASE_BOARD_H // 2
        
        black_count = 19
        black_values = make_values_with_target(black_count, self.y)
        
        for i in range(black_count):
            forced = black_values[i]
            disp, val = make_piece_expr(self.x, forced_value=forced)
            pos = (center_x + random.randint(-50, 50), center_y + random.randint(-50, 50))
            b = Ball(disp, 'black', disp, val, pos, radius=BASE_PIECE_R)
            self.balls.append(b)
            
        q = Ball("Q", 'red', "Q", 0, (center_x, center_y), radius=BASE_PIECE_R, mass=1.2)
        self.balls.append(q)
        
        self.striker = Ball("S", 'striker', "", 0, (center_x, BASE_BOARD_H - BASE_BOARD_PADDING - 40), 
                            radius=BASE_STRIKER_R, mass=1.6)
        self.reset_striker()

    def reset_striker(self):
        self.striker.pos = [BASE_BOARD_W // 2, BASE_BOARD_H - BASE_BOARD_PADDING - 40]
        self.striker.vel = [0, 0]
        self.striker.pocketed = False

    def all_stopped(self):
        if self.striker.is_moving(): return False
        for b in self.balls:
            if not b.pocketed and b.is_moving(): return False
        return True
    
    def update_physics(self):
        # Move everything
        self.striker.update()
        for b in self.balls: b.update()
        
        # Collisions: Ball-Ball
        objs = [b for b in self.balls if not b.pocketed]
        for i in range(len(objs)):
            a = objs[i]
            for j in range(i+1, len(objs)):
                b = objs[j]
                d = dist(a.pos, b.pos)
                if d == 0: continue
                overlap = a.radius + b.radius - d
                if overlap > 0:
                    dx = b.pos[0] - a.pos[0]; dy = b.pos[1] - a.pos[1]
                    nx = dx/d; ny = dy/d
                    push = overlap + 0.5
                    factor_a = b.mass / (a.mass + b.mass)
                    factor_b = a.mass / (a.mass + b.mass)
                    a.pos[0] -= nx * push * factor_a
                    a.pos[1] -= ny * push * factor_a
                    b.pos[0] += nx * push * factor_b
                    b.pos[1] += ny * push * factor_b
                    
                    av, bv = resolve_collision(a.pos, a.vel, a.mass, b.pos, b.vel, b.mass)
                    a.vel = list(av); b.vel = list(bv)

        # Collisions: Striker-Ball
        if not self.striker.pocketed:
            for b in objs:
                d = dist(self.striker.pos, b.pos)
                if d == 0: continue
                overlap = self.striker.radius + b.radius - d
                if overlap > 0:
                    dx = b.pos[0] - self.striker.pos[0]
                    dy = b.pos[1] - self.striker.pos[1]
                    nx = dx/d; ny = dy/d
                    push = overlap + 0.5
                    factor_s = b.mass / (self.striker.mass + b.mass)
                    factor_b = self.striker.mass / (self.striker.mass + b.mass)
                    
                    self.striker.pos[0] -= nx * push * factor_s
                    self.striker.pos[1] -= ny * push * factor_s
                    b.pos[0] += nx * push * factor_b
                    b.pos[1] += ny * push * factor_b
                    
                    sv, bv = resolve_collision(self.striker.pos, self.striker.vel, self.striker.mass, b.pos, b.vel, b.mass)
                    self.striker.vel = list(sv); b.vel = list(bv)

        # Pockets
        for b in self.balls:
            if not b.pocketed:
                for pk in self.pockets:
                    if dist(b.pos, pk) <= BASE_POCKET_R:
                        b.pocketed = True
                        b.vel = [0,0]
                        self.pocketed_this_shot.append(b)
        
        # Striker Pocket
        if not self.striker.pocketed:
            for pk in self.pockets:
                if dist(self.striker.pos, pk) <= BASE_POCKET_R:
                    self.striker.pocketed = True
                    self.striker.vel = [0,0]

    def current_player_name(self):
        return self.p1 if self.current == 0 else self.p2

    def _reset_player_if_over_target(self, player):
        if self.scores[player] > self.y:
            name = self.p1 if player == 0 else self.p2
            self.scores[player] = 0
            self.message = f"{name} exceeded target {self.y}. Score reset to 0."

    def find_queen(self):
        for b in self.balls:
            if b.color == 'red': return b
        return None

    def respawn_queen(self):
        q = self.find_queen()
        if q:
            q.pocketed = False
            q.scored = False
            q.pos = [BASE_BOARD_W//2 + random.randint(-10,10), BASE_BOARD_H//2 + random.randint(-10,10)]
            q.vel = [0,0]

    def resolve_turn(self):
        player = self.current
        any_pocketed = len(self.pocketed_this_shot) > 0
        
        # Check Queen Logic
        queen_in_shot = any(b.color == 'red' for b in self.pocketed_this_shot)
        black_in_shot = any(b.color == 'black' for b in self.pocketed_this_shot)

        # 1. Queen + Black together -> Immediate Points
        if queen_in_shot and black_in_shot:
            total_black = sum(b.value for b in self.pocketed_this_shot if b.color == 'black' and not b.scored)
            for b in self.pocketed_this_shot:
                if not b.scored: b.scored = True
            
            self.scores[player] += total_black + 2
            self.queen_pending = False
            self.queen_holder = None
            self.message = f"{self.current_player_name()} got Queen + Black! (+2 + {total_black})"
            self._reset_player_if_over_target(player)
            # Turn continues if not foul
            # But wait, did they foul striker?
            if self.striker.pocketed:
                 # Foul override
                 self.scores[player] -= 5
                 self.message += " ...but fouled Striker (-5)."
                 self.end_turn()
            return # Turn continues (hit piece)

        # 2. Striker Foul
        if self.striker.pocketed:
            total_val = sum(b.value for b in self.pocketed_this_shot if b.color == 'black' and not b.scored)
            for b in self.pocketed_this_shot: b.scored = True # Counted but effectively lost
            self.scores[player] += total_val
            self.scores[player] -= 5
            self.message = f"Foul! Striker pocketed. -5."
            if self.queen_pending and self.queen_holder == player:
                self.respawn_queen()
                self.queen_holder = None
                self.queen_pending = False
            self._reset_player_if_over_target(player)
            self.end_turn()
            return

        # 3. Queen Alone
        if queen_in_shot and not black_in_shot:
            if self.queen_holder is None:
                self.queen_holder = player
                self.queen_pending = True
                self.find_queen().scored = True
                self.message = f"{self.current_player_name()} got Queen. Must cover!"
                # Turn continues to try and cover
                return
        
        # 4. Pieces Pocketed (No Queen event)
        if any_pocketed:
            # If pending queen, check for cover
            if self.queen_pending and self.queen_holder == player:
                # We hit a black piece. Trigger Selection.
                candidates = [b for b in self.pocketed_this_shot if b.color=='black']
                if candidates:
                    self.cover_candidate_ball = candidates[0] # Just take first for simplicity in web ver
                    self.cover_candidate_player = player
                    self.awaiting_cover_bonus = True
                    self.message = f"Covering Queen! Select Bonus for piece val {self.cover_candidate_ball.value}"
                    return
            
            # Normal scoring
            total = sum(b.value for b in self.pocketed_this_shot if b.color == 'black' and not b.scored)
            for b in self.pocketed_this_shot: b.scored = True
            self.scores[player] += total
            self.message = f"{self.current_player_name()} scored +{total}."
            self._reset_player_if_over_target(player)
            # Turn continues
            return

        # 5. Missed everything
        if not any_pocketed:
            if self.queen_pending and self.queen_holder == player:
                self.respawn_queen()
                self.queen_holder = None
                self.queen_pending = False
                self.message = "Missed cover. Queen returned."
            else:
                self.message = "Missed."
            self.end_turn()

    def end_turn(self):
        self.current = 1 - self.current
        self.message += f" Turn: {self.current_player_name()}"
        self.reset_striker()

    def finalize_cover(self, bonus):
        b = self.cover_candidate_ball
        player = self.cover_candidate_player
        total = b.value + bonus
        b.scored = True
        self.scores[player] += total
        self.queen_pending = False
        self.queen_holder = None
        self.awaiting_cover_bonus = False
        self.cover_candidate_ball = None
        self.message = f"Queen Covered! +{b.value} +{bonus} bonus."
        self._reset_player_if_over_target(player)
    
    def check_win(self):
        if all(b.pocketed or b.scored for b in self.balls) and not self.awaiting_cover_bonus:
            diff0 = abs(self.scores[0] - self.y)
            diff1 = abs(self.scores[1] - self.y)
            if diff0 < diff1: self.winner = 0
            elif diff1 < diff0: self.winner = 1
            else: self.winner = -1 # Draw

# ---------- Drawing (PIL) ----------
# def draw_board(game):
#     # Create canvas
#     img = Image.new('RGB', (BASE_BOARD_W, BASE_BOARD_H), (50, 150, 90))
#     draw = ImageDraw.Draw(img)
    
#     # Board Area
#     margin = BASE_BOARD_PADDING
#     draw.rectangle([margin-20, margin-20, BASE_BOARD_W-margin+20, BASE_BOARD_H-margin+20], 
#                    outline=(20, 90, 50), width=5)
    
#     # Pockets
#     for pk in game.pockets:
#         r = BASE_POCKET_R
#         draw.ellipse([pk[0]-r, pk[1]-r, pk[0]+r, pk[1]+r], fill=(10,10,10))
        
#     # Balls
#     for b in game.balls:
#         if b.pocketed: continue
#         r = b.radius
#         color = (200, 40, 40) if b.color == 'red' else (30, 30, 30)
#         outline = (255, 230, 230) if b.color == 'red' else (230, 230, 230)
#         draw.ellipse([b.pos[0]-r, b.pos[1]-r, b.pos[0]+r, b.pos[1]+r], fill=color, outline=(180,180,180))
        
#         # Text on ball (approximate centering)
#         try:
#             # PIL default font is tiny, but works without external files
#             t_w = len(str(b.expr)) * 6 
#             draw.text((b.pos[0]-t_w/2, b.pos[1]-5), str(b.expr), fill=outline)
#         except: pass

#     # Striker
#     s = game.striker
#     if not s.pocketed:
#         r = s.radius
#         draw.ellipse([s.pos[0]-r, s.pos[1]-r, s.pos[0]+r, s.pos[1]+r], fill=(240, 240, 240), outline=(100,100,100), width=2)
        
#     # Aim Line (if ready)
#     if s.vel[0] == 0 and s.vel[1] == 0 and not s.pocketed and not game.awaiting_cover_bonus and not game.winner:
#         # We need the aim angle/power from session state, passing via game arg is messy, 
#         # so we'll visualize based on the inputs provided in the UI context if possible.
#         # For now, just draw the striker.
#         pass
        
#     return img
def draw_board(game, aim_angle=None):
    # Create canvas
    img = Image.new('RGB', (BASE_BOARD_W, BASE_BOARD_H), (50, 150, 90))
    draw = ImageDraw.Draw(img)
    
    # Board Area
    margin = BASE_BOARD_PADDING
    draw.rectangle([margin-20, margin-20, BASE_BOARD_W-margin+20, BASE_BOARD_H-margin+20], 
                   outline=(20, 90, 50), width=5)
    
    # Pockets
    for pk in game.pockets:
        r = BASE_POCKET_R
        draw.ellipse([pk[0]-r, pk[1]-r, pk[0]+r, pk[1]+r], fill=(10,10,10))
        
    # Balls
    for b in game.balls:
        if b.pocketed: continue
        r = b.radius
        color = (200, 40, 40) if b.color == 'red' else (30, 30, 30)
        outline = (255, 230, 230) if b.color == 'red' else (230, 230, 230)
        draw.ellipse([b.pos[0]-r, b.pos[1]-r, b.pos[0]+r, b.pos[1]+r], fill=color, outline=(180,180,180))
        
        # Text on ball
        try:
            t_w = len(str(b.expr)) * 6 
            draw.text((b.pos[0]-t_w/2, b.pos[1]-5), str(b.expr), fill=outline)
        except: pass

    # Striker
    s = game.striker
    if not s.pocketed:
        r = s.radius
        draw.ellipse([s.pos[0]-r, s.pos[1]-r, s.pos[0]+r, s.pos[1]+r], fill=(240, 240, 240), outline=(100,100,100), width=2)
        
        # --- NEW: AIM LINE DRAWING ---
        # Only draw if angle is provided and game is in a state to shoot
        if aim_angle is not None and not game.winner and not game.awaiting_cover_bonus:
            # Convert degrees to radians
            rad = math.radians(aim_angle)
            # Calculate end point (length 800px to ensure it hits wall)
            line_len = 800
            end_x = s.pos[0] + math.cos(rad) * line_len
            end_y = s.pos[1] + math.sin(rad) * line_len
            
            # Draw Line (White, width 2)
            draw.line([s.pos[0], s.pos[1], end_x, end_y], fill=(255, 255, 255), width=2)
            
    return img
# ---------- Streamlit UI ----------

st.set_page_config(page_title="Algebraic Carrom", layout="wide")

if 'game' not in st.session_state:
    st.session_state.game = GameState()
    st.session_state.game_active = False

def init_game():
    try:
        x = int(st.session_state.input_x)
        y = int(st.session_state.input_y)
    except:
        x, y = random.randint(1,6), random.randint(30, 120)
    
    st.session_state.game.setup_new_game(x, y, st.session_state.p1_name, st.session_state.p2_name)
    st.session_state.game_active = True

# Sidebar Controls
with st.sidebar:
    st.title("Game Setup")
    st.text_input("Player 1 Name", key="p1_name", value="Player 1")
    st.text_input("Player 2 Name", key="p2_name", value="Player 2")
    st.number_input("Value x (1-10)", value=3, key="input_x")
    st.number_input("Target y (30-150)", value=50, key="input_y")
    st.button("New Game", on_click=init_game)
    
    st.markdown("---")
    st.markdown("### How to Play")
    st.markdown("1. Use sliders to position striker and aim.")
    st.markdown("2. Click **STRIKE**.")
    st.markdown("3. **Math Rule:** Solve expressions on pieces.")
    st.markdown("4. **Queen Rule:** If Queen is pocketed with a black piece, +2 points immediately. If alone, must cover next turn.")

# Main Game Area
st.title("Algebraic Carrom (Web Edition)")

game = st.session_state.game

if not st.session_state.game_active:
    st.info("Click 'New Game' in the sidebar to start!")
else:
    # 1. Status Bar
    col1, col2, col3 = st.columns(3)
    col1.metric(game.p1, game.scores[0], delta_color="normal")
    col2.metric("Target", game.y)
    col3.metric(game.p2, game.scores[1], delta_color="normal")
    
    st.info(f"📢 {game.message}")
    if game.queen_pending:
        st.warning(f"👑 Queen held by {game.p1 if game.queen_holder==0 else game.p2}. Needs Cover!")

    # 2. Controls (Only if waiting for shot)
    if game.all_stopped() and game.winner is None and not game.awaiting_cover_bonus:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            # Striker Position Slider
            min_x = BASE_BOARD_PADDING + BASE_STRIKER_R
            max_x = BASE_BOARD_W - BASE_BOARD_PADDING - BASE_STRIKER_R
            # striker_x = st.slider("Striker Position", min_x, max_x, float(BASE_BOARD_W//2))
            # NEW (Fix: wrap min_x and max_x in float())
            striker_x = st.slider(
                "Striker Position", 
                float(min_x), 
                float(max_x), 
                float(BASE_BOARD_W//2)
            )
            game.striker.pos[0] = striker_x
            game.striker.pos[1] = BASE_BOARD_H - BASE_BOARD_PADDING - 40
            
        with c2:
            angle = st.slider("Aim Angle (degrees)", 180, 360, 270, key="aim_angle")
            
        with c3:
            power = st.slider("Power", 0.0, MAX_STRIKE_POWER, 10.0)

        # Calculate vector for preview
        rad = math.radians(angle)
        dx = math.cos(rad) * 40
        dy = math.sin(rad) * 40
        
        # Fire Button
        if st.button("🔥 STRIKE", use_container_width=True):
            # Apply velocity
            vx = math.cos(rad) * power
            vy = math.sin(rad) * power
            game.striker.vel = [vx, vy]
            game.pocketed_this_shot = []
            
            # ANIMATION LOOP
            board_placeholder = st.empty()
            while not game.all_stopped():
                game.update_physics()
                img = draw_board(game)
                board_placeholder.image(img, use_container_width=True)
                time.sleep(0.01) # Small delay for animation
            
            # Resolve end of turn
            game.resolve_turn()
            game.check_win()
            st.rerun()

    # 3. Bonus Selection (Special State)
    elif game.awaiting_cover_bonus:
        st.markdown("### 🎲 Choose Cover Bonus")
        b = game.cover_candidate_ball
        max_bonus = max(1, b.value - 1)
        
        cols = st.columns(max_bonus)
        for i in range(1, max_bonus+1):
            if cols[i-1].button(f"+{i}"):
                game.finalize_cover(i)
                game.check_win()
                st.rerun()

    # 4. Winner State
    elif game.winner is not None:
        winner_name = game.p1 if game.winner == 0 else game.p2
        if game.winner == -1:
             st.success("Game Over! It's a DRAW!")
        else:
            st.balloons()
            st.success(f"🏆 WINNER: {winner_name}!")
        
        if st.button("Reset Board"):
            st.session_state.game_active = False
            st.rerun()

    # 5. Static Display (when not animating)
    if game.all_stopped():
        current_angle = st.session_state.get("aim_angle", 270)
        
        # Pass the angle to the draw function
        img = draw_board(game, aim_angle=current_angle)
        
        st.image(img, use_container_width=True)
        img = draw_board(game)
        # Draw aim line if ready
        # if not game.winner and not game.awaiting_cover_bonus:
        #     draw = ImageDraw.Draw(img)
        #     sx, sy = game.striker.pos
        #     # Re-calculate aim based on current slider values (trick: we need session state values)
        #     # Since strict animation loop handles the active state, here we just show static
        #     # Visualizing aim line statically is hard because sliders update state on interaction
        #     # but we can try to get them from session state if they exist
        #     pass 
            
        # st.image(img, use_container_width=True)

# # EOF

