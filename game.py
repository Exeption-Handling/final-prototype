import pygame
import sys
from fastapi import Request
from sqlalchemy.orm import Session
from main_local import *
import random, json

USER_PLANTS = []

# 실행 시 JSON 파일 경로 받기
if len(sys.argv) > 1:
    json_path = sys.argv[1]
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            USER_PLANTS = data.get("plants", [])
    except Exception as e:
        USER_PLANTS = []
else:
    USER_PLANTS = []

pygame.init()


WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (150, 150, 150)

CELL_WIDTH = 80
CELL_HEIGHT = 100
GRID_COLS = 10
GRID_ROWS = 6

WIDTH = CELL_WIDTH * GRID_COLS
HEIGHT = CELL_HEIGHT * GRID_ROWS

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Plants Defense Game")

clock = pygame.time.Clock()
FPS = 60

UNIT_SIZE = (70, 70)

def load_image(path, size=None):
    image = pygame.image.load(path).convert_alpha()
    if size:
        image = pygame.transform.scale(image, size)
    return image


class Unit(pygame.sprite.Sprite):
    def __init__(self, x, y, hp, image_path):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, UNIT_SIZE)
        self.rect = self.image.get_rect(topleft = (x, y))
        self.hp = hp

        self.original_image = self.image.copy()
        self.hit_flash_timer = 0
        self.flash_duration = 5

        self.row = self.rect.y // CELL_HEIGHT

    def take_damage(self, dmg):
        self.hp -= dmg
        self.hit_flash_timer = self.flash_duration

        if self.hp <= 0:
            self.kill()

    def update_flash(self):
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
            flash_image = self.original_image.copy()
            flash_image.fill((255, 255, 100), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = flash_image
        else:
            self.image = self.original_image.copy()


class Enemy(Unit):
    def __init__(self, x, y, hp, image_path, kill_callback = None):
        super().__init__(x, y, hp, image_path)
        self.speed = 1
        self.attack_damage = 4
        self.attack_delay = 60
        self.attack_timer = 0
        self.kill_callback = kill_callback
        pygame.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 2)

    def take_damage(self, dmg):
        super().take_damage(dmg)
        if self.hp <= 0 and self.kill_callback:
            self.kill_callback()

    def update(self, plants):
        hit_plant = pygame.sprite.spritecollideany(self, plants) # 수정?
        self.update_flash()
        # 적이 앞에 식물이 있는지 체크 (충돌 검사 전 이동 위치 예측)
        next_x = self.rect.x - self.speed
        future_rect = self.rect.copy()
        future_rect.x = next_x

        hit_plant = None
        for plant in plants:
            if future_rect.colliderect(plant.rect):
                hit_plant = plant
                break

        if hit_plant:
            # 식물과 충돌 시 적 이동 멈춤
            # 공격 쿨타임 체크 후 공격
            self.attack_timer += 1
            if self.attack_timer >= self.attack_delay:
                hit_plant.take_damage(self.attack_damage)
                self.attack_timer = 0
        else:
            # 충돌 없으면 앞으로 이동
            self.rect.x = next_x
            self.attack_timer = 0  # 공격 초기화

        # 화면 왼쪽 끝 도달시 게임오버 처리
        if self.rect.x <= 0:
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"reason": "game_over"}))

class RangedPlant(Unit):
    def __init__(self, x, y, bullets):
        super().__init__(x, y, 30, "images/gunner.png")
        self.fire_delay = 75  # 1초 = 60프레임
        self.fire_timer = 0
        self.bullets = bullets
        self.row = self.rect.y // CELL_HEIGHT
        self.attack_range = 200

    def update(self):
        self.update_flash()

        self.fire_timer += 1

        same_row_enemies = [e for e in enemies if e.row == self.row]

        if same_row_enemies and self.fire_timer >= self.fire_delay:
                bullet = Bullet(self.rect.right, self.rect.centery)
                self.bullets.add(bullet)
                self.fire_timer = 0

