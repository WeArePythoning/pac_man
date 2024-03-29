import random

from livewires import games, color


SCREEN_WIDTH = 28 * 16  # = 459, pixels
SCREEN_HEIGHT = 31 * 16  # = 496, pixels
MAP_HEIGHT = 31  # chars (ceiis)
MAP_WIDTH = 28  # chars (cells)
PIXELS_PER_CHAR = SCREEN_WIDTH / MAP_WIDTH


games.init(screen_width=SCREEN_WIDTH, screen_height=SCREEN_HEIGHT, fps=50)


class Game:

    def __init__(self):
        background_image = games.load_image("assets/background.bmp")
        games.screen.background = background_image
        self.ghosts = []
        self.walls, (pacman_i, pacman_j), ghost_s, self.points = self.read_map()

        for point_coord in self.points:
            point_i, point_j, size = point_coord
            point_x, point_y = map_to_screen(point_i, point_j)
            Point(point_x, point_y, size)

        color_number = 0
        colors = [Ghost.PINK, Ghost.ORANGE, Ghost.RED, Ghost.BLUE]

        Ghost.init()
        for coordinates in ghost_s:
            ghost_i, ghost_j = coordinates
            ghost = Ghost(self, ghost_i, ghost_j, color=colors[color_number])
            color_number+=1
            self.ghosts.append(ghost)

        self.pacman = Pacman(self, pacman_i, pacman_j)

        self.score = games.Text(
            value=0,
            size=30,
            color=color.yellow,
            x=16,
            y=10,
            is_collideable=False
        )

        games.screen.add(self.score)
        games.screen.mainloop()
        games.screen.clear()

    def make_ghosts_dumb(self):
        for ghost in self.ghosts:
            i, j = ghost.pos
            DumbGhost(self, i, j, ghost.color)
            ghost.destroy()

    def return_ghosts_origin(self):
        for ghost in self.ghosts:
            ghost.return_to_spawn()

    def is_on_same_row(self, y):
        return -PIXELS_PER_CHAR <= self.pacman.y - y <= PIXELS_PER_CHAR

    def is_on_same_column(self, x):
        return -PIXELS_PER_CHAR <= self.pacman.x - x <= PIXELS_PER_CHAR

    def is_wall_between(self, x, y):
        if self.is_on_same_row(y):
            if self.pacman.x > x:
                step = 1
            else:
                step = -1
            for x_ in range(int(x), int(self.pacman.x), step):
                if self.is_wall_pixel(x_, y):
                    return True
            return False

        if self.is_on_same_column(x):
            if self.pacman.y > y:
                step = 1
            else:
                step = -1
            for y_ in range(int(y), int(self.pacman.y), step):
                if self.is_wall_pixel(x, y_):
                    return True
            return False

        return True

    def looks_towards(self, x, y, angle):
        if angle == 0:
            return self.pacman.x > x
        if angle == 90:
            return self.pacman.y > y
        if angle == 180:
            return self.pacman.x < x
        if angle == 270:
            return self.pacman.y < y

    def update_score(self, score):
        self.score.value = score

    def in_the_middle_char(self, x, y):
        x_on_center = (x - (PIXELS_PER_CHAR - 1) / 2) % PIXELS_PER_CHAR == 0
        y_on_center = (y - (PIXELS_PER_CHAR - 1) / 2) % PIXELS_PER_CHAR == 0
        return x_on_center and y_on_center

    def is_wall_pixel(self, x, y):
        i, j = map(round, screen_to_map(x, y))
        try:
            return self.walls[i][j]
        except IndexError:
            return False

    def read_map(self):
        line_n = 0
        pacman_i = 0
        pacman_j = 0
        walls = []
        ghost_s = []
        points = []
        walls_file = open("assets/map.txt")
        for line in walls_file:
            row =  []
            char_n = 0
            for char in line:
                if char == "#":
                    row.append(True)
                elif char == " ":
                    row.append(False)
                elif char == "W":
                    row.append(False)
                    ghost_s.append((line_n, char_n))
                elif char == "C":
                    row.append(False)
                    pacman_i = line_n
                    pacman_j = char_n
                elif char == ".":
                    row.append(False)
                    points.append((line_n, char_n, Point.SMALL_POINT))
                elif char == "O":
                    row.append(False)
                    points.append((line_n, char_n, Point.BIG_POINT))
                char_n += 1
            line_n += 1
            walls.append(row)
        walls_file.close()
        return walls, (pacman_i, pacman_j), ghost_s, points


