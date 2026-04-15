import os, sys, math, random, json
import pygame
from constants import *
from map_loader import get_tile, is_door_open, toggle_door

class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def update(self, target_x, target_y, map_w, map_h):
        tx = target_x - SCREEN_W / 2
        ty = target_y - SCREEN_H / 2
        self.x += (tx - self.x) * CAMERA_SMOOTHING
        self.y += (ty - self.y) * CAMERA_SMOOTHING
        self.x = max(0, min(self.x, map_w * TILE_SIZE - SCREEN_W))
        self.y = max(0, min(self.y, map_h * TILE_SIZE - SCREEN_H))

    def apply(self, x, y):
        return x - self.x, y - self.y


class Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.hp = PLAYER_MAX_HP
        self.shoot_timer = 0.0
        self.alive = True

    def update(self, keys, game_map, dt):
        if not self.alive:
            return
        dx = dy = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
        spd = PLAYER_SPEED * dt * 60
        nx = self.x + dx * spd
        ny = self.y + dy * spd
        if not self._collides(nx, self.y, game_map):
            self.x = nx
        if not self._collides(self.x, ny, game_map):
            self.y = ny
        mx, my = pygame.mouse.get_pos()
        self.angle = math.atan2(my - SCREEN_H / 2, mx - SCREEN_W / 2)
        self.shoot_timer = max(0, self.shoot_timer - dt)

    def _collides(self, px, py, game_map):
        r = PLAYER_RADIUS
        for cx in (px - r, px + r):
            for cy in (py - r, py + r):
                gx = int(cx // TILE_SIZE)
                gy = int(cy // TILE_SIZE)
                t = get_tile(game_map["grid"], gx, gy)
                if t == TILE_WALL:
                    return True
                if t == TILE_DOOR and not is_door_open(game_map, gx, gy):
                    return True
        return False

    def try_shoot(self):
        if self.shoot_timer <= 0 and self.alive:
            self.shoot_timer = PLAYER_SHOOT_COOLDOWN
            bx = self.x + math.cos(self.angle) * 20
            by = self.y + math.sin(self.angle) * 20
            return Bullet(bx, by, self.angle, True, PLAYER_DAMAGE)
        return None

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def draw(self, surf, cam):
        sx, sy = cam.apply(self.x, self.y)
        pygame.draw.circle(surf, COLOR_PLAYER_OUTLINE, (int(sx), int(sy)), PLAYER_RADIUS + 2)
        pygame.draw.circle(surf, COLOR_PLAYER_BODY, (int(sx), int(sy)), PLAYER_RADIUS)
        ex = sx + math.cos(self.angle) * 18
        ey = sy + math.sin(self.angle) * 18
        pygame.draw.line(surf, COLOR_PLAYER_DIR, (int(sx), int(sy)), (int(ex), int(ey)), 3)


ST_PATROL = 0
ST_ALERT = 1
ST_CHASE = 2
ST_SHOOT = 3


class Enemy:
    def __init__(self, x, y, patrol=None):
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.hp = ENEMY_MAX_HP
        self.alive = True
        self.state = ST_PATROL
        self.alert_timer = 0.0
        self.shoot_timer = 0.0
        self.patrol = patrol or [(x, y)]
        self.patrol_idx = 0
        self.sight_check_timer = 0.0

    def update(self, player, game_map, dt):
        if not self.alive:
            return
        self.sight_check_timer += dt
        can_see = self._can_see(player, game_map)
        dist = math.hypot(player.x - self.x, player.y - self.y)
        if can_see and dist < ENEMY_VIEW_RANGE:
            if self.state == ST_PATROL:
                self.state = ST_ALERT
                self.alert_timer = ENEMY_ALERT_TIME
            if self.state == ST_ALERT:
                self.alert_timer -= dt
                if self.alert_timer <= 0:
                    self.state = ST_CHASE
            if self.state in (ST_CHASE, ST_SHOOT):
                self.angle = math.atan2(player.y - self.y, player.x - self.x)
                if dist < ENEMY_VIEW_RANGE * 0.8:
                    self.state = ST_SHOOT
                else:
                    self.state = ST_CHASE
        elif self.state != ST_PATROL:
            if self.state == ST_SHOOT:
                self.state = ST_CHASE
            elif self.state == ST_CHASE:
                self.state = ST_ALERT
                self.alert_timer = ENEMY_ALERT_TIME
            elif self.state == ST_ALERT:
                self.alert_timer -= dt
                if self.alert_timer <= 0:
                    self.state = ST_PATROL
        if self.state == ST_PATROL:
            self._patrol(dt, game_map)
        elif self.state == ST_CHASE:
            self._move_toward(player.x, player.y, ENEMY_SPEED, game_map, dt)
        self.shoot_timer = max(0, self.shoot_timer - dt)

    def _patrol(self, dt, game_map):
        if not self.patrol:
            return
        tx, ty = self.patrol[self.patrol_idx]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 8:
            self.patrol_idx = (self.patrol_idx + 1) % len(self.patrol)
        else:
            self.angle = math.atan2(dy, dx)
            self._move_toward(tx, ty, ENEMY_PATROL_SPEED, game_map, dt)

    def _move_toward(self, tx, ty, speed, game_map, dt):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        spd = speed * dt * 60
        mx = (dx / dist) * spd
        my = (dy / dist) * spd
        nx = self.x + mx
        ny = self.y + my
        if not self._collides(nx, self.y, game_map):
            self.x = nx
        if not self._collides(self.x, ny, game_map):
            self.y = ny

    def _collides(self, px, py, game_map):
        r = ENEMY_RADIUS
        for cx in (px - r, px + r):
            for cy in (py - r, py + r):
                gx = int(cx // TILE_SIZE)
                gy = int(cy // TILE_SIZE)
                t = get_tile(game_map["grid"], gx, gy)
                if t == TILE_WALL:
                    return True
                if t == TILE_DOOR and not is_door_open(game_map, gx, gy):
                    return True
        return False

    def _can_see(self, player, game_map):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > ENEMY_VIEW_RANGE:
            return False
        angle_to = math.atan2(dy, dx)
        diff = abs((angle_to - self.angle + math.pi) % (2 * math.pi) - math.pi)
        if diff > math.radians(ENEMY_VIEW_ANGLE / 2):
            return False
        steps = int(dist / (TILE_SIZE / 2))
        for i in range(steps):
            t = (i + 1) / steps
            cx = self.x + dx * t
            cy = self.y + dy * t
            gx = int(cx // TILE_SIZE)
            gy = int(cy // TILE_SIZE)
            tile = get_tile(game_map["grid"], gx, gy)
            if tile == TILE_WALL:
                return False
            if tile == TILE_DOOR and not is_door_open(game_map, gx, gy):
                return False
        return True

    def try_shoot(self, player):
        if self.shoot_timer <= 0 and self.alive and self.state == ST_SHOOT:
            self.shoot_timer = ENEMY_SHOOT_COOLDOWN
            bx = self.x + math.cos(self.angle) * 20
            by = self.y + math.sin(self.angle) * 20
            spread = random.uniform(-0.1, 0.1)
            return Bullet(bx, by, self.angle + spread, False, ENEMY_DAMAGE)
        return None

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def draw(self, surf, cam):
        if not self.alive:
            return
        sx, sy = cam.apply(self.x, self.y)
        pygame.draw.circle(surf, COLOR_ENEMY_OUTLINE, (int(sx), int(sy)), ENEMY_RADIUS + 2)
        pygame.draw.circle(surf, COLOR_ENEMY_BODY, (int(sx), int(sy)), ENEMY_RADIUS)
        ex = sx + math.cos(self.angle) * 18
        ey = sy + math.sin(self.angle) * 18
        pygame.draw.line(surf, (255, 255, 255), (int(sx), int(sy)), (int(ex), int(ey)), 3)
        if self.state == ST_ALERT:
            pygame.draw.circle(surf, COLOR_ENEMY_ALERT, (int(sx), int(sy)), ENEMY_RADIUS + 6, 2)
        elif self.state == ST_SHOOT:
            pygame.draw.circle(surf, (255, 50, 50), (int(sx), int(sy)), ENEMY_RADIUS + 6, 2)


class Bullet:
    def __init__(self, x, y, angle, is_player, damage):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.is_player = is_player
        self.damage = damage
        self.lifetime = BULLET_LIFETIME
        self.alive = True

    def update(self, dt):
        self.x += math.cos(self.angle) * BULLET_SPEED * dt * 60
        self.y += math.sin(self.angle) * BULLET_SPEED * dt * 60
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def check_wall(self, game_map):
        gx = int(self.x // TILE_SIZE)
        gy = int(self.y // TILE_SIZE)
        t = get_tile(game_map["grid"], gx, gy)
        if t == TILE_WALL:
            self.alive = False
            return True
        if t == TILE_DOOR and not is_door_open(game_map, gx, gy):
            self.alive = False
            return True
        return False

    def draw(self, surf, cam):
        sx, sy = cam.apply(self.x, self.y)
        color = COLOR_BULLET_PLAYER if self.is_player else COLOR_BULLET_ENEMY
        pygame.draw.circle(surf, color, (int(sx), int(sy)), BULLET_RADIUS)


class MapRenderer:
    def __init__(self, game_map):
        self.game_map = game_map
        self.grid = game_map["grid"]
        self.map_h = len(self.grid)
        self.map_w = len(self.grid[0]) if self.grid else 0

    def draw(self, surf, cam):
        sx0 = max(0, int(cam.x // TILE_SIZE))
        sy0 = max(0, int(cam.y // TILE_SIZE))
        sx1 = min(self.map_w, int((cam.x + SCREEN_W) // TILE_SIZE) + 2)
        sy1 = min(self.map_h, int((cam.y + SCREEN_H) // TILE_SIZE) + 2)
        for gy in range(sy0, sy1):
            for gx in range(sx0, sx1):
                tile = get_tile(self.grid, gx, gy)
                px, py = cam.apply(gx * TILE_SIZE, gy * TILE_SIZE)
                r = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)
                if tile == TILE_FLOOR:
                    pygame.draw.rect(surf, COLOR_FLOOR, r)
                    if (gx + gy) % 4 == 0:
                        pygame.draw.line(surf, COLOR_FLOOR_LINE, r.topleft, r.topright, 1)
                elif tile == TILE_TILE:
                    c = COLOR_TILE_A if (gx + gy) % 2 == 0 else COLOR_TILE_B
                    pygame.draw.rect(surf, c, r)
                    pygame.draw.rect(surf, (0, 0, 0, 40), r, 1)
                elif tile == TILE_GRASS:
                    c = COLOR_GRASS_A if (gx + gy) % 2 == 0 else COLOR_GRASS_B
                    pygame.draw.rect(surf, c, r)
                    random.seed(gx * 1000 + gy)
                    for _ in range(3):
                        dx = random.randint(4, TILE_SIZE - 4)
                        dy = random.randint(4, TILE_SIZE - 4)
                        pygame.draw.circle(surf, COLOR_GRASS_DETAIL, (int(px + dx), int(py + dy)), 2)
                    random.seed()
                elif tile == TILE_WALL:
                    self._draw_wall(surf, px, py, gx, gy)
                elif tile == TILE_WINDOW:
                    pygame.draw.rect(surf, COLOR_WINDOW_FRAME, r)
                    inner = r.inflate(-8, -8)
                    s = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
                    s.fill(COLOR_WINDOW_GLASS)
                    surf.blit(s, inner.topleft)
                    pygame.draw.line(surf, COLOR_WINDOW_FRAME, (int(px + TILE_SIZE/2), int(py)), (int(px + TILE_SIZE/2), int(py + TILE_SIZE)), 2)
                elif tile == TILE_DOOR:
                    if is_door_open(self.game_map, gx, gy):
                        pygame.draw.rect(surf, COLOR_DOOR_OPEN, r)
                    else:
                        pygame.draw.rect(surf, COLOR_DOOR_CLOSED, r)
                        r2 = r.inflate(-8, -8)
                        pygame.draw.rect(surf, COLOR_DOOR_CLOSED2, r2)
                        hx = int(px + TILE_SIZE * 0.7)
                        hy = int(py + TILE_SIZE / 2)
                        pygame.draw.circle(surf, COLOR_DOOR_HANDLE, (hx, hy), 3)

    def _draw_wall(self, surf, px, py, gx, gy):
        r = pygame.Rect(px, py - WALL_RELIEF_HEIGHT, TILE_SIZE, TILE_SIZE + WALL_RELIEF_HEIGHT)
        pygame.draw.rect(surf, COLOR_WALL_TOP, r)
        pygame.draw.rect(surf, COLOR_WALL_TOP2, (px + 2, py - WALL_RELIEF_HEIGHT + 2, TILE_SIZE - 4, WALL_RELIEF_HEIGHT - 2))
        side = pygame.Rect(px, py + TILE_SIZE - 6, TILE_SIZE, 6)
        pygame.draw.rect(surf, COLOR_WALL_SIDE, side)
        pygame.draw.line(surf, COLOR_WALL_SIDE2, (int(px), int(py + TILE_SIZE - 1)), (int(px + TILE_SIZE), int(py + TILE_SIZE - 1)), 1)


class HUD:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("consolas", 16, bold=True)
        self.font_big = pygame.font.SysFont("consolas", 28, bold=True)

    def draw(self, player, enemies):
        self._draw_hp(player)
        self._draw_minimap(player, enemies)
        self._draw_crosshair()

    def _draw_hp(self, player):
        bar_w, bar_h = 200, 20
        x, y = 20, 20
        bg = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
        bg.fill(HUD_BG)
        self.screen.blit(bg, (x - 2, y - 2))
        pygame.draw.rect(self.screen, (60, 60, 60), (x, y, bar_w, bar_h))
        ratio = player.hp / PLAYER_MAX_HP
        color = HUD_HP_HIGH if ratio > 0.5 else (HUD_HP_MED if ratio > 0.25 else HUD_HP_LOW)
        pygame.draw.rect(self.screen, color, (x, y, int(bar_w * ratio), bar_h))
        txt = self.font.render(f"HP: {player.hp}/{PLAYER_MAX_HP}", True, HUD_COLOR)
        self.screen.blit(txt, (x + 6, y + 2))

    def _draw_minimap(self, player, enemies, map_data=None):
        if map_data is None:
            return
        scale = MINIMAP_SCALE
        mw = map_data["width"] * scale
        mh = map_data["height"] * scale
        mx = SCREEN_W - mw - 15
        my = 15
        bg = pygame.Surface((mw + 4, mh + 4), pygame.SRCALPHA)
        bg.fill(MINIMAP_BG)
        self.screen.blit(bg, (mx - 2, my - 2))
        grid = map_data["grid"]
        for gy in range(len(grid)):
            for gx in range(len(grid[gy])):
                t = grid[gy][gx]
                if t == TILE_WALL:
                    pygame.draw.rect(self.screen, (120, 120, 130), (mx + gx * scale, my + gy * scale, scale, scale))
                elif t == TILE_DOOR:
                    pygame.draw.rect(self.screen, COLOR_DOOR_CLOSED, (mx + gx * scale, my + gy * scale, scale, scale))
        ppx = mx + int(player.x / TILE_SIZE * scale)
        ppy = my + int(player.y / TILE_SIZE * scale)
        pygame.draw.circle(self.screen, MINIMAP_PLAYER_COLOR, (ppx, ppy), 3)
        for e in enemies:
            if e.alive:
                epx = mx + int(e.x / TILE_SIZE * scale)
                epy = my + int(e.y / TILE_SIZE * scale)
                pygame.draw.circle(self.screen, MINIMAP_ENEMY_COLOR, (epx, epy), 2)

    def _draw_crosshair(self):
        cx, cy = pygame.mouse.get_pos()
        s = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.line(s, CROSSHAIR_COLOR, (10, 2), (10, 8), 2)
        pygame.draw.line(s, CROSSHAIR_COLOR, (10, 12), (10, 18), 2)
        pygame.draw.line(s, CROSSHAIR_COLOR, (2, 10), (8, 10), 2)
        pygame.draw.line(s, CROSSHAIR_COLOR, (12, 10), (18, 10), 2)
        self.screen.blit(s, (cx - 10, cy - 10))


def create_default_map(filepath):
    W, H = DEFAULT_MAP_W, DEFAULT_MAP_H
    grid = [[TILE_FLOOR] * W for _ in range(H)]
    for x in range(W):
        grid[0][x] = TILE_WALL
        grid[H - 1][x] = TILE_WALL
    for y in range(H):
        grid[y][0] = TILE_WALL
        grid[y][W - 1] = TILE_WALL
    rooms = [(1, 1, 8, 7), (10, 1, 20, 7), (22, 1, 29, 7),
             (1, 9, 8, 19), (10, 9, 20, 19), (22, 9, 29, 19)]
    for rx1, ry1, rx2, ry2 in rooms:
        for x in range(rx1, rx2 + 1):
            grid[ry1][x] = TILE_WALL
            grid[ry2][x] = TILE_WALL
        for y in range(ry1, ry2 + 1):
            grid[y][rx1] = TILE_WALL
            grid[y][rx2] = TILE_WALL
    doors = [(8, 4, 3), (8, 14, 3), (10, 4, 1), (10, 14, 1),
             (20, 4, 1), (20, 14, 1), (22, 4, 3), (22, 14, 3),
             (4, 7, 3), (4, 9, 3), (14, 7, 3), (14, 9, 3),
             (25, 7, 3), (25, 9, 3)]
    for dx, dy, dw in doors:
        for i in range(dw):
            if 0 <= dy < H and 0 <= dx + i < W:
                grid[dy][dx + i] = TILE_DOOR
    enemies = [
        {"x": 3, "y": 3, "patrol": [[3, 3], [6, 3], [6, 5], [3, 5]]},
        {"x": 15, "y": 3, "patrol": [[12, 3], [18, 3]]},
        {"x": 25, "y": 3, "patrol": [[24, 3], [28, 3], [28, 5], [24, 5]]},
        {"x": 3, "y": 14, "patrol": [[3, 12], [6, 12], [6, 16], [3, 16]]},
        {"x": 15, "y": 14, "patrol": [[12, 14], [18, 14], [18, 17], [12, 17]]},
        {"x": 25, "y": 14, "patrol": [[24, 12], [28, 12], [28, 17], [24, 17]]},
        {"x": 14, "y": 8, "patrol": [[10, 8], [20, 8]]},
    ]
    game_map = {
        "name": "Default",
        "width": W,
        "height": H,
        "grid": grid,
        "doors_open": [],
        "player_spawn": [2, 2],
        "enemies": enemies,
    }
    from map_loader import save_map
    save_map(game_map, filepath)
    return game_map


def run_game(map_path):
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("ARE YOU READY? - Tactical Special Forces")
    clock = pygame.time.Clock()
    pygame.mouse.set_visible(False)

    from map_loader import load_map
    if not os.path.exists(map_path):
        create_default_map(map_path)
    game_map = load_map(map_path)

    sx, sy = game_map["player_spawn"]
    player = Player(sx * TILE_SIZE + TILE_SIZE / 2, sy * TILE_SIZE + TILE_SIZE / 2)
    enemies = []
    for ed in game_map.get("enemies", []):
        e = Enemy(ed["x"] * TILE_SIZE + TILE_SIZE / 2, ed["y"] * TILE_SIZE + TILE_SIZE / 2, ed.get("patrol"))
        enemies.append(e)
    bullets = []
    camera = Camera()
    renderer = MapRenderer(game_map)
    hud = HUD(screen)
    paused = False
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    paused = not paused
                elif ev.key == pygame.K_e and not paused:
                    gx = int(player.x // TILE_SIZE)
                    gy = int(player.y // TILE_SIZE)
                    for ddx, ddy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        if toggle_door(game_map, gx + ddx, gy + ddy):
                            break
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and not paused:
                b = player.try_shoot()
                if b:
                    bullets.append(b)

        if not paused:
            keys = pygame.key.get_pressed()
            player.update(keys, game_map, dt)
            for e in enemies:
                e.update(player, game_map, dt)
                if random.random() < 0.3:
                    b = e.try_shoot(player)
                    if b:
                        bullets.append(b)
            for b in bullets[:]:
                b.update(dt)
                if b.check_wall(game_map):
                    bullets.remove(b)
                    continue
                if not b.alive:
                    bullets.remove(b)
                    continue
                if b.is_player:
                    for e in enemies:
                        if e.alive and math.hypot(b.x - e.x, b.y - e.y) < ENEMY_RADIUS + BULLET_RADIUS:
                            e.take_damage(b.damage)
                            b.alive = False
                            if b in bullets:
                                bullets.remove(b)
                            break
                else:
                    if player.alive and math.hypot(b.x - player.x, b.y - player.y) < PLAYER_RADIUS + BULLET_RADIUS:
                        player.take_damage(b.damage)
                        b.alive = False
                        if b in bullets:
                            bullets.remove(b)
            camera.update(player.x, player.y, game_map["width"], game_map["height"])

        screen.fill(COLOR_BG)
        renderer.draw(screen, camera)
        for b in bullets:
            b.draw(screen, camera)
        for e in enemies:
            e.draw(screen, camera)
        player.draw(screen, camera)
        hud.draw(player, enemies)
        hud._draw_minimap(player, enemies, game_map)

        if paused:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            ptxt = hud.font_big.render("PAUSED", True, (255, 255, 255))
            screen.blit(ptxt, (SCREEN_W // 2 - ptxt.get_width() // 2, SCREEN_H // 2 - 20))

        if not player.alive:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((100, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            dtxt = hud.font_big.render("MISSION FAILED", True, (255, 80, 80))
            screen.blit(dtxt, (SCREEN_W // 2 - dtxt.get_width() // 2, SCREEN_H // 2 - 20))

        alive_count = sum(1 for e in enemies if e.alive)
        if alive_count == 0 and player.alive:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 80, 0, 160))
            screen.blit(overlay, (0, 0))
            wtxt = hud.font_big.render("MISSION COMPLETE!", True, (80, 255, 80))
            screen.blit(wtxt, (SCREEN_W // 2 - wtxt.get_width() // 2, SCREEN_H // 2 - 20))

        pygame.display.flip()

    pygame.mouse.set_visible(True)
    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_game(sys.argv[1])
    else:
        mp = os.path.join(os.path.dirname(__file__), "maps", "default.json")
        run_game(mp)
