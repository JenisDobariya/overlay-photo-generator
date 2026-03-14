import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import numpy as np
import random
import math
import io
import zipfile
import requests
import difflib
from google import genai
from google.genai import types
import firebase_admin
from firebase_admin import credentials, db

# --- SECURE CLOUD INITIALIZATION ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]

except KeyError:
    st.error("🚨 Missing API Keys! Please configure GEMINI_API_KEY and PIXABAY_API_KEY in Streamlit Secrets.")
    st.stop()

@st.cache_resource
def init_firebase():
    """Initializes Firebase Realtime Database securely using Streamlit Secrets."""
    if not firebase_admin._apps:
        try:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
            
            # Realtime Database requires the databaseURL to be passed during initialization!
            firebase_admin.initialize_app(cred, {
                'databaseURL': st.secrets["firebase"]["databaseURL"]
            })
        except Exception as e:
            st.error(f"🚨 Failed to initialize Firebase: {e}. Check your Streamlit Secrets formatting.")
            st.stop()
    return True

# Run the initialization
init_firebase()

# --- STEP 1: UTILITIES & AI ---
@st.cache_resource
def get_rembg_session():
    from rembg import new_session
    return new_session()

def get_color_variants(hex_color):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    shade = tuple(max(0, c - 60) for c in rgb)
    tint = tuple(min(255, c + 60) for c in rgb)
    def to_hex(c): return '#%02x%02x%02x' % c
    return [to_hex(rgb), to_hex(shade), to_hex(tint)]

def process_logo_logic(uploaded_file, should_remove_bg):
    input_image = Image.open(uploaded_file)
    input_image.thumbnail((1200, 1200), Image.LANCZOS)
    if should_remove_bg:
        from rembg import remove
        session = get_rembg_session()
        output_image = remove(input_image, session=session)
    else:
        output_image = input_image.convert("RGBA")
    return output_image

# --- REALTIME DATABASE CACHE LOGIC ---
@st.cache_data(ttl=300, show_spinner=False)
def load_category_cache():
    """Fetches all previously searched categories from Firebase Realtime Database."""
    cache = {}
    try:
        # Reference the root 'category_cache' node
        ref = db.reference('category_cache')
        data = ref.get()
        if data:
            cache = data
    except Exception as e:
        st.warning(f"Failed to load cache from Realtime Database: {e}")
    return cache

def save_category_to_cache(category_key, keywords):
    """Saves a newly searched category permanently to Firebase Realtime Database."""
    try:
        ref = db.reference('category_cache')
        # Add the new category as a child node with the list of keywords
        ref.child(category_key).set(keywords)
    except Exception as e:
        st.warning(f"Failed to save to Realtime Database: {e}")

