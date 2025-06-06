import pygame
import sys
import pickle
import os

# Initialize Pygame
pygame.init()

# Set up display
WIDTH, HEIGHT = 1600, 800
TILE_SIZE = 40
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Colonies")

# setting up UI hitboxes
pause_button = pygame.Rect(10, 10, 80, 30)
HOTBAR_RECT = pygame.Rect(10, HEIGHT - 60, 420, 50)
resume_button = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 - 60, 120, 40)
options_button = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 - 10, 120, 40)
quit_button = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 40, 120, 40)
back_button = pygame.Rect(WIDTH // 2 - 60, HEIGHT - 80, 120, 40)
mode_toggle_button = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 90, 120, 40)
save_button = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 140, 120, 40)
load_button = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 190, 120, 40)
player_rect = pygame.Rect(100, 100, 30, 30)
input_box = pygame.Rect(WIDTH // 2 - 100, 160, 200, 30)

# setting up camera variables
camera_x = 0
camera_y = 0
camera_speed = 10

suppress_click = False  # prevents accidental tile placement

# set up font
pygame.font.init()
font = pygame.font.SysFont('Times New Roman', 16)

# Set up clock
clock = pygame.time.Clock()

# setting up tilemap
ROWS = HEIGHT // TILE_SIZE
COLS = WIDTH // TILE_SIZE

# Tile IDs
TILE_EMPTY = 0
TILE_GRASS = 1
TILE_WATER = 2
TILE_SHALLOW = 3
TILE_DIRT = 4
TILE_STONE = 5
TILE_SPAWN = 6

# Tile colors
TILE_INFO = {
    TILE_EMPTY: {"name": "Empty", "color": (200, 200, 200)},
    TILE_GRASS: {"name": "Grass", "color": (0, 200, 0)},
    TILE_WATER: {"name": "Water", "color": (0, 100, 255)},
    TILE_SHALLOW: {"name": "Shallow", "color": (0, 150, 255)},
    TILE_DIRT: {"name": "Dirt", "color": (139, 69, 19)},
    TILE_STONE: {"name": "Stone", "color": (90, 90, 90)},
    TILE_SPAWN: {"name": "Spawn", "color": (125, 125, 0)},
}

selected_tile = TILE_GRASS
current_screen = "game"  # can be "game", "pause", "options", "resuming"
world_name = "MyWorld"
editing_name = False
pause_cooldown = 0
player_speed = 4
spawn_found = False
game_mode = "build"  # or "play"
player = None
spawn_point = (1*TILE_SIZE,1*TILE_SIZE)
pause_delay_frames = 0

projectiles = []

class Projectile:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 6, 6)
        self.speed = 7
        mx, my = pygame.mouse.get_pos()
        self.slope = (y - my)/(x - mx)
        if mx > x:
            self.direction = 1
        else:
            self.direction = -1

    def update(self):
        self.rect.y -= self.speed
        #self.rect.y -= self.speed*self.direction*self.slope
        #self.rect.x = self.rect.y / self.slope


    def draw(self, surface):
        pygame.draw.rect(surface, (255, 255, 0), self.rect)


class Tile:
    def __init__(self, tile_id):
        self.tile_id = tile_id
        self.updated = False
        self.spread_timer = 0

    def update(self, row, col, world):
        if self.tile_id == TILE_GRASS:
            self.spread_timer += 1
            if self.spread_timer >= 60:
                self.spread_timer = 0
                for dy in [-1, 1]:
                    r = row + dy
                    if 0 <= r < ROWS and world[r][col].tile_id == TILE_DIRT:
                        world[r][col] = Tile(TILE_GRASS)
                for dx in [-1, 1]:
                    c = col + dx
                    if 0 <= c < COLS and world[row][c].tile_id == TILE_DIRT:
                        world[row][c] = Tile(TILE_GRASS)

        if self.tile_id == TILE_WATER:
            self.spread_timer += 1
            if self.spread_timer >= 20:
                self.spread_timer = 0
                for dy, dx in [(-1,0), (1,0), (0,-1), (0,1)]:
                    ny, nx = row + dy, col + dx
                    if 0 <= ny < ROWS and 0 <= nx < COLS and world[ny][nx].tile_id == TILE_EMPTY:
                        world[ny][nx] = Tile(TILE_SHALLOW)

        if self.tile_id == TILE_SHALLOW:
            self.spread_timer += 1
            if self.spread_timer >= 60:
                self.spread_timer = 0

                has_water_neighbor = False
                for dy, dx in [(-1,0), (1,0), (0,-1), (0,1)]:
                    ny, nx = row + dy, col + dx
                    if 0 <= ny < ROWS and 0 <= nx < COLS:
                        if world[ny][nx].tile_id == TILE_WATER:
                            has_water_neighbor = True
                            break

                if has_water_neighbor:
                    for dy, dx in [(-1,0), (1,0), (0,-1), (0,1)]:
                        ny, nx = row + dy, col + dx
                        if 0 <= ny < ROWS and 0 <= nx < COLS and world[ny][nx].tile_id == TILE_EMPTY:
                            world[ny][nx] = Tile(TILE_SHALLOW)

