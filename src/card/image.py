import datetime
import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
from colorsys import rgb_to_hsv, hsv_to_rgb
import numpy as np
from sklearn.cluster import KMeans
import requests

IMAGE_HEIGHT = 940
IMAGE_WIDTH = 1500
TORUS_REGULAR = "src/resources/fonts/torus/Torus-Regular.otf"
TORUS_BOLD = "src/resources/fonts/torus/Torus-Bold.otf"
TORUS_SEMIBOLD = "src/resources/fonts/torus/Torus-SemiBold.otf"
DEFAULT_COVER = "src/resources/images/default_cover.png"

image = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)


def draw_background():
    corner_radius = calculate_corner_radius(IMAGE_WIDTH, IMAGE_HEIGHT, 5)
    draw.rounded_rectangle(
        (0, 0, IMAGE_WIDTH, IMAGE_HEIGHT), fill="#2E3835", radius=corner_radius
    )


def draw_header_background(avatar_color, cover_url):
    if cover_url:
        res = requests.get(cover_url)
        if res.status_code == requests.codes.ok:
            cover = res.content
        else:
            cover = DEFAULT_COVER
    else:
        cover = DEFAULT_COVER

    header_image = fit_image_to_aspect_ratio(cover, IMAGE_WIDTH / (IMAGE_HEIGHT // 4))

    header_image = header_image.resize(
        (IMAGE_WIDTH, IMAGE_HEIGHT // 4), resample=Image.LANCZOS
    )

    header_image_x = 0
    header_image_y = 0

    corner_radius = calculate_corner_radius(header_image.width, header_image.height, 20)
    mask = Image.new("L", header_image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), header_image.size], corner_radius, fill=255)

    gradient_image = Image.new("RGBA", header_image.size)
    gradient_draw = ImageDraw.Draw(gradient_image)

    start_opacity = 255
    end_opacity = 153  # 60%

    for x in range(header_image.width):
        t = x / (header_image.width - 1)

        opacity = int((1 - t) * start_opacity + t * end_opacity)

        color = avatar_color + (opacity,)
        gradient_draw.line([(x, 0), (x, header_image.height - 1)], fill=color)

    header_image = Image.alpha_composite(header_image, gradient_image)

    image.paste(header_image, (header_image_x, header_image_y), mask)


def draw_avatar(avatar_data):
    avatar_size = (IMAGE_HEIGHT // 4, IMAGE_HEIGHT // 4)
    avatar_image = (
        Image.open(io.BytesIO(avatar_data))
        .resize(avatar_size, resample=Image.LANCZOS)
        .convert("RGBA")
    )
    avatar_x = 0
    avatar_y = 0

    corner_radius = calculate_corner_radius(avatar_size[0], avatar_size[1], 15)
    mask = Image.new("L", avatar_size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), avatar_size], corner_radius, fill=255)

    avatar_with_rounded_corners = Image.new("RGBA", avatar_size, (0, 0, 0, 0))
    avatar_with_rounded_corners.paste(avatar_image, mask=mask)

    image.paste(
        avatar_with_rounded_corners,
        (avatar_x, avatar_y),
        mask=avatar_with_rounded_corners,
    )