class MeleePlant(Unit):
    def __init__(self, x, y):
        super().__init__(x, y, 75, "images/cactus.png")
        self.attack_damage = 5
        self.attack_delay = 60  # 근접 공격 아군 유닛 공격 속도 (60프레임 기준 60 = 1초)
        self.attack_timer = 0

    def update(self, enemies):
        self.update_flash()
        self.attack_timer += 1

        # 공격 범위 확장 (오른쪽으로 1칸 정도)
        attack_range = self.rect.copy()
        attack_range.width += CELL_WIDTH  # 오른쪽으로 1칸 정도 확장

        for enemy in enemies:
            if attack_range.colliderect(enemy.rect):
                if self.attack_timer >= self.attack_delay:
                    enemy.take_damage(self.attack_damage)
                    self.attack_timer = 0
                    break

class ShieldPlant(Unit):
    def __init__(self, x, y):
        super().__init__(x, y, 150, "images/shield.png")

    def update(self):
        self.update_flash()

class NormalEnemy(Enemy):
    def __init__(self, x, y, kill_callback = None):
        super().__init__(x, y, 50, "images/normal.png", kill_callback)
        self.speed = 1
        self.attack_delay = 60
        self.attack_damage = 3

class FastEnemy(Enemy):
    def __init__(self, x, y, kill_callback = None):
        super().__init__(x, y, 20, "images/bolt.png", kill_callback)
        self.speed = 2
        self.hp = 20
        self.attack_delay = 45
        self.attack_damage = 2
        self.image.fill((255, 165, 0)) # 주황색, 이미지 여기에 채우기
        pygame.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 2)
    
class TankEnemy(Enemy):
    def __init__(self, x, y, kill_callback = None):
        super().__init__(x, y, 100, "images/bulldozer.png", kill_callback)
        self.speed = 1
        self.hp = 100
        self.attack_delay = 120
        self.attack_damage = 6
        self.image.fill((100, 100, 255))
        pygame.draw.rect(self.image, (0, 0, 0), self.image.get_rect(), 2)

class RangedEnemy(Enemy):
    def __init__(self, x, y, enemy_bullets, kill_callback = None):
        super().__init__(x, y, 30, "images/ranged.png", kill_callback)
        self.image.fill((255, 100, 100))
        self.hp = 20
        self.speed = 1
        self.shoot_delay = 75
        self.shoot_timer = 0
        self.enemy_bullets = enemy_bullets

    def update(self, plants):
        self.update_flash()
        self.shoot_timer += 1

        attack_range = CELL_WIDTH * 5
        should_attack = False
        should_move = True  # 이동 여부 플래그

        # 공격 판단
        for plant in plants:
            distance_x = self.rect.x - plant.rect.x
            same_row = abs(self.rect.centery - plant.rect.centery) < 40
            if 0 < distance_x <= attack_range and same_row:
                should_attack = True
                should_move = False  # 공격 중엔 이동 멈춤
                break

        # 이동 전 예측 위치 계산
        next_x = self.rect.x - self.speed
        future_rect = self.rect.copy()
        future_rect.x = next_x

        # 식물이랑 충돌 검사
        if should_move:
            for plant in plants:
                if future_rect.colliderect(plant.rect):
                    should_move = False     #이동 취소
                    break

        # 실제 이동
        if should_move:
            self.rect.x = next_x

        # 공격 처리
        if should_attack and self.shoot_timer >= self.shoot_delay:
            bullet = EnemyBullet(self.rect.left, self.rect.centery)
            self.enemy_bullets.add(bullet)
            self.shoot_timer = 0

        # 화면 밖으로 나가면 게임 오버 이벤트
        if self.rect.x <= 0:
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"reason": "game_over"}))


class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((8, 8))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = -5

    def update(self, plants):
        prev_x = self.rect.x
        self.rect.x += self.speed

        movement_rect = self.rect.union(pygame.Rect(prev_x, self.rect.y, self.rect.width, self.rect.height))

        # 충돌 처리 부분
        hit_plants = [plant for plant in plants if movement_rect.colliderect(plant.rect)]
        for hit_plant in hit_plants:
            hit_plant.take_damage(2)
            self.kill()
            break   # 한 번 맞으면 탄환 소멸

        if self.rect.right < 0:
            self.kill()

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (0, 0, 0), (5, 5), 5)  # 원형 탄환
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 5

    def update(self, enemies):
        self.rect.x += self.speed

        # 적 유닛과 충돌 처리
        hit_enemy = pygame.sprite.spritecollideany(self, enemies)
        if hit_enemy:
            hit_enemy.take_damage(3)
            self.kill()

        # 화면 밖으로 나가면 삭제
        if self.rect.x > WIDTH:
            self.kill()

