import pygame
import random
import math
import json
import os

pygame.init()
WIDTH, HEIGHT = 700, 700
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 128, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
screen = pygame.display.set_mode([WIDTH, HEIGHT])
clock = pygame.time.Clock()
pygame.display.set_caption('Cross Fire')

# dif settings
DIFFICULTIES = {
    "Easy": {
        "base_enemy_speed": 3,
        "base_spawn_interval": 50,
        "homing_spawn_interval": 999999,
        "num_to_spawn_func": lambda score: 1,
    },
    "Medium": {
        "base_enemy_speed": 4,
        "base_spawn_interval": 30,
        "homing_spawn_interval": 500,
        "num_to_spawn_func": lambda score: 1 + score // 10,
    },
    "Hard": {
        "base_enemy_speed": 5,
        "base_spawn_interval": 15,
        "homing_spawn_interval": 200,
        "num_to_spawn_func": lambda score: 2 + score // 8,
    }
}
LEADERBOARD_FILE = "leaderboards.json"
MAX_LEADERS = 3

# --- Persistent leaderboard logic ---
def load_leaderboards():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    # If file doesn't exist, make empty leaderboards for each mode
    return {mode: [] for mode in DIFFICULTIES}

def save_leaderboards(leaderboards):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(leaderboards, f)

leaderboards = load_leaderboards()

difficulty = "Medium"
def set_difficulty(diff):
    global base_enemy_speed, base_spawn_interval, homing_spawn_interval, num_to_spawn_func, difficulty
    base_enemy_speed = DIFFICULTIES[diff]["base_enemy_speed"]
    base_spawn_interval = DIFFICULTIES[diff]["base_spawn_interval"]
    homing_spawn_interval = DIFFICULTIES[diff]["homing_spawn_interval"]
    num_to_spawn_func = DIFFICULTIES[diff]["num_to_spawn_func"]
    difficulty = diff

set_difficulty(difficulty)

x, y = WIDTH // 2, HEIGHT // 2
radius = 10
speed = 5
dx, dy = 0, 0

enemies = []  # [x, y, dx, dy, slowed]
spawn_timer = 0

homing_enemies = []  # [x, y, spawn_time, slowed]
homing_spawn_timer = 0
HOMING_LIFESPAN = 5000  # ms

zigzag_enemies = []  # [x, y, dx, base_y, amplitude, freq, t, slowed]
zigzag_spawn_timer = 0
ZIGZAG_SPAWN_INTERVAL = 180  # 3 seconds at 60fps

score = 0
collectables = []
collectable_spawn_timer = 0
collectable_interval = 90
collectable_radius = 6

rare_collectables = []
rare_spawn_timer = 0
rare_interval = 600
rare_radius = 8
RARE_VALUE = 3

powerups = []  # [x, y, type]
powerup_spawn_timer = 0
powerup_spawn_interval = 1200
powerup_radius = 8

slow_spawn_timer = 0
slow_spawn_interval = 1600
SLOW_DURATION = 5000  # ms
slow_active = False
slow_start_time = 0

SHRINK_DURATION = 5000  # ms
shrink_active = False
shrink_start_time = 0
shrink_radius = 5

BOOST_AMOUNT = 10

invincible = False
invincible_start_time = 0
INVINCIBLE_DURATION = 5000  # ms

button_font = pygame.font.SysFont(None, 48)
font = pygame.font.SysFont(None, 72)
button_text = button_font.render("Restart", True, BLACK)
button_width, button_height = 200, 60
button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, HEIGHT // 2 + 20, button_width, button_height)

easy_text = button_font.render("Easy", True, BLACK)
medium_text = button_font.render("Medium", True, BLACK)
hard_text = button_font.render("Hard", True, RED)
easy_button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, HEIGHT // 2 - 80, button_width, button_height)
medium_button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, HEIGHT // 2, button_width, button_height)
hard_button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, HEIGHT // 2 + 80, button_width, button_height)

home_text = button_font.render("Home", True, BLACK)
home_button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, HEIGHT // 2 + 100, button_width, button_height)

running = True
game_over = False
main_menu = True

