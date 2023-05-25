import datetime
import json
from decimal import ROUND_HALF_UP
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import numpy as np
import requests
from card.helpers import (
    get_image_color,
    get_rank_tier,
    calculate_corner_radius,
    convert_country_code_to_unicode,
    fit_image_to_aspect_ratio,
)

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


def draw_score_rank(score_rank):
    header_font_size = 48
    rank_font_size = 96
    tier = get_rank_tier(score_rank)
    colors = tier["colors"]
    header_text = "Score Rank"
    rank_text = f"#{score_rank:,}" if score_rank and score_rank > 0 else "-"

    font_header = ImageFont.truetype(TORUS_SEMIBOLD, header_font_size)
    font_rank = ImageFont.truetype(tier["font_path"], rank_font_size)

    _, _, header_width, header_height = font_header.getbbox(header_text)
    _, _, value_width, value_height = font_rank.getbbox(rank_text)

    width = max(header_width, value_width)
    height = header_height + value_height

    rank_image = Image.new("RGBA", (width, height))
    rank_draw = ImageDraw.Draw(rank_image)

    rank_draw.text((0, 0), header_text, font=font_header, fill="white")

    if len(colors) < 2:
        rank_draw.text((0, header_height), rank_text, font=font_rank, fill=colors[0])

        return rank_image

    start_color = colors[0]
    end_color = colors[1]

    gradient = np.linspace(0, 1, value_height)

    gradient_image = Image.new("RGBA", (value_width, value_height))
    gradient_draw = ImageDraw.Draw(gradient_image)

    for j in range(value_height):
        r = int(start_color[0] + (end_color[0] - start_color[0]) * gradient[j])
        g = int(start_color[1] + (end_color[1] - start_color[1]) * gradient[j])
        b = int(start_color[2] + (end_color[2] - start_color[2]) * gradient[j])
        gradient_color = (r, g, b)

        gradient_draw.line([(0, j), (value_width, j)], fill=gradient_color, width=1)

    alpha_image = Image.new("L", (value_width, value_height))
    alpha_draw = ImageDraw.Draw(alpha_image)
    alpha_draw.text((0, 0), rank_text, font=font_rank, fill=255)

    gradient_image.putalpha(alpha_image)
    rank_image.alpha_composite(gradient_image, (0, header_height))

    return rank_image


def draw_generic_rank(text, rank):
    header_font_size = 48
    rank_font_size = 96

    rank_text = f"#{rank:,}" if rank and rank > 0 else "-"

    font_header = ImageFont.truetype(TORUS_SEMIBOLD, header_font_size)
    font_rank = ImageFont.truetype(TORUS_REGULAR, rank_font_size)

    _, _, header_width, header_height = font_header.getbbox(text)
    _, _, value_width, value_height = font_rank.getbbox(rank_text)

    width = max(header_width, value_width)
    height = header_height + value_height

    rank_image = Image.new("RGBA", (width, height))
    rank_draw = ImageDraw.Draw(rank_image)

    rank_draw.text((0, 0), text, font=font_header, fill="white")
    rank_draw.text((0, header_height), rank_text, font=font_rank, fill="#DBF0E9")

    return rank_image