plants = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bullets = pygame.sprite.Group()
enemy_bullets = pygame.sprite.Group()

enemy_spawn_timer = 0
ENEMY_SPAWN_INTERVAL = FPS * 5


class ConveyorCard(pygame.sprite.Sprite):
    def __init__(self, plant_type, x, y, index):
        super().__init__()
        self.plant_type = plant_type
        # self.image = pygame.Surface((50, 50))
        # self.image.fill(self.get_color())
        image_paths = {
            "ranged" : "images/gunner.png",
            "melee" : "images/cactus.png",
            "shield" : "images/shield.png"
        }
        self.image = load_image(image_paths[self.plant_type], (70, 70))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0
        self.index = index
        self.target_x = x

    def update(self):
        if not self.dragging:
            if self.rect.x < self.target_x:
                self.rect.x += 2
                if self.rect.x > self.target_x:
                    self.rect.x = self.target_x
            elif self.rect.x > self.target_x:
                self.rect.x -= 2
                if self.rect.x < self.target_x:
                    self.rect.x = self.target_x

class ConveyorBelt:
    def __init__(self, y=0):
        self.cards = pygame.sprite.Group()
        self.spawn_timer = 0
        self.spawn_interval = 200   # 카드 생성 간격
        self.y = y
        self.card_count = 0     # 카드 쌓인 양

        self.card_list = []     # 카드 순서 유지용 리스트
        self.y = y


    def update(self):
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            if len(self.card_list) < 5:
                self.spawn_card()
                self.spawn_timer = 0

        self.cards.update()

    def spawn_card(self):
        plant_type = random.choice(USER_PLANTS)
        x = -60
        y = get_cell_center(0, 0)[1]
        index = len(self.card_list)
        card = ConveyorCard(plant_type, x, y, index)
        card.target_x = WIDTH - ((index + 2) * CELL_WIDTH) # 가장 오른쪽에서 2칸 띄기
        self.cards.add(card)
        self.card_list.append(card)

    def remove_card(self, card):
        if card in self.card_list:
            self.card_list.remove(card)
            card.kill()
            # 인덱스 재정렬, 위치 업데이트
            for i, c in enumerate(self.card_list):
                c.index = i
                c.target_x = WIDTH - ((i + 2) * CELL_WIDTH) # 가장 오른쪽에서 2칸 띄기


    def draw(self, surface):
        self.cards.draw(surface)

class Button:
    def __init__(self, rect, text, callback):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = pygame.font.SysFont(None, 36)
        self.color = (100, 100, 100)
    
    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()

def draw_grid():
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            rect = pygame.Rect(col * CELL_WIDTH, row * CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)

            if row == 0:
                pygame.draw.rect(screen, (230, 230, 230), rect)

                if col == 0:
                    pygame.draw.line(screen, (180, 180, 180), (0, CELL_HEIGHT), (WIDTH, CELL_HEIGHT), 1)

            else:
                pygame.draw.rect(screen, (255, 255, 255), rect)
                pygame.draw.rect(screen, (200, 200, 200), rect, 1)


def get_grid_pos(mouse_pos):
    x, y = mouse_pos
    col = x // CELL_WIDTH
    row = y // CELL_HEIGHT
    return (col, row)

def get_cell_center(col, row):
    x = col * CELL_WIDTH + CELL_WIDTH // 2 - UNIT_SIZE[0] // 2
    y = row * CELL_HEIGHT + CELL_HEIGHT // 2 - UNIT_SIZE[1] // 2
    return x, y

def get_row_from_y(y, row_heigt=60):
    return y // row_heigt