class Character(games.Animation):
    """Абстрактный - создаём объекты только из производных: Pacman, Ghost"""
    SPEED = 1

    def __init__(self, game, images, i, j):
        self.game = game
        x, y = map_to_screen(i, j)
        super().__init__(images = images, x=x, y=y, repeat_interval=4)
        games.screen.add(self)
        self.change_direction_key = None

    @property
    def pos(self):
        return screen_to_map(self.x, self.y)

    def update(self):
        if self.x < 0:
            self.x += games.screen.width
        if self.x > games.screen.width:
            self.x -= games.screen.width
        if self.is_on_wall():
            # снимаем со стены и останавливаем
            self.x -= self.dx
            self.y -= self.dy
            self.stop()
            self.after_on_wall()
        else:
            self.maybe_choose_new_direction()

            if self.change_direction_key \
                    and self.game.in_the_middle_char(self.x, self.y):
                # наступил правильный момент - поворачиваем
                x_, y_ , angle = {
                    games.K_LEFT: (-1, 0, 180),
                    games.K_RIGHT: (1, 0, 0),
                    games.K_UP: (0, -1, 270),
                    games.K_DOWN: (0, 1, 90),
                } [self.change_direction_key]
                is_wall_in_desired_direction = self.game.is_wall_pixel(
                    self.x + x_*PIXELS_PER_CHAR,
                    self.y + y_*PIXELS_PER_CHAR
                )
                if not is_wall_in_desired_direction:
                    self.rotate(angle)
                    self.move(x_, y_)
                    self.change_direction_key = None

    def is_on_wall(self):
        # достаточно проверить лишь две противоположных угловых точки
        for d in (-1, 1):
            delta = d * (PIXELS_PER_CHAR - 1) / 2
            if self.game.is_wall_pixel(self.x + delta, self.y + delta):
                return True
        return False

    def maybe_choose_new_direction(self):
        pass

    def after_on_wall(self):
        pass

    def rotate(self):
        return angle

    def move(self, x_, y_):
        self.dx = x_ * self.SPEED
        self.dy = y_ * self.SPEED

    def stop(self):
        self.dx = 0
        self.dy = 0


class Pacman(Character):
    images_init = ["assets/pac_man/close.bmp"]
    images_move = [
        games.load_image('assets/pac_man/' + filename + '.bmp')
        for filename in ["right_1", 'right_2', "close"]
    ]
    images_stop = [games.load_image("assets/pac_man/right_1.bmp")]
    score = 0

    def __init__(self, game, i, j):
        super().__init__(game, Pacman.images_init, i, j)

    def move(self, x_, y_):
        self.images = Pacman.images_move
        super().move(x_, y_)

    def stop(self):
        self.images = Pacman.images_stop
        super().stop()

    def maybe_choose_new_direction(self):
        # сохраняет клавишу, которую нажал пользователь, для поворота в
        # правильный момент
        for key in (
            games.K_LEFT,
            games.K_RIGHT,
            games.K_UP,
            games.K_DOWN
        ):
            if games.keyboard.is_pressed(key):
                self.change_direction_key = key

    def update(self):
        if self.overlapping_sprites:
            for sprite in self.overlapping_sprites:
                if isinstance(sprite, Ghost):
                    self.destroy()
                    DeadPacman(self.x, self.y)
                if isinstance(sprite, DumbGhost):
                    sprite.return_to_spawn()
                elif (self.x, self.y) == (sprite.x, sprite.y):
                    if sprite.value == 20:
                        self.game.make_ghosts_dumb()
                    self.score += sprite.value
                    self.game.update_score(self.score)
                    sprite.destroy()
        super().update()

    def rotate(self, angle):
        self.angle = angle