world = [[Tile(TILE_EMPTY) for _ in range(COLS)] for _ in range(ROWS)]


def draw_grid():
    for row in range(ROWS):
        for col in range(COLS):
            tile = world[row][col]
            world_x = col * TILE_SIZE - camera_x
            world_y = row * TILE_SIZE - camera_y
            rect = pygame.Rect(world_x, world_y, TILE_SIZE, TILE_SIZE)
            color = TILE_INFO.get(tile.tile_id, {"color": (255, 0, 255)})["color"]
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (50, 50, 50), rect, 1)

def place_tile():
    global suppress_click
    if suppress_click:
        suppress_click = False
        return
    mouse_pos = pygame.mouse.get_pos()
    if pause_button.collidepoint(mouse_pos) or HOTBAR_RECT.collidepoint(mouse_pos):
        return
    world_x = mouse_pos[0] + camera_x
    world_y = mouse_pos[1] + camera_y
    col = world_x // TILE_SIZE
    row = world_y // TILE_SIZE
    if 0 <= row < ROWS and 0 <= col < COLS:
        if pygame.mouse.get_pressed()[0]:
            if selected_tile == TILE_SPAWN:
                # Remove old spawn point
                global spawn_point
                if spawn_point:
                    old_row, old_col = spawn_point
                    world[old_row][old_col] = Tile(TILE_EMPTY)
                spawn_point = (row, col)
            world[row][col] = Tile(selected_tile)
        elif pygame.mouse.get_pressed()[2]:
            if world[row][col].tile_id == TILE_SPAWN:
                spawn_point = None
            world[row][col] = Tile(TILE_EMPTY)

def update_tiles():
    for row in range(ROWS):
        for col in range(COLS):
            world[row][col].updated = False
    for row in range(ROWS):
        for col in range(COLS):
            tile = world[row][col]
            if not tile.updated:
                tile.update(row, col, world)
                tile.updated = True


def draw_hotbar():
    pygame.draw.rect(screen, (50, 50, 50), HOTBAR_RECT, border_radius=8)
    for i, tile_id in enumerate(TILE_INFO):
        x = 20 + i * 60
        y = HEIGHT - 50
        color = TILE_INFO[tile_id]["color"]
        name = TILE_INFO[tile_id]["name"]
        tile_rect = pygame.Rect(x, y, 40, 40)
        pygame.draw.rect(screen, color, tile_rect)
        label = font.render(name, True, (255, 255, 255))
        label_rect = label.get_rect(center=(x + 20, y + 25))
        screen.blit(label, label_rect)
        if tile_id == selected_tile:
            pygame.draw.rect(screen, (255, 255, 0), tile_rect, 3)
        else:
            pygame.draw.rect(screen, (0, 0, 0), tile_rect, 1)

def draw_pause_button():
    pygame.draw.rect(screen, (100, 100, 100), pause_button, border_radius=6)
    label = font.render("Pause", True, (255, 255, 255))
    label_rect = label.get_rect(center=pause_button.center)
    screen.blit(label, label_rect)

def draw_game_mode():
    text = f"Mode: {'PLAY' if game_mode == 'play' else 'BUILD'}"
    color = (255, 0, 0) if game_mode == "play" else (0, 255, 255)
    label = font.render(text, True, color)
    screen.blit(label, (WIDTH - 130, 10))