def main():
    global enemy_spawn_timer
    running = True
    killed_enemies_count = 0
    dragging_card = None
    
    TRASH_CAN_RECT = pygame.Rect(WIDTH - 60, 10, 50, 50)
    TRASH_CAN_COLOR = (100, 100, 100)

    FONT_MEDIUM = pygame.font.SysFont(None, 36)
    FONT_LARGE = pygame.font.SysFont(None, 72)

    def draw_trash_can(surface):
        pygame.draw.rect(surface, TRASH_CAN_COLOR, TRASH_CAN_RECT)
        pygame.draw.rect(surface, (0, 0, 0), TRASH_CAN_RECT, 2)
        font = pygame.font.SysFont(None, 14)
        text = font.render("TRASH", True, (255, 255, 255))
        surface.blit(text, (TRASH_CAN_RECT.x + 10, TRASH_CAN_RECT.y + 10))

    def on_enemy_killed():
        nonlocal killed_enemies_count
        killed_enemies_count += 1

    ENEMY_TYPES = [
        lambda x, y: NormalEnemy(x, y, kill_callback = on_enemy_killed),
        lambda x, y: FastEnemy(x, y, kill_callback = on_enemy_killed),
        lambda x, y: TankEnemy(x, y, kill_callback = on_enemy_killed),
        lambda x, y: RangedEnemy(x, y, enemy_bullets, kill_callback = on_enemy_killed)
        ]

    conveyor = ConveyorBelt()

    STATE_MENU = 0
    STATE_PLAYING = 1
    STATE_GAME_OVER = 2

    state = STATE_MENU

    start_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 50, 200, 50)
    quit_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 20, 200, 50)
    back_to_menu_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 40, 200, 50)


    while running:

        conveyor.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == STATE_MENU:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if start_button_rect.collidepoint(event.pos):
                        state = STATE_PLAYING
                        killed_enemies_count = 0
                        enemy_spawn_timer = 0
                        conveyor = ConveyorBelt()
                        plants.empty()
                        enemies.empty()
                        bullets.empty()
                        enemy_bullets.empty()
                        dragging_card = None

                    elif quit_button_rect.collidepoint(event.pos):
                        running = False
                
            elif state == STATE_PLAYING:
                if event.type == pygame.USEREVENT and event.dict.get("reason") == "game_over":
                    state = STATE_GAME_OVER
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for card in conveyor.cards:
                        if card.rect.collidepoint(event.pos):
                            card.dragging = True
                            dragging_card = card
                            card.offset_x = event.pos[0] - card.rect.x
                            card.offset_y = event.pos[1] - card.rect.y
                            break

                elif event.type == pygame.MOUSEBUTTONUP:
                    if dragging_card is not None:
                        dragging_card.dragging = False
                        col, row = get_grid_pos(event.pos)

                        # 쓰레기통에 버린 경우
                        if TRASH_CAN_RECT.collidepoint(event.pos):
                                conveyor.remove_card(dragging_card)
                        else:
                            col, row = get_grid_pos(event.pos)

                            # 1. 배치 가능한 행, 열인지 확인
                            if 0 <= col < GRID_COLS and 1 <= row < GRID_ROWS:
                                x, y = get_cell_center(col, row)

                                # 2. 해당 칸에 적 유닛이 있는지 체크
                                enemy_in_cell = False
                                for enemy in enemies:
                                    enemy_col = enemy.rect.centerx // CELL_WIDTH
                                    enemy_row = enemy.rect.centery // CELL_HEIGHT
                                    if enemy_col == col and enemy_row == row:
                                        enemy_in_cell = True
                                        break

                                # 3. 적이 없고, 식물도 없으면 배치 허용
                                if not enemy_in_cell and not any(
                                    plant.rect.collidepoint(x + UNIT_SIZE[0]//2, y + UNIT_SIZE[1]//2) for plant in plants
                                ):
                                    if dragging_card.plant_type == "ranged":
                                        plants.add(RangedPlant(x, y, bullets))
                                    elif dragging_card.plant_type == "melee":
                                        plants.add(MeleePlant(x, y))
                                    elif dragging_card.plant_type == "shield":
                                        plants.add(ShieldPlant(x, y))

                                    conveyor.remove_card(dragging_card)  # 카드 제거 및 재배치
                                else:
                                    # 적이 있거나 식물이 있으면 원복
                                    dragging_card.rect.topleft = (dragging_card.target_x, get_cell_center(0, 0)[1])
                                    dragging_card.target_x = WIDTH - ((dragging_card.index + 2) * CELL_WIDTH)
                            else:
                                # 범위 밖일 경우에도 원복
                                dragging_card.rect.topleft = (dragging_card.target_x, get_cell_center(0, 0)[1])
                                dragging_card.target_x = WIDTH - ((dragging_card.index + 2) * CELL_WIDTH)

                            dragging_card = None

                elif event.type == pygame.MOUSEMOTION and dragging_card:
                    dragging_card.rect.x = event.pos[0] - dragging_card.offset_x
                    dragging_card.rect.y = event.pos[1] - dragging_card.offset_y
                elif event.type == pygame.USEREVENT and event.dict.get("reason") == "game_over":
                    state = STATE_GAME_OVER

            elif state == STATE_GAME_OVER:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_to_menu_rect.collidepoint(event.pos):
                        state = STATE_MENU



        if state == STATE_MENU:
            screen.fill(WHITE)
            # 메뉴 화면 그리기
            title_text = FONT_LARGE.render("Plant vs Zombie Prototype", True, (0, 0, 0))                    
            screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 4))
            # 버튼 그리기
            pygame.draw.rect(screen, (0, 200, 0), start_button_rect)
            start_text = FONT_MEDIUM.render("Game Start", True, (255, 255, 255))
            screen.blit(start_text, (start_button_rect.x + 50, start_button_rect.y + 10))
                # 버튼 그리기
            pygame.draw.rect(screen, (200, 0, 0), quit_button_rect)
            quit_text = FONT_MEDIUM.render("Quit Game", True, (255, 255, 255))
            screen.blit(quit_text, (quit_button_rect.x + 50, quit_button_rect.y + 10))

        elif state == STATE_PLAYING:
            screen.fill(WHITE)
            enemy_spawn_timer += 1
            if enemy_spawn_timer >= ENEMY_SPAWN_INTERVAL:
                row = random.randint(1, GRID_ROWS - 1)
                x, y = get_cell_center(GRID_COLS, row)
                enemy_class = random.choice(ENEMY_TYPES)
                enemies.add(enemy_class(x, y))
                enemy_spawn_timer = 0


            for plant in plants:
                if isinstance(plant, RangedPlant) or isinstance(plant, ShieldPlant):
                        plant.update()
                elif isinstance(plant, MeleePlant):
                    plant.update(enemies)

            enemies.update(plants)
            bullets.update(enemies)
            enemy_bullets.update(plants)
            conveyor.update()
                
            draw_grid()
            draw_trash_can(screen)

            font = pygame.font.SysFont(None, 30)
            text_surface = font.render(f"Kill Count : {killed_enemies_count}", True, (0, 0, 0))
            text_pos = (WIDTH - 200, 10)  # 화면 오른쪽 위 위치, 적당히 조절 가능
            screen.blit(text_surface, text_pos)

            plants.draw(screen)
            enemies.draw(screen)
            bullets.draw(screen)
            conveyor.draw(screen)
            enemy_bullets.draw(screen)

        elif state == STATE_GAME_OVER:
            screen.fill(WHITE)
            # 게임 오버 화면
            game_over_text = FONT_LARGE.render("GAME OVER!", True, (255, 0, 0))
            screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 3))

            pygame.draw.rect(screen, (0, 100, 200), back_to_menu_rect)
            back_text = FONT_MEDIUM.render("Back to Menu", True, (255, 255, 255))
            screen.blit(back_text, (back_to_menu_rect.x + 30, back_to_menu_rect.y + 10))

            # 죽인 적 수 표시
            kill_count_text = FONT_MEDIUM.render(f"Kill Count: {killed_enemies_count}", True, (0, 0, 0))
            screen.blit(kill_count_text, (WIDTH // 2 - kill_count_text.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()
        clock.tick(FPS)


    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()