def draw_ranks(user_data):
    ranks = [
        draw_score_rank(user_data["score_rank"]),
        draw_generic_rank("Global Rank", user_data["global_rank"]),
        draw_generic_rank("Country Rank", user_data["country_rank"]),
    ]

    total_ranks_width = sum(rank.width for rank in ranks)
    num_ranks = len(ranks)
    spacing = (IMAGE_WIDTH - total_ranks_width) // (num_ranks + 1)

    padding = IMAGE_HEIGHT // 30
    y = (IMAGE_HEIGHT // 4) + padding
    x_offset = spacing
    for rank in ranks:
        image.alpha_composite(rank, (x_offset, y))
        x_offset += rank.width + spacing


def draw_stat(header, value):
    height = 128
    header_font = ImageFont.truetype(TORUS_SEMIBOLD, 44)
    stat_font = ImageFont.truetype(TORUS_REGULAR, 60)

    if header in ("Accuracy", "Completion"):
        stat_text = f"{value}%"
    elif header == "Play Time":
        hours = value // 3600
        minutes = (value % 3600) // 60
        stat_text = f"{hours}h {minutes}m"
    else:
        stat_text = f"{value:,}"

    if not header in ("Ranked Score", "Total Score"):
        _, _, header_width, _ = header_font.getbbox(header)
        _, _, value_width, _ = stat_font.getbbox(stat_text)

        width = max(header_width, value_width)

        stat_image = Image.new("RGBA", (width, height))
        stat_draw = ImageDraw.Draw(stat_image)

        stat_draw.text((0, 0), header, font=header_font, fill="white")
        stat_draw.text((0, 112), stat_text, font=stat_font, fill="#DBF0E9", anchor="ls")

        return stat_image

    numbers = stat_text.split(",")
    score_font_size = 60
    _, _, header_width, _ = header_font.getbbox(header)
    initial_width = max(
        header_width,
        (
            sum(len(number) for number in numbers) * score_font_size
            + (len(numbers) - 1) * score_font_size // 2
        ),
    )
    stat_image = Image.new("RGBA", (initial_width, height))
    stat_draw = ImageDraw.Draw(stat_image)

    stat_draw.text((0, 0), header, font=header_font, fill="white")

    x = 0
    y = 112
    for i, number in enumerate(numbers):
        font = ImageFont.truetype(TORUS_REGULAR, score_font_size)
        _, _, number_width, _ = font.getbbox(number)

        stat_draw.text((x, y), number, font=font, fill="#DBF0E9", anchor="ls")

        comma_width = 0
        if i < len(numbers) - 1:
            _, _, comma_width, _ = font.getbbox(",")
            stat_draw.text(
                (x + number_width, y), ",", font=font, fill="#DBF0E9", anchor="ls"
            )

        score_font_size -= 4

        x += number_width + comma_width

    width = max(header_width, x)
    stat_image = stat_image.crop((0, 0, width, height))

    return stat_image


def draw_stats_row(stats, y_offset=0):
    total_stats_width = sum(stat.width for stat in stats)
    num_stats = len(stats)
    spacing = (IMAGE_WIDTH - total_stats_width) // (num_stats + 1)

    y = int(IMAGE_HEIGHT / 2.1) + y_offset
    x_offset = spacing
    for stat in stats:
        image.alpha_composite(stat, (x_offset, y))
        x_offset += stat.width + spacing


def draw_stats(user_data):
    row1 = [
        draw_stat("Medals", user_data["medal_count"]),
        draw_stat("pp", user_data["pp"].quantize(0, ROUND_HALF_UP)),
        draw_stat("Play Time", user_data["playtime"]),
        draw_stat("Play Count", user_data["playcount"]),
        draw_stat("Accuracy", user_data["hit_accuracy"]),
    ]
    row2 = [
        draw_stat("Ranked Score", user_data["ranked_score"]),
        draw_stat("Total Score", user_data["total_score"]),
        draw_stat("Clears", user_data["scores_count"]),
        draw_stat(
            "Completion",
            round(user_data["scores_count"] / user_data["beatmaps_count"] * 100, 2),
        ),
    ]

    draw_stats_row(row1)
    draw_stats_row(row2, 144)


def draw_grade(grade, count):
    grade_image = Image.open(f"src/resources/images/grades/{grade}.png").convert("RGBA")
    grade_image.thumbnail((IMAGE_HEIGHT // 8, IMAGE_HEIGHT // 8))
    font = ImageFont.truetype(TORUS_SEMIBOLD, 48)
    padding = 10
    count_text = f"{count:,}"
    _, _, count_width, count_height = font.getbbox(count_text)

    width = max(count_width, grade_image.width)
    height = count_height + grade_image.height + padding

    count_image = Image.new("RGBA", (width, height))
    count_draw = ImageDraw.Draw(count_image)

    count_image.alpha_composite(grade_image, ((width - grade_image.width) // 2, 0))

    x = width // 2
    y = grade_image.height + padding

    count_draw.text((x, y), count_text, font=font, fill="white", anchor="mt")

    return count_image


def draw_grades(user_data):
    grades = [
        draw_grade("XH", user_data["grade_xh_count"]),
        draw_grade("X", user_data["grade_x_count"]),
        draw_grade("SH", user_data["grade_sh_count"]),
        draw_grade("S", user_data["grade_s_count"]),
        draw_grade("A", user_data["grade_a_count"]),
        draw_grade("B", user_data["grade_b_count"]),
        draw_grade("C", user_data["grade_c_count"]),
        draw_grade("D", user_data["grade_d_count"]),
    ]

    draw_stats_row(grades, 320)


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


def draw_body(user_data):
    draw_ranks(user_data)
    draw_stats(user_data)
    draw_grades(user_data)


# Card design is using flyte's Player Card design as a base and builds on top of it
# https://www.figma.com/file/ocltATjJqWQZBravhPuqjB/UI%2FPlayer-Card
def draw_card(user_data, avatar_data):
    draw_background()
    draw_header(user_data, avatar_data)
    draw_body(user_data)

    return image
