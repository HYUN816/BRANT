from PIL import Image, ImageDraw, ImageFont

def create_image_with_text(text, font_path, max_font_size, image_size=(512, 512),  output_path="output.png", line_spacing_ratio=0.1, char_spacing_ratio=0.0):
    # Create a white background image
    image = Image.new("RGB", image_size, "white")
    draw = ImageDraw.Draw(image)
    
    # Function to find the maximum font size that fits within the image
    def find_max_font_size(draw, text_lines, font_path, image_size, line_spacing_ratio, char_spacing_ratio):
        max_size = min(image_size)
        for size in range(max_size, 0, -1):
            font = ImageFont.truetype(font_path, size=size)
            char_spacing = int(size * char_spacing_ratio)
            text_widths = []
            text_heights = []
            for line in text_lines:
                width = sum(draw.textbbox((0, 0), char, font=font)[2] - draw.textbbox((0, 0), char, font=font)[0] for char in line) + (len(line) - 1) * char_spacing
                text_widths.append(width)
                text_heights.append(draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1])
            total_height = sum(text_heights) + int((len(text_lines) - 1) * size * line_spacing_ratio)  # Include line spacing
            if max(text_widths) <= image_size[0] and total_height <= image_size[1]:
                return size
        return 1  # If no suitable size is found, return the smallest size

    # Split text into lines
    text_lines = text.split('\n')
    
    # Find the maximum font size
    
    calc_font_size = find_max_font_size(draw, text_lines, font_path, image_size, line_spacing_ratio, char_spacing_ratio)
    max_font_size = min(max_font_size, calc_font_size)
    font = ImageFont.truetype(font_path, size=max_font_size)
    char_spacing = int(max_font_size * char_spacing_ratio)
    
    # Calculate total text height
    text_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in text_lines]
    total_text_height = sum(text_heights) + int((len(text_lines) - 1) * max_font_size * line_spacing_ratio)  # Include line spacing
    
    # Starting y position for the text block
    y_start = (image_size[1] - total_text_height) // 2
    
    # Draw each line of text
    y = y_start
    for line, text_height in zip(text_lines, text_heights):
        total_line_width = sum(draw.textbbox((0, 0), char, font=font)[2] - draw.textbbox((0, 0), char, font=font)[0] for char in line) + (len(line) - 1) * char_spacing
        x = (image_size[0] - total_line_width) // 2
        for char in line:
            draw.text((x, y), char, fill="black", font=font)
            x += draw.textbbox((0, 0), char, font=font)[2] - draw.textbbox((0, 0), char, font=font)[0] + char_spacing
        y += text_height + int(max_font_size * line_spacing_ratio)  # Move to the next line, including line spacing
    
    # Save the image
    image.save(output_path)
    return image

# Example usage
# text = "This is a test\nof multiple lines\nin an image"
# font_path = './fonts/NanumSquareR.ttf'  # 사용자 폰트 파일 경로
# image_size = (512, 512)  # 이미지 사이즈 지정 (가로, 세로)
# output_path = "output.png"  # 결과 이미지 저장 경로
# line_spacing_ratio = 0.1  # 줄 간격 비율 (0.1은 폰트 크기의 10%), 음수로 설정 시 겹치게도 가능
# char_spacing_ratio = -0.1 # 문자 간격 비율 (0.05는 폰트 크기의 5%), 음수로 설정 시 겹치게도 가능

# create_image_with_text(text, font_path, image_size, output_path, line_spacing_ratio, char_spacing_ratio)