def draw_pause_menu():
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    # Buttons
    pygame.draw.rect(screen, (70, 70, 70), resume_button, border_radius=8)
    pygame.draw.rect(screen, (70, 70, 70), options_button, border_radius=8)
    pygame.draw.rect(screen, (70, 70, 70), quit_button, border_radius=8)
    pygame.draw.rect(screen, (100, 100, 100), mode_toggle_button, border_radius=8)

        # Labels
    save_label = font.render("Save", True, (255, 255, 255))
    load_label = font.render("Load", True, (255, 255, 255))
    resume_label = font.render("Resume", True, (255, 255, 255))
    options_label = font.render("Options", True, (255, 255, 255))
    quit_label = font.render("Quit", True, (255, 255, 255))
    toggle_label = font.render("To " + ("Build" if game_mode == "play" else "Play"), True, (255, 255, 255))

    screen.blit(resume_label, resume_label.get_rect(center=resume_button.center))
    screen.blit(options_label, options_label.get_rect(center=options_button.center))
    screen.blit(quit_label, quit_label.get_rect(center=quit_button.center))
    screen.blit(toggle_label, toggle_label.get_rect(center=mode_toggle_button.center))
    pygame.draw.rect(screen, (70, 70, 70), save_button, border_radius=8)
    pygame.draw.rect(screen, (70, 70, 70), load_button, border_radius=8)

    screen.blit(save_label, save_label.get_rect(center=save_button.center))
    screen.blit(load_label, load_label.get_rect(center=load_button.center))



def draw_options_menu():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)  # Enable alpha channel
    overlay.fill((30, 30, 30, 180))  # RGBA: semi-transparent dark overlay
    screen.blit(overlay, (0, 0))

    pygame.draw.rect(screen, (70, 70, 70), back_button, border_radius=8)
    back_label = font.render("Back", True, (255, 255, 255))
    screen.blit(back_label, back_label.get_rect(center=back_button.center))

    title = font.render("Options Menu", True, (255, 255, 255))
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 100)))

    pygame.draw.rect(screen, (100, 100, 100), input_box, border_radius=4)
    world_name_display = world_name + ("|" if editing_name else "")
    name_text = font.render(f"World Name: {world_name_display}", True, (255, 255, 255))
    screen.blit(name_text, (input_box.x + 10, input_box.y + 5))



def find_spawn_point():
    for row in range(ROWS):
        for col in range(COLS):
            if world[row][col].tile_id == TILE_SPAWN:
                return col * TILE_SIZE, row * TILE_SIZE
    return 100, 100  # fallback position

def save_game():
    save_data = {
        "world": [[tile.tile_id for tile in row] for row in world],
        "spawn_point": spawn_point,
        "world_name": world_name
    }
    with open(f"{world_name}.sav", "wb") as f:
        pickle.dump(save_data, f)
    print("Game saved!")

def load_game():
    global world, spawn_point, world_name
    if os.path.exists(f"{world_name}.sav"):
        with open(f"{world_name}.sav", "rb") as f:
            save_data = pickle.load(f)
            world_data = save_data["world"]
            spawn_point = save_data["spawn_point"]
            world_name = save_data["world_name"]
            world = [[Tile(tile_id) for tile_id in row] for row in world_data]
        print("Game loaded!")
    else:
        print("Save file not found.")