def get_ai_keywords(category_name):
    """Hits Firebase first (handling typos). If missing, hits Gemini and saves to Firebase."""
    if not category_name or category_name.strip() == "":
        return []
        
    category_key = category_name.lower().strip()
    cache = load_category_cache()
    
    existing_keys = list(cache.keys())
    close_matches = difflib.get_close_matches(category_key, existing_keys, n=1, cutoff=0.8)
    
    if close_matches:
        matched_key = close_matches[0]
        if matched_key != category_key:
            st.toast(f"💡 Typo corrected: '{category_key}' matched with database entry '{matched_key}'!")
        return cache[matched_key]
        
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        system_instruction = """
        Output ONLY a single line of comma-separated keywords representing physical objects for the category.
        Provide exactly 12 highly visual items. No descriptions. Keep words simple (e.g. 'wedding ring').
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Category: {category_key}",
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
        )
        items_list = [item.strip() for item in response.text.split(',')]
        
        save_category_to_cache(category_key, items_list)
        st.toast(f"☁️ Saved new category to Firebase Realtime Database: '{category_key}'")
        return items_list
        
    except Exception as e:
        st.warning(f"Gemini API Error: {e}")
        return []

@st.cache_data(show_spinner=False)
def fetch_pixabay_stickers(keywords):
    stickers_bytes = []
    for query in keywords:
        url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={requests.utils.quote(query)}&image_type=vector&colors=transparent&per_page=3"
        try:
            data = requests.get(url).json()
            if data.get('hits') and len(data['hits']) > 0:
                image_url = data['hits'][0]['webformatURL']
                img_data = requests.get(image_url).content
                stickers_bytes.append(img_data)
        except Exception:
            continue
    return stickers_bytes

# --- STEP 2: HIGH-IMPACT DESIGN ENGINE ---
class CategoryObjectEngine:
    @staticmethod
    def create_gradient(c1, c2, w, h):
        base = Image.new('RGB', (w, h), c1)
        top = Image.new('RGB', (w, h), c2)
        mask = Image.new('L', (w, h))
        mask_data = [int(255 * (y / h)) for y in range(h) for _ in range(w)]
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        return base

    def draw_sparkle(self, draw, x, y, size, color):
        half, core = size // 2, max(2, size // 8)
        pts = [(x, y - half), (x + core, y - core), (x + half, y), (x + core, y + core),
               (x, y + half), (x - core, y + core), (x - half, y), (x - core, y - core)]
        draw.polygon(pts, fill=color)

    def draw_hexagon(self, draw, x, y, size, color, fill=True):
        r = size // 2
        pts = [(x + r * math.cos(math.radians(angle)), y + r * math.sin(math.radians(angle))) for angle in range(0, 360, 60)]
        if fill: draw.polygon(pts, fill=color)
        else: draw.polygon(pts, outline=color, width=max(1, size//15))

    def draw_chevron(self, draw, x, y, size, color):
        w, h = size, size // 2
        thick = max(4, size // 4)
        pts = [(x, y), (x + w, y + h//2), (x, y + h), (x + thick, y + h), (x + w + thick, y + h//2), (x + thick, y)]
        draw.polygon(pts, fill=color)

    def draw_leaf(self, draw, x, y, size, color):
        draw.pieslice([x, y, x+size, y+size], 180, 270, fill=color)
        draw.pieslice([x, y, x+size, y+size], 0, 90, fill=color)
        draw.polygon([(x+size//2, y), (x+size, y+size//2), (x+size//2, y+size), (x, y+size//2)], fill=color)

    def draw_abstract_objects(self, draw, brand_palette, w, h, category):
        cat = category.lower()
        full_harmonic = []
        for color in brand_palette:
            full_harmonic.extend(get_color_variants(color))
        
        for _ in range(random.randint(40, 70)):
            x, y = random.randint(0, w), random.randint(0, h)
            size = random.randint(30, 180)
            color = random.choice(full_harmonic) + random.choice(["66", "99", "CC", "FF"])
            
            if any(k in cat for k in ["luxury", "wedding", "beauty", "premium"]):
                if random.random() > 0.4: self.draw_sparkle(draw, x, y, size, color)
                else: draw.ellipse([x, y, x+size, y+size], outline=color, width=2)
            
            elif any(k in cat for k in ["tech", "cyber", "corporate", "data", "it"]):
                if random.random() > 0.5: self.draw_hexagon(draw, x, y, size, color, fill=random.choice([True, False]))
                else:
                    draw.rectangle([x, y, x+size, y+max(4, size//10)], fill=color)
                    draw.ellipse([x-4, y-4, x+4, y+4], fill=color)
            
            elif any(k in cat for k in ["sports", "fitness", "gym", "auto", "speed"]):
                if random.random() > 0.5: self.draw_chevron(draw, x, y, size, color)
                else: draw.line([x, y, x+size*2, y], fill=color, width=max(2, size//5))
            
            elif any(k in cat for k in ["party", "fun", "kids", "event"]):
                shape_type = random.choice(["circle", "triangle", "confetti"])
                if shape_type == "circle": draw.ellipse([x, y, x+size, y+size], fill=color)
                elif shape_type == "triangle": draw.polygon([(x, y-size//2), (x+size//2, y+size//2), (x-size//2, y+size//2)], fill=color)
                else: draw.regular_polygon((x, y, size//3), n_sides=4, rotation=random.randint(0, 360), fill=color)
            
            elif any(k in cat for k in ["food", "cafe", "restaurant", "organic", "health"]):
                if random.random() > 0.5: self.draw_leaf(draw, x, y, size, color)
                else:
                    draw.ellipse([x, y, x+size, y+size], fill=color)
                    if random.random() > 0.5: draw.ellipse([x+10, y+10, x+size-10, y+size-10], outline="#FFFFFF66", width=2)
            
            else:
                draw.regular_polygon((x, y, size//2), n_sides=random.randint(3, 8), rotation=random.randint(0,360), fill=color)

def generate_branded_frame(company_name, brand_text_color, text_size, text_pos, text_order, category, logos_list, use_ai_stickers, ai_stickers, palette, w, h, mt, mb, ms, bg_style, pattern_style, radius_val):
    engine = CategoryObjectEngine()
    empty_rect = (ms, mt, w - ms, h - mb)
    p_copy = list(palette) if palette else ["#000000", "#FFFFFF"]
    random.shuffle(p_copy)
    
    c1 = p_copy[0]
    if bg_style == "Gradient":
        c2 = p_copy[1] if len(p_copy) > 1 else get_color_variants(p_copy[0])[1]
        base = engine.create_gradient(c1, c2, w, h)
    else:
        base = Image.new('RGB', (w, h), c1)
        
    draw = ImageDraw.Draw(base, "RGBA")
    
    if pattern_style == "With Design":
        engine.draw_abstract_objects(draw, p_copy, w, h, category)
        
    if use_ai_stickers and ai_stickers:
        for _ in range(random.randint(20, 35)): 
            sticker = random.choice(ai_stickers)
            scale = random.uniform(0.3, 1.2)
            new_w, new_h = max(20, int(sticker.width * scale)), max(20, int(sticker.height * scale))
            new_w, new_h = min(new_w, 350), min(new_h, 350)
            s_copy = sticker.copy().resize((new_w, new_h), Image.LANCZOS)
            
            angle = random.randint(-45, 45)
            s_copy = s_copy.rotate(angle, expand=True, resample=Image.BICUBIC)
            
            r, g, b, a = s_copy.split()
            a = a.point(lambda p: p * 0.6) 
            s_copy.putalpha(a)
            
            x = random.randint(-100, w - 50)
            y = random.randint(-100, h - 50)
            base.paste(s_copy, (x, y), s_copy)

    mask = Image.new('L', (w, h), 255)
    ImageDraw.Draw(mask).rounded_rectangle(empty_rect, radius=radius_val, fill=0)
    base.putalpha(mask)

    draw = ImageDraw.Draw(base)
    try: font = ImageFont.truetype("arialbd.ttf", int(text_size))
    except: font = ImageFont.load_default()

    zones = {
        "Top Left": [], "Top Middle": [], "Top Right": [],
        "Bottom Left": [], "Bottom Middle": [], "Bottom Right": []
    }

    for l in logos_list:
        aspect = l['img'].width / l['img'].height
        lw, lh = int(l['size'] * aspect), int(l['size'])
        zones[l['position']].append({'type': 'logo', 'img': l['img'], 'w': lw, 'h': lh, 'order': l['order']})
        
    if company_name:
        bbox = draw.textbbox((0, 0), company_name.upper(), font=font)
        tw = bbox[2] - bbox[0]
        zones[text_pos].append({'type': 'text', 'text': company_name.upper(), 'w': tw, 'h': int(text_size), 'order': text_order})

    for zone_name, items in zones.items():
        if not items: continue
        
        items = sorted(items, key=lambda x: x['order'])
        total_width = sum(item['w'] for item in items) + (20 * (len(items) - 1))
        
        target_y = mt // 2 if "Top" in zone_name else h - (mb // 2)
        
        if "Left" in zone_name: current_x = ms
        elif "Right" in zone_name: current_x = w - ms - total_width
        else: current_x = (w - total_width) // 2 

        for item in items:
            if item['type'] == 'logo':
                l_copy = item['img'].copy().resize((item['w'], item['h']), Image.LANCZOS)
                base.paste(l_copy, (int(current_x), int(target_y - (item['h'] // 2))), l_copy)
            elif item['type'] == 'text':
                draw.text((current_x, target_y), item['text'], fill=brand_text_color, font=font, anchor="lm")
            
            current_x += item['w'] + 20 

    return base

# --- STEP 3: STREAMLIT APP ---
st.set_page_config(page_title="Pro Studio v12", layout="wide")

st.markdown("""
    <style>
    div[data-testid="stButton"] button[kind="secondary"] {
        padding: 2px 10px !important; height: 24px !important; min-height: 24px !important;
        font-size: 12px !important; line-height: 1 !important; border-radius: 4px !important; margin-top: 5px !important;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        height: 50px !important; font-size: 18px !important; font-weight: 800 !important;
        border-radius: 8px !important; letter-spacing: 1px !important;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important; color: white !important;
        border: none !important; transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important; transform: translateY(-1px) !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'all_images' not in st.session_state: st.session_state.all_images = []
if 'brand_palette' not in st.session_state: st.session_state.brand_palette = ['#000000', '#FFFFFF']
if 'logo_cache' not in st.session_state: st.session_state.logo_cache = {}

pos_options = ["Top Middle", "Top Left", "Top Right", "Bottom Middle", "Bottom Left", "Bottom Right"]

st.title("🚀 Studio Agent v12: RTDB Enabled")

left_panel, right_panel = st.columns([3, 1])

with left_panel:
    c1, c2 = st.columns(2)
    with c1:
        st.write("📝 **Brand Text Settings**")
        sub_c1, sub_c2, sub_c3 = st.columns([2, 1, 1])
        company_name = sub_c1.text_input("Brand Name", "LEAP")
        brand_text_color = sub_c2.color_picker("Text Color", "#FFFFFF")
        text_size = sub_c3.number_input("Text Size", value=80, min_value=10, max_value=300)
        
        tx_c1, tx_c2 = st.columns([2, 1])
        text_pos = tx_c1.selectbox("Text Position", pos_options, index=0)
        text_order = tx_c2.number_input("Text Order", value=99)
        
        st.markdown("---")
        st.write("🎨 **Background & Category**")
        
        # Load from Realtime Database
        saved_cache = load_category_cache()
        category_options = ["➕ Add New Category"] + [c.title() for c in sorted(list(saved_cache.keys()))]
        
        selected_cat = st.selectbox("Select or Search Category", category_options)
        
        if selected_cat == "➕ Add New Category":
            category_input = st.text_input("Type New Category (e.g. Real Estate, Gaming)")
        else:
            category_input = selected_cat

        sc_bg, sc_pat = st.columns(2)
        bg_style = sc_bg.radio("Background Style", ["Gradient", "Solid"])
        pattern_style = sc_pat.radio("Pattern Type", ["With Design", "Without Design"])
        use_ai_stickers = st.toggle("✨ Layer AI Smart Stickers", value=False)
        
    with c2:
        st.write("🖼️ **Logo Center**")
        uploaded_logos = st.file_uploader("Upload Logos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        remove_bg_opt = st.checkbox("AI BG Removal", value=False)
        
        active_logos = []
        if uploaded_logos:
            for i, file in enumerate(uploaded_logos):
                cache_key = f"{file.name}_{remove_bg_opt}"
                if cache_key not in st.session_state.logo_cache:
                    with st.spinner(f"Processing {file.name}..."):
                        clean_img = process_logo_logic(file, remove_bg_opt)
                        st.session_state.logo_cache[cache_key] = clean_img
                
                with st.expander(f"⚙️ {file.name} Settings", expanded=True):
                    sc1, sc2, sc3 = st.columns(3)
                    l_size = sc1.number_input("Size (px)", value=150, key=f"sz_{file.name}")
                    l_order = sc2.number_input("Order", value=i, step=1, key=f"ord_{file.name}")
                    l_pos = sc3.selectbox("Position", pos_options, index=0, key=f"pos_{file.name}")
                    
                active_logos.append({
                    "img": st.session_state.logo_cache[cache_key],
                    "size": l_size, "order": l_order, "position": l_pos
                })

    if st.session_state.brand_palette:
        st.write("### Brand Palette")
        p_cols = st.columns(12)
        to_delete = None
        for i, color in enumerate(st.session_state.brand_palette):
            with p_cols[i]:
                st.markdown(f'<div style="background-color:{color}; width:60px; height:60px; border-radius:10px; border:2px solid #ddd; margin:0 auto;"></div>', unsafe_allow_html=True)
                if st.button("x", key=f"del_{i}", help="Delete", type="secondary", use_container_width=True): to_delete = i
        
        if to_delete is not None:
            st.session_state.brand_palette.pop(to_delete)
            st.rerun()

        with p_cols[min(len(st.session_state.brand_palette), 11)]:
            with st.popover("➕", use_container_width=True):
                picked = st.color_picker("Add Color", "#FF0000")
                if st.button("Add", type="secondary"):
                    if picked not in st.session_state.brand_palette:
                        st.session_state.brand_palette.append(picked)
                        st.rerun()

    st.markdown("---")
    d_cols = st.columns(6)
    w_val = d_cols[0].number_input("↔️ Width", value=1200)
    h_val = d_cols[1].number_input("↕️ Height", value=1800)
    mt_val = d_cols[2].number_input("⬆️ Top Margin", value=200)
    mb_val = d_cols[3].number_input("⬇️ Bottom Margin", value=200)
    ms_val = d_cols[4].number_input("⬅️➡️ Side Margin", value=100)
    radius_val = d_cols[5].number_input("📐 Corner Curve", value=60)

loaded_stickers = []
if use_ai_stickers and category_input.strip() != "":
    with st.spinner(f"Fetching AI Stickers from RTDB/Pixabay for '{category_input}'..."):
        keywords = get_ai_keywords(category_input)
        raw_bytes = fetch_pixabay_stickers(keywords)
        loaded_stickers = [Image.open(io.BytesIO(b)).convert("RGBA") for b in raw_bytes]

with right_panel:
    st.write("### 👁️ Live Preview")
    preview_img = generate_branded_frame(
        company_name, brand_text_color, text_size, text_pos, text_order, category_input, 
        active_logos, use_ai_stickers, loaded_stickers, st.session_state.brand_palette, 
        w_val, h_val, mt_val, mb_val, ms_val, bg_style, pattern_style, radius_val
    )
    st.image(preview_img, use_container_width=True, caption="Auto-updates with settings")

st.markdown("---")

if st.button("✨ GENERATE 40 IMPACTFUL DESIGNS", type="primary", use_container_width=True):
    st.session_state.all_images = []
    with st.spinner("Rendering Cloud Graphics Batch..."):
        for i in range(40):
            img = generate_branded_frame(
                company_name, brand_text_color, text_size, text_pos, text_order, category_input, 
                active_logos, use_ai_stickers, loaded_stickers, st.session_state.brand_palette, 
                w_val, h_val, mt_val, mb_val, ms_val, bg_style, pattern_style, radius_val
            )
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            st.session_state.all_images.append({"data": buf.getvalue(), "filename": f"{category_input}_{i+1}.png"})

if st.session_state.all_images:
    z_buf = io.BytesIO()
    with zipfile.ZipFile(z_buf, "w") as zf:
        for itm in st.session_state.all_images: zf.writestr(itm["filename"], itm["data"])
    st.download_button("📦 DOWNLOAD ALL (ZIP)", data=z_buf.getvalue(), file_name="Design_Pack_v12.zip", type="primary", use_container_width=True)

    st.markdown("---")
    total_imgs = len(st.session_state.all_images)
    for i in range(0, total_imgs, 5):
        grid = st.columns(5)
        for j in range(5):
            idx = i + j
            if idx < total_imgs:
                with grid[j]:
                    st.image(st.session_state.all_images[idx]["data"], use_container_width=True)
                    st.download_button("Download", data=st.session_state.all_images[idx]["data"], file_name=st.session_state.all_images[idx]["filename"], key=f"btn_{idx}", type="secondary")
