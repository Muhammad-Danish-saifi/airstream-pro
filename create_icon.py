from PIL import Image, ImageDraw

def create_airstream_icon(output_ico="app_icon.ico", output_png="app_icon.png"):
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background with dark gradient fill
    padding = 12
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=54,
        fill="#0a0e1c",
        outline="#00f2fe",
        width=4
    )

    # Inner subtle glow circle
    draw.ellipse([36, 36, size - 36, size - 36], fill="#12182c")

    # Headphone band (arch)
    band_box = [60, 52, size - 60, 185]
    draw.arc(band_box, start=180, end=0, fill="#00f2fe", width=14)

    # Top band highlight
    top_band = [72, 60, size - 72, 175]
    draw.arc(top_band, start=200, end=340, fill="#4facfe", width=6)

    # Left Earcup
    draw.rounded_rectangle([44, 120, 80, 192], radius=16, fill="#00f2fe")
    draw.rounded_rectangle([50, 130, 74, 182], radius=10, fill="#0a0e1c")

    # Right Earcup
    draw.rounded_rectangle([size - 80, 120, size - 44, 192], radius=16, fill="#9d4edd")
    draw.rounded_rectangle([size - 74, 130, size - 50, 182], radius=10, fill="#0a0e1c")

    # Sound wave pulses inside
    cx, cy = size // 2, 155
    draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill="#00f59b")
    draw.arc([cx - 24, cy - 24, cx + 24, cy + 24], start=210, end=330, fill="#00f2fe", width=4)
    draw.arc([cx - 38, cy - 38, cx + 38, cy + 38], start=210, end=330, fill="#4facfe", width=4)

    # Save PNG
    img.save(output_png, "PNG")

    # Save multi-resolution ICO
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_ico, format="ICO", sizes=sizes)
    print(f"Generated {output_ico} and {output_png} successfully!")

if __name__ == "__main__":
    create_airstream_icon()