# Main game loop
running = True
while running:
    clock.tick(60)
    screen.fill((0, 0, 0))

    if current_screen in ("game", "resuming"):
        # Handle visual consistency
        draw_grid()
        draw_hotbar()
        draw_pause_button()
        draw_game_mode()
        if game_mode == "play":
            pygame.draw.rect(screen, (255, 0, 0), player_rect)

            for projectile in projectiles[:]:
                projectile.update()
                projectile.draw(screen)
                if projectile.rect.bottom < 0:
                    projectiles.remove(projectile)
                if projectile.rect.top > HEIGHT:
                    projectiles.remove(projectile)

        if current_screen == "game":
            if game_mode == "play":
                update_tiles()
            place_tile()  # Allow placing tiles in both modes

        elif current_screen == "resuming":
            pause_cooldown -= 1
            if pause_cooldown <= 0:
                current_screen = "game"
    elif current_screen == "pause":
        draw_grid()
        draw_hotbar()
        draw_pause_button()
        draw_pause_menu()

    elif current_screen == "options":
        draw_options_menu()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if current_screen == "game":
                if pause_button.collidepoint(mouse_pos):
                    current_screen = "pause"
                elif HOTBAR_RECT.collidepoint(mouse_pos):
                    for i, tile_id in enumerate(TILE_INFO):
                        x = 20 + i * 60
                        y = HEIGHT - 50
                        tile_rect = pygame.Rect(x, y, 40, 40)
                        if tile_rect.collidepoint(mouse_pos):
                            selected_tile = tile_id
                            break
            elif current_screen == "pause":
                if resume_button.collidepoint(mouse_pos):
                    current_screen = "resuming"
                    pause_cooldown = 15
                    suppress_click = True
                elif save_button.collidepoint(mouse_pos):
                    save_game()
                    suppress_click = True
                elif load_button.collidepoint(mouse_pos):
                    load_game()
                    suppress_click = True
                elif options_button.collidepoint(mouse_pos):
                    current_screen = "options"
                elif quit_button.collidepoint(mouse_pos):
                    running = False
                elif mode_toggle_button.collidepoint(mouse_pos):
                    if game_mode == "build":
                        if spawn_point:
                            game_mode = "play"
                            player = pygame.Rect(
                                spawn_point[0] * TILE_SIZE - camera_x,
                                spawn_point[1] * TILE_SIZE - camera_y,
                                TILE_SIZE,
                                TILE_SIZE
                            )
                        else:
                            game_mode = "play"
                            player = pygame.Rect(
                                400,
                                400,
                                TILE_SIZE,
                                TILE_SIZE
                            )
                    else:
                        game_mode = "build"
                        player = None
                    suppress_click = True

            elif current_screen == "options":
                if back_button.collidepoint(mouse_pos):
                    current_screen = "pause"
                elif input_box.collidepoint(mouse_pos):
                    editing_name = True
                else:
                    editing_name = False
        elif event.type == pygame.KEYDOWN:
            if current_screen == "game":
                if event.key == pygame.K_1:
                    selected_tile = TILE_GRASS
                elif event.key == pygame.K_2:
                    selected_tile = TILE_WATER
                elif event.key == pygame.K_3:
                    selected_tile = TILE_SHALLOW
                elif event.key == pygame.K_4:
                    selected_tile = TILE_DIRT
                elif event.key == pygame.K_5:
                    selected_tile = TILE_STONE
                elif event.key == pygame.K_6:
                    selected_tile = TILE_SPAWN
            elif current_screen == "options" and editing_name:
                if event.key == pygame.K_BACKSPACE:
                    world_name = world_name[:-1]
                elif event.key == pygame.K_RETURN:
                    editing_name = False
                else:
                    world_name += event.unicode

            elif event.key == pygame.K_q:
                if game_mode == "build":
                        if spawn_point:
                            game_mode = "play"
                            player = pygame.Rect(
                                spawn_point[0] * TILE_SIZE - camera_x,
                                spawn_point[1] * TILE_SIZE - camera_y,
                                TILE_SIZE,
                                TILE_SIZE
                            )
                        else:
                            game_mode = "play"
                            player = pygame.Rect(
                                400,
                                400,
                                TILE_SIZE,
                                TILE_SIZE
                            )
                else:
                    game_mode = "build"
                    player = None
                suppress_click = True
            elif event.key == pygame.K_SPACE:
                if game_mode == "play":
                    print("signal recieved in play by spacebar")
                    proj_x = player_rect.centerx
                    proj_y = player_rect.centery
                    projectiles.append(Projectile(proj_x, proj_y))


    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        camera_y -= camera_speed
    if keys[pygame.K_DOWN]:
        camera_y += camera_speed
    if keys[pygame.K_LEFT]:
        camera_x -= camera_speed
    if keys[pygame.K_RIGHT]:
        camera_x += camera_speed
    if game_mode == "play":
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]: player_rect.y -= player_speed
        if keys[pygame.K_s]: player_rect.y += player_speed
        if keys[pygame.K_a]: player_rect.x -= player_speed
        if keys[pygame.K_d]: player_rect.x += player_speed

    pygame.display.flip()

pygame.quit()
sys.exit()