def draw_user_group_line(user_data):
    profile_color = user_data["profile_colour"]

    if profile_color is None or profile_color == "-1":
        profile_color = "#FF66AB" if user_data["is_supporter"] else "#0087CA"

    thickness = 20
    rounding_radius = 10
    header_height = IMAGE_HEIGHT // 4
    start = (int(header_height + thickness * 1.5), header_height // 6)
    end = (int(header_height + thickness * 1.5), (header_height // 6) * 5)

    draw.line([start, end], fill=profile_color, width=thickness)

    draw.ellipse(
        (
            start[0] - rounding_radius + 1,
            start[1] - rounding_radius,
            start[0] + rounding_radius,
            start[1] + rounding_radius,
        ),
        fill=profile_color,
    )

    draw.ellipse(
        (
            end[0] - rounding_radius + 1,
            end[1] - rounding_radius,
            end[0] + rounding_radius,
            end[1] + rounding_radius,
        ),
        fill=profile_color,
    )


def draw_username(username):
    font_size = 64
    font = ImageFont.truetype(TORUS_SEMIBOLD, font_size)
    text_color = "white"
    shadow_color = (0, 0, 0, 64)

    username_x = IMAGE_WIDTH // 4.8
    username_y = IMAGE_HEIGHT // 44

    shadow_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_image)
    shadow_position = (username_x, username_y + 4)
    shadow_draw.text(shadow_position, username, font=font, fill=shadow_color)
    shadow_image_blur = shadow_image.filter(ImageFilter.GaussianBlur(2))

    image.alpha_composite(shadow_image_blur)

    draw.text((username_x, username_y), username, font=font, fill=text_color)


def draw_osu_logo():
    osu_logo_x = int(IMAGE_WIDTH // 4.8)
    osu_logo_y = int(IMAGE_HEIGHT // 8.5)

    osu_logo = Image.open("src/resources/images/osu.png")

    image.paste(osu_logo, (osu_logo_x, osu_logo_y), osu_logo)


def draw_user_group_pill(groups_string):
    groups = json.loads(groups_string)
    primary_group = groups[0]
    group_name = primary_group["short_name"]
    group_color = primary_group["colour"]

    padding = 40
    pill_height = 128

    font_size = 96
    font = ImageFont.truetype(TORUS_BOLD, font_size)
    text_width, text_height = font.getsize(group_name)

    pill_width = text_width + padding * 2

    group_pill = Image.new("RGBA", (pill_width, pill_height), (0, 0, 0, 0))
    group_draw = ImageDraw.Draw(group_pill)
    group_draw.rounded_rectangle(
        (0, 0, pill_width, pill_height), fill=(0, 0, 0, 128), radius=64
    )

    text_x = pill_width // 2
    text_y = (pill_height // 2) - 5

    group_draw.text(
        (text_x, text_y), group_name, fill=group_color, font=font, anchor="mm"
    )

    return group_pill


def draw_followers_pill(follower_count):
    follower_count_string = f"{follower_count:,}"
    user_icon = Image.open("src/resources/images/user-solid.png").convert("RGBA")
    user_icon.thumbnail((80, 80), Image.LANCZOS)

    padding = 40
    pill_height = 128
    text_padding = 20

    font_size = 96
    font = ImageFont.truetype(TORUS_SEMIBOLD, font_size)
    text_width, text_height = font.getsize(follower_count_string)

    pill_width = text_padding * 2 + user_icon.width + text_width + padding * 2

    followers_pill = Image.new("RGBA", (pill_width, pill_height), (0, 0, 0, 0))
    followers_draw = ImageDraw.Draw(followers_pill)
    followers_draw.rounded_rectangle(
        (0, 0, pill_width, pill_height), fill=(0, 0, 0, 128), radius=64
    )
    followers_pill.paste(
        user_icon, (padding + 10, (pill_height - user_icon.height) // 2), user_icon
    )

    text_x = padding + user_icon.width + text_padding + 10

    text_y = (pill_height - text_height) // 2 - (15 if follower_count < 1000 else 5)

    followers_draw.text(
        (text_x, text_y), follower_count_string, fill=(255, 255, 255), font=font
    )

    return followers_pill


def draw_supporter_pill(support_level):
    heart_icon = (
        Image.open("src/resources/images/heart-solid.png")
        .convert("RGBA")
        .resize((80, 80), Image.LANCZOS)
    )

    padding = 40
    pill_height = 128
    pill_width = heart_icon.width * support_level + padding * 2

    supporter_pill = Image.new("RGBA", (pill_width, pill_height), (0, 0, 0, 0))
    supporter_draw = ImageDraw.Draw(supporter_pill)
    supporter_draw.rounded_rectangle(
        (0, 0, pill_width, pill_height), fill="#EB549C", radius=64
    )

    start_x = (pill_width - (heart_icon.width * support_level)) // 2

    for i in range(support_level):
        supporter_pill.alpha_composite(
            heart_icon,
            (start_x + i * heart_icon.width, (pill_height - heart_icon.height) // 2),
        )

    return supporter_pill


def draw_pills(pills):
    margin = 20
    x = int(IMAGE_WIDTH // 3.5)
    y = int(IMAGE_HEIGHT // 8.5)

    for pill in pills:
        pill = pill.resize((pill.width // 2, pill.height // 2), Image.LANCZOS)
        image.alpha_composite(pill, (x, y))

        x += pill.width + margin


def draw_level(level):
    # No idea how the hexagon design from flytes designs is meant to work
    # so we just draw the same image for everyone ¯\_(ツ)_/¯
    level_hexagon = Image.open("src/resources/images/level-hexagon.png")
    font_size = 64
    font = ImageFont.truetype(TORUS_REGULAR, font_size)
    text_color = (255, 255, 255)

    hexagon_x = int(IMAGE_WIDTH // 1.18)
    hexagon_y = int((IMAGE_HEIGHT / 4 - level_hexagon.height) // 2)

    image.paste(level_hexagon, (hexagon_x, hexagon_y), level_hexagon)

    text_x = int(IMAGE_WIDTH // 1.094)
    text_y = int((IMAGE_HEIGHT / 4) / 2 - font_size / 8)

    draw.text(
        (text_x, text_y), f"{int(level)}", fill=text_color, font=font, anchor="mm"
    )


def draw_flag(country_code):
    unicode_hex = convert_country_code_to_unicode(country_code)
    flag_path = f"src/resources/twemoji/{unicode_hex}.png"
    if os.path.exists(flag_path):
        country_flag = Image.open(flag_path).convert("RGBA")
    else:
        country_flag = Image.open("src/resources/images/unknown.png").convert("RGBA")

    x = int(IMAGE_WIDTH / 1.25)
    y = int((IMAGE_HEIGHT / 4 - country_flag.height) / 2)

    image.paste(country_flag, (x, y), country_flag)


def draw_join_date(join_date):
    date_string = join_date.strftime("%d %B %Y")
    relative_time = (datetime.datetime.now() - join_date).days
    relative_time_string = f" ({relative_time}d ago)"

    font_size = 42
    font = ImageFont.truetype(TORUS_REGULAR, font_size)
    bold_font = ImageFont.truetype(TORUS_SEMIBOLD, font_size)

    x = int(IMAGE_WIDTH // 4.8)
    y = int(IMAGE_HEIGHT // 5.3)

    draw.text((x, y), "Joined ", fill="white", font=font)
    draw.text(
        (x + font.getsize("Joined ")[0], y),
        date_string,
        fill="white",
        font=bold_font,
    )
    draw.text(
        (
            x + font.getsize("Joined ")[0] + bold_font.getsize(date_string)[0],
            y,
        ),
        relative_time_string,
        fill="white",
        font=font,
    )


def draw_header(user_data, avatar_data):
    avatar_color = get_image_color(avatar_data)
    draw_header_background(avatar_color, user_data["cover_url"])
    draw_avatar(avatar_data)
    draw_user_group_line(user_data)
    draw_username(user_data["username"])
    draw_osu_logo()
    pills = []
    if len(json.loads(user_data["groups"] or "[]")) > 0:
        pills.append(draw_user_group_pill(user_data["groups"]))

    pills.append(draw_followers_pill(user_data["follower_count"]))
    if user_data["is_supporter"]:
        pills.append(draw_supporter_pill(user_data["support_level"]))

    draw_pills(pills)
    draw_level(user_data["level"])
    draw_flag(user_data["country_code"])
    draw_join_date(user_data["join_date"])


def draw_card(user_data, avatar_data):
    draw_background()
    draw_header(user_data, avatar_data)

    return image


# Helper functions


def fit_image_to_aspect_ratio(image_input, aspect_ratio):
    if isinstance(image_input, str):
        image = Image.open(image_input)
    else:
        image = Image.open(io.BytesIO(image_input))

    image_width, image_height = image.size
    target_width = int(min(image_width, image_height * aspect_ratio))
    target_height = int(min(image_height, image_width / aspect_ratio))

    new_image = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    new_image.paste(
        image, ((target_width - image_width) // 2, (target_height - image_height) // 2)
    )

    return new_image


def adjust_color_saturation_and_brightness(rgb_color, saturation, brightness):
    hsv_color = rgb_to_hsv(*rgb_color)
    adjusted_hsv = (hsv_color[0], saturation, brightness)
    adjusted_rgb = hsv_to_rgb(*adjusted_hsv)
    normalized_rgb = [int(c * 255) for c in adjusted_rgb]
    return tuple(normalized_rgb)


def get_image_color(image_data):
    image = Image.open(io.BytesIO(image_data)).convert("RGB")

    pixels = np.array(image).reshape(-1, 3)

    kmeans = KMeans(n_init=10, n_clusters=5)
    kmeans.fit(pixels)

    cluster_centers = kmeans.cluster_centers_

    _, counts = np.unique(kmeans.labels_, return_counts=True)

    dominant_color = tuple(map(int, cluster_centers[np.argmax(counts)]))

    if dominant_color == (255, 255, 255) or dominant_color == (0, 0, 0):
        dominant_color = (255, 0, 115)  # osu! Pink

    adjusted_color = adjust_color_saturation_and_brightness(dominant_color, 0.45, 0.3)

    return adjusted_color


def calculate_corner_radius(image_width, image_height, percentage):
    min_dimension = min(image_width, image_height)
    radius = int(min_dimension * (percentage / 100))
    return radius


def convert_country_code_to_unicode(country_code):
    unicode_hex_values = [
        hex(ord(char) - 65 + 0x1F1E6)[2:].upper()
        for char in country_code.upper()
        if char.isalpha()
    ]
    return "-".join(unicode_hex_values)
