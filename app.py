import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import random
import math
import io
import zipfile
import itertools

# ==========================================
# ENGINE A: DYNAMIC PREMIUM ENGINE (20 IMAGES)
# ==========================================
class PremiumPalettes:
    @staticmethod
    def get_all_palettes():
        # Returning all palettes to guarantee unique combinations
        return [
            ["#141E30", "#243B55", "#FFD700", "#FF8C00"], # Luxury Night & Gold
            ["#2c3e50", "#3498db", "#e74c3c", "#f1c40f"], # Corporate Pop
            ["#ff9a9e", "#fecfef", "#a18cd1", "#fbc2eb"], # Soft Pastel
            ["#0f2027", "#203a43", "#2c5364", "#00b4d8"], # Deep Ocean
            ["#111111", "#222222", "#ff003c", "#f0f0f0"], # Urban Grunge
            ["#41295a", "#2F0743", "#f12711", "#f5af19"], # Neon Sunset
            ["#ece9e6", "#ffffff", "#8e9eab", "#283048"], # Minimalist
            ["#2E1437", "#4A1C40", "#F2D0A9", "#E63946"], # Memphis Retro
        ]

class PremiumEngine:
    @staticmethod
    def create_gradient(c1, c2, w, h):
        base = Image.new('RGB', (w, h), c1)
        top = Image.new('RGB', (w, h), c2)
        mask = Image.new('L', (w, h))
        mask_data = [int(255 * (y / h)) for y in range(h) for _ in range(w)]
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        return base

    @staticmethod
    def add_noise(img, intensity=10):
        arr = np.array(img, dtype=np.int16)
        noise = np.random.normal(0, intensity, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(arr).convert('RGBA')

    def draw_bokeh(self, draw, colors, w, h):
        for _ in range(int((w*h)/25000)):
            x, y = random.randint(-200, w), random.randint(-200, h)
            r = random.randint(100, 400)
            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            ImageDraw.Draw(overlay).ellipse([x, y, x+r, y+r], fill=random.choice(colors) + "44") 
            draw.im.paste(overlay.im, (0,0, w, h))

    def draw_memphis(self, draw, colors, w, h):
        for _ in range(int((w*h)/35000)):
            x, y = random.randint(0, w), random.randint(0, h)
            shape = random.choice(["circle", "triangle", "zigzag", "dots"])
            color = random.choice(colors)
            if shape == "circle": draw.ellipse([x, y, x+random.randint(20, 100), y+random.randint(20, 100)], outline=color, width=8)
            elif shape == "triangle":
                s = random.randint(40, 150)
                draw.polygon([(x, y), (x+s, y+s), (x-s, y+s)], fill=color)
            elif shape == "zigzag": draw.line([(x, y), (x+40, y-40), (x+80, y), (x+120, y-40)], fill=color, width=10, joint="curve")
            elif shape == "dots":
                for dx in range(0, 100, 20):
                    for dy in range(0, 100, 20): draw.ellipse([x+dx, y+dy, x+dx+8, y+dy+8], fill=color)

    def draw_halftone(self, draw, colors, w, h):
        c = random.choice(colors)
        for x in range(0, w, 40):
            for y in range(0, h, 40):
                r = random.randint(2, 12)
                draw.ellipse([x, y, x+r, y+r], fill=c)

    def draw_cyber(self, draw, colors, w, h):
        c1, c2 = colors[0], colors[1]
        for x in range(0, w, 80): draw.line([x, 0, x, h], fill=c1, width=2)
        for y in range(0, h, 80): draw.line([0, y, w, y], fill=c1, width=2)
        for _ in range(40):
            nx, ny = random.randint(0, w//80)*80, random.randint(0, h//80)*80
            draw.ellipse([nx-6, ny-6, nx+6, ny+6], fill=c2)

    def draw_liquid(self, draw, colors, w, h):
        for _ in range(8):
            x = random.choice([-100, w//2, w+100])
            y = random.choice([-100, h//2, h+100])
            r = random.randint(300, 800)
            draw.ellipse([x-r, y-r, x+r, y+r], fill=random.choice(colors))

    def draw_stripes(self, draw, colors, w, h):
        c = random.choice(colors)
        for y in range(-h, h*2, 100):
            draw.line([0, y, w, y+w], fill=c, width=35)

def generate_premium_frame(company_name, theme_colors, text_placement, style_type, w, h):
    engine = PremiumEngine()
    if w == 1200 and h == 1800:
        margin_top, margin_bottom, margin_sides = 200, 200, 90
    else: 
        margin_top, margin_bottom, margin_sides = 150, 150, 180
        
    empty_rect = (margin_sides, margin_top, w - margin_sides, h - margin_bottom)
    
    base = engine.create_gradient(theme_colors[0], theme_colors[1], w, h)
    base = engine.add_noise(base, intensity=12)
    draw = ImageDraw.Draw(base, "RGBA")
    
    art_colors = [theme_colors[2], theme_colors[3], "#ffffff", "#000000"]
    if style_type == "Bokeh": engine.draw_bokeh(draw, art_colors, w, h)
    elif style_type == "Memphis": engine.draw_memphis(draw, art_colors, w, h)
    elif style_type == "Halftone": engine.draw_halftone(draw, art_colors, w, h)
    elif style_type == "CyberTech": engine.draw_cyber(draw, art_colors, w, h)
    elif style_type == "Liquid": engine.draw_liquid(draw, art_colors, w, h)
    elif style_type == "RetroStripes": engine.draw_stripes(draw, art_colors, w, h)

    shadow_offset = 20
    shadow_layer = Image.new('RGBA', (w, h), (0,0,0,0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.rounded_rectangle((empty_rect[0]+shadow_offset, empty_rect[1]+shadow_offset, empty_rect[2]+shadow_offset, empty_rect[3]+shadow_offset), radius=60, fill=(0, 0, 0, 150))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=25))
    base = Image.alpha_composite(base, shadow_layer)
    draw = ImageDraw.Draw(base)

    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(empty_rect, radius=60, fill=255)
    base.paste((255, 255, 255, 255), (0, 0), mask)
    
    if random.choice([True, False]):
        draw.rounded_rectangle(empty_rect, radius=60, outline=theme_colors[2], width=5)

    try: font = ImageFont.truetype("arialbd.ttf", 95) 
    except: font = ImageFont.load_default(size=85)
    text_str = company_name.upper()

    if text_placement in ["Top", "Both"]:
        y_top = margin_top // 2 
        draw.text((w/2 + 4, y_top + 4), text_str, fill=(0,0,0,180), font=font, anchor="mm")
        draw.text((w/2, y_top), text_str, fill="#FFFFFF", font=font, anchor="mm", stroke_width=3, stroke_fill=theme_colors[3])

    if text_placement in ["Bottom", "Both"]:
        y_bottom = h - (margin_bottom // 2)
        draw.text((w/2 + 4, y_bottom + 4), text_str, fill=(0,0,0,180), font=font, anchor="mm")
        draw.text((w/2, y_bottom), text_str, fill="#FFFFFF", font=font, anchor="mm", stroke_width=3, stroke_fill=theme_colors[3])

    return base

# ==========================================
# ENGINE B: THE CURATED 20 THEMES ENGINE
# ==========================================
THEMES = [
    {"name": "Neon_Cyberpunk", "bg": (20, 20, 25), "c1": (255, 0, 255), "c2": (0, 255, 255), "pattern": "grid", "asset": "tech_lines"},
    {"name": "Kawaii_Pastel", "bg": (255, 228, 225), "c1": (176, 224, 230), "c2": (255, 250, 205), "pattern": "polka_dots", "asset": "stars"},
    {"name": "Luxury_Gold", "bg": (15, 15, 15), "c1": (212, 175, 55), "c2": (255, 223, 0), "pattern": "none", "asset": "elegant_dust"},
    {"name": "Forest_Nature", "bg": (240, 255, 240), "c1": (34, 139, 34), "c2": (154, 205, 50), "pattern": "leaves_abstract", "asset": "bubbles"},
    {"name": "Ocean_Depth", "bg": (10, 25, 47), "c1": (0, 191, 255), "c2": (0, 128, 128), "pattern": "sine_waves", "asset": "bubbles"},
    {"name": "Pop_Art", "bg": (255, 255, 0), "c1": (255, 0, 0), "c2": (0, 0, 255), "pattern": "halftone", "asset": "comic_splats"},
    {"name": "Synthwave_80s", "bg": (43, 0, 60), "c1": (242, 34, 255), "c2": (255, 124, 0), "pattern": "grid", "asset": "stars"},
    {"name": "Minimalist_Mono", "bg": (240, 240, 240), "c1": (100, 100, 100), "c2": (50, 50, 50), "pattern": "none", "asset": "geometry_shards"},
    {"name": "Tropical_Vibe", "bg": (255, 127, 80), "c1": (255, 215, 0), "c2": (255, 20, 147), "pattern": "polka_dots", "asset": "sunburst"},
    {"name": "Midnight_Magic", "bg": (25, 25, 112), "c1": (238, 130, 238), "c2": (255, 215, 0), "pattern": "none", "asset": "stars"},
    {"name": "Candy_Store", "bg": (255, 182, 193), "c1": (64, 224, 208), "c2": (255, 255, 255), "pattern": "stripes", "asset": "bubbles"},
    {"name": "Coffee_House", "bg": (245, 222, 179), "c1": (139, 69, 19), "c2": (205, 133, 63), "pattern": "halftone", "asset": "splats"},
    {"name": "SciFi_Hologram", "bg": (0, 0, 0), "c1": (0, 255, 255), "c2": (255, 255, 255), "pattern": "grid", "asset": "tech_lines"},
    {"name": "Retro_70s", "bg": (244, 164, 96), "c1": (139, 69, 19), "c2": (218, 165, 32), "pattern": "sine_waves", "asset": "bubbles"},
    {"name": "Velvet_Royal", "bg": (75, 0, 130), "c1": (220, 20, 60), "c2": (218, 165, 32), "pattern": "none", "asset": "elegant_dust"},
    {"name": "Fresh_Spring", "bg": (255, 255, 255), "c1": (152, 251, 152), "c2": (240, 230, 140), "pattern": "polka_dots", "asset": "splats"},
    {"name": "Lava_Lamp", "bg": (139, 0, 0), "c1": (255, 69, 0), "c2": (255, 140, 0), "pattern": "none", "asset": "large_blobs"},
    {"name": "Winter_Ice", "bg": (240, 248, 255), "c1": (173, 216, 230), "c2": (192, 192, 192), "pattern": "stripes", "asset": "geometry_shards"},
    {"name": "Graffiti_Alley", "bg": (40, 40, 40), "c1": (255, 20, 147), "c2": (0, 255, 0), "pattern": "halftone", "asset": "comic_splats"},
    {"name": "Abstract_Art", "bg": (245, 245, 245), "c1": (255, 99, 71), "c2": (70, 130, 180), "pattern": "none", "asset": "geometry_shards"}
]

def draw_pattern(draw, width, height, theme):
    c1, c2 = theme["c1"], theme["c2"]
    alpha_c1, alpha_c2 = c1 + (100,), c2 + (80,)

    if theme["pattern"] == "grid":
        for i in range(0, width, 50): draw.line([(i, 0), (i, height)], fill=alpha_c1, width=2)
        for i in range(0, height, 50): draw.line([(0, i), (width, i)], fill=alpha_c1, width=2)
    elif theme["pattern"] == "polka_dots":
        for x in range(0, width, 60):
            for y in range(0, height, 60):
                offset_x = 30 if (y//60)%2 == 0 else 0
                r = random.randint(5, 15)
                draw.ellipse([x+offset_x-r, y-r, x+offset_x+r, y+r], fill=alpha_c2)
    elif theme["pattern"] == "halftone":
        for x in range(0, width, 30):
            for y in range(0, height, 30):
                draw.ellipse([x-(r:=random.randint(2, 12)), y-r, x+r, y+r], fill=alpha_c1)
    elif theme["pattern"] == "stripes":
        for x in range(-height, width, 80): draw.line([(x, 0), (x+height, height)], fill=alpha_c1, width=20)
    elif theme["pattern"] == "sine_waves":
        for _ in range(10):
            amp, freq, y_base = random.randint(20, 80), random.uniform(0.005, 0.015), random.randint(0, height)
            pts = [(x, y_base + math.sin(x*freq)*amp) for x in range(0, width, 10)]
            if len(pts)>1: draw.line(pts, fill=alpha_c2, width=15)

def draw_assets(draw, width, height, theme):
    c1, c2 = theme["c1"], theme["c2"]
    margin_x, margin_y = int(width * 0.1), int(height * 0.1)
    
    for _ in range(random.randint(15, 30)):
        x = random.randint(0, width) if random.random() > 0.5 else random.choice([random.randint(0, margin_x), random.randint(width-margin_x, width)])
        y = random.choice([random.randint(0, margin_y), random.randint(height-margin_y, height)]) if random.random() > 0.5 else random.randint(0, height)
        size = random.randint(30, 150)
        
        if theme["asset"] == "stars":
            draw.polygon([(x, y-size), (x+size/4, y-size/4), (x+size, y), (x+size/4, y+size/4), (x, y+size), (x-size/4, y+size/4), (x-size, y), (x-size/4, y-size/4)], fill=c1+(150,))
        elif theme["asset"] == "bubbles":
            draw.ellipse([x-size, y-size, x+size, y+size], outline=c2+(150,), width=8)
            draw.ellipse([x-size*0.8, y-size*0.8, x+size*0.8, y+size*0.8], fill=c1+(50,))
        elif theme["asset"] == "comic_splats":
            pts = [(x + (size * random.uniform(0.5, 1.5)) * math.cos(math.radians(a)), y + (size * random.uniform(0.5, 1.5)) * math.sin(math.radians(a))) for a in range(0, 360, 30)]
            draw.polygon(pts, fill=random.choice([c1, c2])+(180,))
        elif theme["asset"] == "geometry_shards":
            sides = random.randint(3, 5)
            pts = [(x + size * math.cos(math.radians(i * (360/sides) + random.randint(0, 90))), y + size * math.sin(math.radians(i * (360/sides) + random.randint(0, 90)))) for i in range(sides)]
            draw.polygon(pts, fill=random.choice([c1, c2])+(200,))
        elif theme["asset"] == "tech_lines":
            draw.line([(x, y), (x+size, y), (x+size, y+size/2)], fill=c1+(180,), width=8)
            draw.ellipse([x-10, y-10, x+10, y+10], fill=c2+(200,))
        elif theme["asset"] == "elegant_dust":
            for _ in range(5): draw.ellipse([x+(dx:=random.randint(-50, 50))-(r:=random.randint(2, 8)), y+(dy:=random.randint(-50, 50))-r, x+dx+r, y+dy+r], fill=c2+(180,))
        elif theme["asset"] == "large_blobs":
            draw.ellipse([x-size*2, y-size*2, x+size*2, y+size*2], fill=c1+(120,))
        elif theme["asset"] == "sunburst":
            for a in range(0, 360, 45): draw.line([(x,y), (x + size * 1.5 * math.cos(math.radians(a)), y + size * 1.5 * math.sin(math.radians(a)))], fill=c2+(100,), width=10)

def generate_curated_theme_frame(company_name, theme, text_placement, w, h):
    if w == 1200 and h == 1800:
        margin_top, margin_bottom, margin_sides = 200, 200, 90
    else: 
        margin_top, margin_bottom, margin_sides = 150, 150, 180
    empty_rect = (margin_sides, margin_top, w - margin_sides, h - margin_bottom)

    bg_color = '#%02x%02x%02x' % theme["bg"]
    c2_color = '#%02x%02x%02x' % theme["c2"]
    
    base = PremiumEngine.create_gradient(bg_color, c2_color, w, h)
    draw = ImageDraw.Draw(base, 'RGBA')
    draw_pattern(draw, w, h, theme)
    draw_assets(draw, w, h, theme)
    base = PremiumEngine.add_noise(base, intensity=12)
    base = base.filter(ImageFilter.SMOOTH_MORE)

    shadow_offset = 20
    shadow_layer = Image.new('RGBA', (w, h), (0,0,0,0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.rounded_rectangle((empty_rect[0]+shadow_offset, empty_rect[1]+shadow_offset, empty_rect[2]+shadow_offset, empty_rect[3]+shadow_offset), radius=60, fill=(0, 0, 0, 150))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=25))
    base = Image.alpha_composite(base.convert('RGBA'), shadow_layer)
    draw = ImageDraw.Draw(base)

    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(empty_rect, radius=60, fill=255)
    base.paste((255, 255, 255, 255), (0, 0), mask)
    draw.rounded_rectangle(empty_rect, radius=60, outline=theme["c2"]+(255,), width=5)

    try: font = ImageFont.truetype("arialbd.ttf", 95) 
    except: font = ImageFont.load_default(size=85)
    text_str = company_name.upper()

    bg_r, bg_g, bg_b = theme["bg"]
    lum = (0.299*bg_r + 0.587*bg_g + 0.114*bg_b)
    text_color = "#FFFFFF" if lum < 128 else "#1A1A1A"
    stroke_color = '#%02x%02x%02x' % theme["c1"]

    if text_placement in ["Top", "Both"]:
        y_top = margin_top // 2 
        draw.text((w/2 + 4, y_top + 4), text_str, fill=(0,0,0,180), font=font, anchor="mm")
        draw.text((w/2, y_top), text_str, fill=text_color, font=font, anchor="mm", stroke_width=3, stroke_fill=stroke_color)

    if text_placement in ["Bottom", "Both"]:
        y_bottom = h - (margin_bottom // 2)
        draw.text((w/2 + 4, y_bottom + 4), text_str, fill=(0,0,0,180), font=font, anchor="mm")
        draw.text((w/2, y_bottom), text_str, fill=text_color, font=font, anchor="mm", stroke_width=3, stroke_fill=stroke_color)

    return base

# ==========================================
# STREAMLIT UI: 40 IMAGES WITH ZIP DOWNLOAD
# ==========================================
st.set_page_config(page_title="Mega 40-Frame Generator", layout="wide")
st.title("✨ Mega Studio Agent (40 Frames)")

# Set up memory (Session State) to hold the 40 generated images
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []

size_choice = st.radio("Select Frame Orientation:", ["Portrait (1200 x 1800)", "Landscape (1800 x 1200)"], horizontal=True)
company_name = st.text_input("Enter Company Name", "STREET ORIGINS")

if st.button("Generate All 40 Designs"):
    if company_name:
        current_w, current_h = (1200, 1800) if "Portrait" in size_choice else (1800, 1200)
        
        # Clear old images
        st.session_state.generated_images = []
        
        with st.spinner(f"Generating 40 unique {size_choice} designs... this takes about 10-15 seconds."):
            
            # --- Guarantee Unique Combinations for Engine A ---
            all_styles = ["Bokeh", "Memphis", "Halftone", "CyberTech", "Liquid", "RetroStripes"]
            all_palettes = PremiumPalettes.get_all_palettes()
            
            # Create a list of all 48 possible style+palette combos and shuffle them
            unique_combinations = list(itertools.product(all_styles, all_palettes))
            random.shuffle(unique_combinations)
            
            # 1. Engine A (First 20 Images)
            for i in range(20):
                placement = "Top" if i < 5 else "Bottom" if i < 10 else random.choice(["Top", "Bottom", "Both"])
                
                # Pick guaranteed unique combo
                style, colors = unique_combinations[i] 
                
                img = generate_premium_frame(company_name, colors, placement, style, current_w, current_h)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                
                st.session_state.generated_images.append({
                    "data": buf.getvalue(),
                    "caption": f"Dynamic: {style} ({placement})",
                    "filename": f"{company_name}_{style}_Dynamic_{i+1}.png",
                    "collection": "1"
                })

            # 2. Engine B (Curated 20 Themes)
            for i in range(20):
                theme = THEMES[i]
                placement = "Top" if i < 5 else "Bottom" if i < 10 else random.choice(["Top", "Bottom", "Both"])
                img = generate_curated_theme_frame(company_name, theme, placement, current_w, current_h)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                
                st.session_state.generated_images.append({
                    "data": buf.getvalue(),
                    "caption": f"{theme['name']} ({placement})",
                    "filename": f"{company_name}_{theme['name']}_Curated_{i+1}.png",
                    "collection": "2"
                })
    else:
        st.warning("Please enter a company name.")

# --- DISPLAY MEMORY & ZIP EXPORT LOGIC ---
if len(st.session_state.generated_images) == 40:
    st.success("All 40 Designs Ready! Download them individually below, or download all at once.")
    
    # --- CREATE ZIP FILE IN MEMORY ---
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in st.session_state.generated_images:
            zip_file.writestr(item["filename"], item["data"])
            
    # Show the Download All Button at the top!
    st.download_button(
        label="📦 DOWNLOAD ALL 40 IMAGES (ZIP FILE)",
        data=zip_buffer.getvalue(),
        file_name=f"{company_name}_All_Frames.zip",
        mime="application/zip",
        use_container_width=True
    )
    
    st.markdown("---")
    
    # Display the grid for individual downloads
    st.write("### Collection 1: Dynamic Styles (1-20)")
    for row in range(4):
        cols = st.columns(5)
        for col in range(5):
            idx = (row * 5) + col
            item = st.session_state.generated_images[idx]
            with cols[col]:
                st.image(item["data"], caption=item["caption"], use_container_width=True)
                st.download_button("Download", data=item["data"], file_name=item["filename"], mime="image/png", key=f"dl_a_{idx}")

    st.write("### Collection 2: Curated Themes (21-40)")
    for row in range(4):
        cols = st.columns(5)
        for col in range(5):
            idx = 20 + (row * 5) + col
            item = st.session_state.generated_images[idx]
            with cols[col]:
                st.image(item["data"], caption=item["caption"], use_container_width=True)
                st.download_button("Download", data=item["data"], file_name=item["filename"], mime="image/png", key=f"dl_b_{idx}")