def reset_game():
    global x, y, dx, dy, enemies, collectables, score, spawn_timer, collectable_spawn_timer
    global rare_collectables, homing_enemies, powerups, invincible, game_over, homing_spawn_timer, powerup_spawn_timer
    global slow_active, slow_start_time, slow_spawn_timer, shrink_active, shrink_start_time
    global zigzag_enemies, zigzag_spawn_timer
    x, y = WIDTH // 2, HEIGHT // 2
    dx, dy = 0, 0
    enemies = []
    collectables = []
    score = 0
    spawn_timer = 0
    collectable_spawn_timer = 0
    rare_collectables = []
    homing_enemies = []
    powerups = []
    invincible = False
    game_over = False
    homing_spawn_timer = 0
    powerup_spawn_timer = 0
    slow_active = False
    slow_start_time = 0
    slow_spawn_timer = 0
    shrink_active = False
    shrink_start_time = 0
    zigzag_enemies = []
    zigzag_spawn_timer = 0

while running:
    screen.fill(BLACK)

    if main_menu:
        title = font.render("Cross Fire", True, GREEN)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 180))
        pygame.draw.rect(screen, WHITE, easy_button_rect)
        screen.blit(easy_text, (easy_button_rect.x + (button_width - easy_text.get_width()) // 2,
                                easy_button_rect.y + (button_height - easy_text.get_height()) // 2))
        pygame.draw.rect(screen, WHITE, medium_button_rect)
        screen.blit(medium_text, (medium_button_rect.x + (button_width - medium_text.get_width()) // 2,
                                  medium_button_rect.y + (button_height - medium_text.get_height()) // 2))
        pygame.draw.rect(screen, WHITE, hard_button_rect)
        screen.blit(hard_text, (hard_button_rect.x + (button_width - hard_text.get_width()) // 2,
                                hard_button_rect.y + (button_height - hard_text.get_height()) // 2))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if easy_button_rect.collidepoint(event.pos):
                    set_difficulty("Easy")
                    reset_game()
                    main_menu = False
                elif medium_button_rect.collidepoint(event.pos):
                    set_difficulty("Medium")
                    reset_game()
                    main_menu = False
                elif hard_button_rect.collidepoint(event.pos):
                    set_difficulty("Hard")
                    reset_game()
                    main_menu = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    set_difficulty("Easy")
                    reset_game()
                    main_menu = False
                elif event.key == pygame.K_2:
                    set_difficulty("Medium")
                    reset_game()
                    main_menu = False
                elif event.key == pygame.K_3:
                    set_difficulty("Hard")
                    reset_game()
                    main_menu = False
        pygame.display.update()
        clock.tick(60)
        continue

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if not game_over:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    dx -= speed
                elif event.key == pygame.K_d:
                    dx += speed
                elif event.key == pygame.K_w:
                    dy -= speed
                elif event.key == pygame.K_s:
                    dy += speed
                if event.key == pygame.K_LEFT:
                    dx -= speed
                elif event.key == pygame.K_RIGHT:
                    dx += speed
                elif event.key == pygame.K_UP:
                    dy -= speed
                elif event.key == pygame.K_DOWN:
                    dy += speed

            elif event.type == pygame.KEYUP:
                if event.key in [pygame.K_a, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT]:
                    dx = 0
                elif event.key in [pygame.K_w, pygame.K_s, pygame.K_UP, pygame.K_DOWN]:
                    dy = 0

        else:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    reset_game()
                elif home_button_rect.collidepoint(event.pos):
                    main_menu = True
                    game_over = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    reset_game()
                elif event.key == pygame.K_ESCAPE:
                    main_menu = True
                    game_over = False

    if not game_over:
        x += dx
        y += dy
        x = max(radius, min(WIDTH - radius, x))
        y = max(radius, min(HEIGHT - radius, y))

        if slow_active:
            enemy_speed = (base_enemy_speed + (score // 20)) * 0.2
        else:
            enemy_speed = base_enemy_speed + (score // 20)
        spawn_interval = max(10, base_spawn_interval - score // 2)
        num_to_spawn = num_to_spawn_func(score)

        spawn_timer += 1
        if spawn_timer >= spawn_interval:
            spawn_timer = 0
            for _ in range(num_to_spawn):
                side = random.choice(['top', 'bottom', 'left', 'right'])
                if side == 'top':
                    ex = random.randint(0, WIDTH)
                    ey = -20
                    edx, edy = 0, enemy_speed
                elif side == 'bottom':
                    ex = random.randint(0, WIDTH)
                    ey = HEIGHT + 20
                    edx, edy = 0, -enemy_speed
                elif side == 'left':
                    ex = -20
                    ey = random.randint(0, HEIGHT)
                    edx, edy = enemy_speed, 0
                else:
                    ex = WIDTH + 20
                    ey = random.randint(0, HEIGHT)
                    edx, edy = -enemy_speed, 0
                enemies.append([ex, ey, edx, edy, False])

        zigzag_spawn_timer += 1
        if zigzag_spawn_timer >= ZIGZAG_SPAWN_INTERVAL:
            zigzag_spawn_timer = 0
            side = random.choice(['left', 'right'])
            amplitude = random.randint(40, 120)
            freq = random.uniform(0.04, 0.07)
            if side == 'left':
                zx = -20
                zy = random.randint(100, HEIGHT - 100)
                dxz = 4
            else:
                zx = WIDTH + 20
                zy = random.randint(100, HEIGHT - 100)
                dxz = -4
            base_y = zy
            t = 0
            zigzag_enemies.append([zx, zy, dxz, base_y, amplitude, freq, t, False])

        for enemy in enemies:
            if slow_active:
                enemy[0] += enemy[2] * 0.5
                enemy[1] += enemy[3] * 0.5
                enemy[4] = True
            else:
                enemy[0] += enemy[2]
                enemy[1] += enemy[3]
        enemies = [e for e in enemies if -30 < e[0] < WIDTH + 30 and -30 < e[1] < HEIGHT + 30]

        for z in zigzag_enemies:
            if slow_active:
                z[0] += z[2] * 0.5
                z[6] += 0.5
                z[7] = True
            else:
                z[0] += z[2]
                z[6] += 1
            z[1] = z[3] + math.sin(z[6] * z[5]) * z[4]
        zigzag_enemies = [z for z in zigzag_enemies if -30 < z[0] < WIDTH + 30 and 0 < z[1] < HEIGHT]

        current_time = pygame.time.get_ticks()
        for h_enemy in homing_enemies[:]:
            if current_time - h_enemy[2] > HOMING_LIFESPAN:
                homing_enemies.remove(h_enemy)
                continue
            dx_to_player = x - h_enemy[0]
            dy_to_player = y - h_enemy[1]
            dist = max(1, (dx_to_player**2 + dy_to_player**2)**0.5)
            speed_factor = 0.75 * (0.4 if slow_active else 1)
            if slow_active:
                h_enemy[0] += (dx_to_player / dist) * enemy_speed * speed_factor * 0.5
                h_enemy[1] += (dy_to_player / dist) * enemy_speed * speed_factor * 0.5
                if len(h_enemy) < 4:
                    h_enemy.append(True)
                else:
                    h_enemy[3] = True
            else:
                h_enemy[0] += (dx_to_player / dist) * enemy_speed * speed_factor
                h_enemy[1] += (dy_to_player / dist) * enemy_speed * speed_factor
                if len(h_enemy) < 4:
                    h_enemy.append(False)
                else:
                    h_enemy[3] = False
        homing_enemies = [h for h in homing_enemies if -30 < h[0] < WIDTH + 30 and -30 < h[1] < HEIGHT + 30]

        for enemy in enemies:
            dist = ((enemy[0] - x) ** 2 + (enemy[1] - y) ** 2) ** 0.5
            if dist < (radius if not shrink_active else shrink_radius) + 10 and not invincible:
                game_over = True
                # --- leaderboard update ---
                lb = leaderboards[difficulty]
                lb.append(score)
                lb.sort(reverse=True)
                leaderboards[difficulty] = lb[:MAX_LEADERS]
                save_leaderboards(leaderboards)
                break

        for z in zigzag_enemies:
            dist = ((z[0] - x) ** 2 + (z[1] - y) ** 2) ** 0.5
            if dist < (radius if not shrink_active else shrink_radius) + 14 and not invincible:
                game_over = True
                lb = leaderboards[difficulty]
                lb.append(score)
                lb.sort(reverse=True)
                leaderboards[difficulty] = lb[:MAX_LEADERS]
                save_leaderboards(leaderboards)
                break

        for h_enemy in homing_enemies:
            dist = ((h_enemy[0] - x) ** 2 + (h_enemy[1] - y) ** 2) ** 0.5
            if dist < (radius if not shrink_active else shrink_radius) + 10 and not invincible:
                game_over = True
                lb = leaderboards[difficulty]
                lb.append(score)
                lb.sort(reverse=True)
                leaderboards[difficulty] = lb[:MAX_LEADERS]
                save_leaderboards(leaderboards)
                break

        collectable_spawn_timer += 1
        if collectable_spawn_timer >= collectable_interval:
            collectable_spawn_timer = 0
            cx = random.randint(collectable_radius, WIDTH - collectable_radius)
            cy = random.randint(collectable_radius, HEIGHT - collectable_radius)
            collectables.append([cx, cy])

        rare_spawn_timer += 1
        if rare_spawn_timer >= rare_interval:
            rare_spawn_timer = 0
            rx = random.randint(rare_radius, WIDTH - rare_radius)
            ry = random.randint(rare_radius, HEIGHT - rare_radius)
            rare_collectables.append([rx, ry])

        if homing_spawn_interval < 999999:
            homing_spawn_timer += 1
            if homing_spawn_timer >= homing_spawn_interval:
                homing_spawn_timer = 0
                side = random.choice(['top', 'bottom', 'left', 'right'])
                if side == 'top':
                    hx = random.randint(0, WIDTH)
                    hy = -20
                elif side == 'bottom':
                    hx = random.randint(0, WIDTH)
                    hy = HEIGHT + 20
                elif side == 'left':
                    hx = -20
                    hy = random.randint(0, HEIGHT)
                else:
                    hx = WIDTH + 20
                    hy = random.randint(0, HEIGHT)
                spawn_time = pygame.time.get_ticks()
                homing_enemies.append([hx, hy, spawn_time, False])

        powerup_spawn_timer += 1
        if powerup_spawn_timer >= powerup_spawn_interval:
            powerup_spawn_timer = 0
            px = random.randint(powerup_radius, WIDTH - powerup_radius)
            py = random.randint(powerup_radius, HEIGHT - powerup_radius)
            ptype = random.choice(['shield', 'shrink', 'clear', 'boost'])
            powerups.append([px, py, ptype])

        slow_spawn_timer += 1
        if slow_spawn_timer >= slow_spawn_interval:
            slow_spawn_timer = 0
            sx = random.randint(powerup_radius, WIDTH - powerup_radius)
            sy = random.randint(powerup_radius, HEIGHT - powerup_radius)
            powerups.append([sx, sy, 'slow'])

        for c in collectables[:]:
            dist = ((c[0] - x) ** 2 + (c[1] - y) ** 2) ** 0.5
            if dist < (radius if not shrink_active else shrink_radius) + collectable_radius:
                collectables.remove(c)
                score += 1

        for r in rare_collectables[:]:
            dist = ((r[0] - x) ** 2 + (r[1] - y) ** 2) ** 0.5
            if dist < (radius if not shrink_active else shrink_radius) + rare_radius:
                rare_collectables.remove(r)
                score += RARE_VALUE

        for p in powerups[:]:
            dist = ((p[0] - x) ** 2 + (p[1] - y) ** 2) ** 0.5
            if dist < (radius if not shrink_active else shrink_radius) + powerup_radius:
                if p[2] == 'shield':
                    invincible = True
                    invincible_start_time = pygame.time.get_ticks()
                elif p[2] == 'slow':
                    slow_active = True
                    slow_start_time = pygame.time.get_ticks()
                elif p[2] == 'shrink':
                    shrink_active = True
                    shrink_start_time = pygame.time.get_ticks()
                elif p[2] == 'clear':
                    enemies.clear()
                    homing_enemies.clear()
                    zigzag_enemies.clear()
                elif p[2] == 'boost':
                    score += BOOST_AMOUNT
                powerups.remove(p)

        if invincible and pygame.time.get_ticks() - invincible_start_time > INVINCIBLE_DURATION:
            invincible = False

        if slow_active and pygame.time.get_ticks() - slow_start_time > SLOW_DURATION:
            slow_active = False
            enemies = [e for e in enemies if not e[4]]
            zigzag_enemies = [z for z in zigzag_enemies if not z[7]]
            homing_enemies = [h for h in homing_enemies if len(h) < 4 or not h[3]]

        if shrink_active and pygame.time.get_ticks() - shrink_start_time > SHRINK_DURATION:
            shrink_active = False

        for enemy in enemies:
            pygame.draw.circle(screen, RED, (int(enemy[0]), int(enemy[1])), 10)

        for z in zigzag_enemies:
            pygame.draw.circle(screen, YELLOW, (int(z[0]), int(z[1])), 14)

        for r in rare_collectables:
            pygame.draw.circle(screen, (255, 215, 0), (r[0], r[1]), rare_radius)

        for c in collectables:
            pygame.draw.circle(screen, GREEN, (c[0], c[1]), collectable_radius)

        for p in powerups:
            if p[2] == 'shield':
                pygame.draw.circle(screen, CYAN, (p[0], p[1]), powerup_radius)
            elif p[2] == 'slow':
                pygame.draw.circle(screen, BLUE, (p[0], p[1]), powerup_radius)
            elif p[2] == 'shrink':
                pygame.draw.circle(screen, (255, 105, 180), (p[0], p[1]), powerup_radius)
            elif p[2] == 'clear':
                pygame.draw.circle(screen, (255, 255, 0), (p[0], p[1]), powerup_radius)
            elif p[2] == 'boost':
                pygame.draw.circle(screen, (255, 140, 0), (p[0], p[1]), powerup_radius)

        if invincible:
            pygame.draw.circle(screen, CYAN, (x, y), (radius if not shrink_active else shrink_radius) + 4, 2)

        pygame.draw.circle(screen, WHITE, (x, y), shrink_radius if shrink_active else radius)

        for h_enemy in homing_enemies:
            pygame.draw.circle(screen, PURPLE, (int(h_enemy[0]), int(h_enemy[1])), 10)

        if invincible:
            time_left = max(0, INVINCIBLE_DURATION - (pygame.time.get_ticks() - invincible_start_time))
            seconds = math.ceil(time_left / 1000)
            timer_text = button_font.render(f"Shield: {seconds}s", True, CYAN)
            screen.blit(timer_text, (WIDTH - timer_text.get_width() - 10, 10))

        if slow_active:
            time_left = max(0, SLOW_DURATION - (pygame.time.get_ticks() - slow_start_time))
            seconds = math.ceil(time_left / 1000)
            slow_text = button_font.render(f"Slow: {seconds}s", True, BLUE)
            screen.blit(slow_text, (WIDTH - 180, 60))

        if shrink_active:
            time_left = max(0, SHRINK_DURATION - (pygame.time.get_ticks() - shrink_start_time))
            seconds = math.ceil(time_left / 1000)
            shrink_text = button_font.render(f"Shrink: {seconds}s", True, (255, 105, 180))
            screen.blit(shrink_text, (WIDTH - 180, 110))

    else:
        text = font.render("Game Over", True, RED)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 50))

        pygame.draw.rect(screen, WHITE, button_rect)
        screen.blit(button_text, (button_rect.x + (button_width - button_text.get_width()) // 2,
                                  button_rect.y + (button_height - button_text.get_height()) // 2))

        pygame.draw.rect(screen, WHITE, home_button_rect)
        screen.blit(home_text, (home_button_rect.x + (button_width - home_text.get_width()) // 2,
                                home_button_rect.y + (button_height - home_text.get_height()) // 2))

        # --- Show leaderboard for current mode ---
        lb_title = button_font.render(f"Top Scores: {difficulty}", True, WHITE)
        screen.blit(lb_title, (WIDTH // 2 - lb_title.get_width() // 2, HEIGHT // 2 + 180))
        lb = leaderboards[difficulty]
        for i, s in enumerate(lb):
            lb_entry = button_font.render(f"{i+1}:  {s}", True, WHITE)
            screen.blit(lb_entry, (WIDTH // 2 - lb_entry.get_width() // 2, HEIGHT // 2 + 220 + i * 30))

    score_text = button_font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))

    pygame.display.update()
    clock.tick(60)

pygame.quit()