class DeadPacman(games.Animation):
    images = ["assets/pac_man/die/" + str(n) + '.bmp' for n in range(11)]

    def __init__(self, x, y):
        super().__init__(
            images = DeadPacman.images,
            x=x, y=y,
            repeat_interval=4, n_repeats=1,
            is_collideable=False
        )
        games.screen.add(self)


class Ghost(Character):
    PINK=1
    RED=2
    BLUE=3
    ORANGE=4

    IMAGES = {
        PINK: 'pink',
        RED: 'red',
        BLUE: 'blue',
        ORANGE: 'orange',
    }

    @classmethod
    def init(cls):
        for color_number in cls.IMAGES:  # color_number <- keys (PINK, RED,...)
            color_name = cls.IMAGES[color_number]  # ('pink, 'red',...)
            all_direction_images = {
                0: [color_name + '/right', color_name + '/right_2'],
                90: [color_name + '/down', color_name + '/down_2'],
                180: [color_name + '/left', color_name + '/left_2'],
                270: [color_name + '/up', color_name + '/up_2']
            }
            # convert file names to file objects
            for angle in all_direction_images:
                image_names = all_direction_images[angle]
                images = [
                    games.load_image('assets/ghosts/' + name + '.bmp')
                    for name in image_names
                ]
                all_direction_images[angle] = images
            cls.IMAGES[color_number] = all_direction_images

    def __init__(self, game, i, j, color):
        self.color = color
        self.all_direction_images = Ghost.IMAGES[color]
        super().__init__(game, self.all_direction_images[0], i, j)

    def maybe_choose_new_direction(self):
        if not self.is_pacman_visible():
            rand = random.randint(1, 100)
            if rand == 25:
                self.choose_new_direction()

    def is_pacman_visible(self):
        return (
            not self.game.is_wall_between(self.x, self.y)
            and
            self.game.looks_towards(self.x, self.y, self.angle)
        )

    def choose_new_direction(self):
        key_name = [games.K_LEFT, games.K_RIGHT, games.K_UP, games.K_DOWN]
        key_index = random.randint(0, 3)
        self.change_direction_key = key_name[key_index]

    def after_on_wall(self):
        self.choose_new_direction()

    def rotate(self, angle):
        self.images = self.all_direction_images[angle]


class DumbGhost(Character):
    images = ["assets/ghosts/dark.bmp", "assets/ghosts/dark_2.bmp"]

    def __init__(self, game, i, j, color):
        self.colors = [1, 2, 3, 4]
        self.color = color
        self.game = game
        self.origin = (i, j)
        super().__init__(game, DumbGhost.images, i, j)
        self.time = 0

    def update(self):
        self.time += 1
        if self.time == 500:
            self.destroy()
            for color in self.colors:
                Ghost(self.game, self.x, self.y, color)
        super().update()

    def return_to_spawn(self):
        self.destroy()
        for c in self.colors:
            if self.color == c:
                self.colors.remove(self.color)
        Ghost(self.game, *self.origin, self.color)


class Point(games.Animation):
    SMALL_POINT = 0
    BIG_POINT = 1

    POINT_IMAGES = {
        SMALL_POINT: ["assets/point/small.bmp"],
        BIG_POINT: ["assets/point/big.bmp", "assets/point/big_blink.bmp"]
    }

    POINT_VALUE = {
        SMALL_POINT: 10,
        BIG_POINT: 20
    }

    def __init__(self, x, y, size):
        self._value = Point.POINT_VALUE[size]
        super().__init__(
            images=Point.POINT_IMAGES[size],
            x=x, y=y, repeat_interval=8
        )
        games.screen.add(self)

    @property
    def value(self):
        return self._value


def screen_to_map(x, y):  # x = 0..458 -> 0..27, 46 -> 3
    i = (y + 0.5) / PIXELS_PER_CHAR - 0.5
    j = (x + 0.5) / PIXELS_PER_CHAR - 0.5
    return i, j


def map_to_screen(i, j):
    x = (j + 0.5) * PIXELS_PER_CHAR - 0.5
    y = (i + 0.5) * PIXELS_PER_CHAR - 0.5
    return x, y


Game()
