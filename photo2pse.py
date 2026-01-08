import argparse
import random
import math
import os
from PIL import Image, ImageFilter, ImageStat
from pymol import cgo
from pymol import cmd

def generate_mae_from_img(args):
    try:
        img = Image.open(args.img).convert('RGB')
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    # 1. AUTO-ADJUST LOGIC
    auto_contrast = args.contrast
    auto_gamma = args.gamma
    if args.auto:
        stat = ImageStat.Stat(img.convert('L'))
        mean_brightness = stat.mean[0]  # 0-255
        std_dev = stat.stddev[0]
        
        print(f"-> Auto-Adjusting: Mean={mean_brightness:.1f}, StdDev={std_dev:.1f}")
        
        # Adjust Gamma based on mean (center it around 128)
        # If mean is 50 (dark), gamma becomes ~0.6 (brightens)
        auto_gamma = math.log(128/255) / math.log(mean_brightness/255)
        auto_gamma = max(0.4, min(2.2, auto_gamma))
        
        # Adjust Contrast based on standard deviation
        # If std_dev is low (flat), boost contrast
        if std_dev < 40:
            auto_contrast = 50.0
        elif std_dev > 80:
            auto_contrast = 10.0
        else:
            auto_contrast = 30.0
        print(f"-> Selected: Gamma={auto_gamma:.2f}, Contrast={auto_contrast:.1f}")

    if args.denoise:
        img = img.filter(ImageFilter.MedianFilter(size=3))
    if args.dither:
        img = img.convert('P', palette=Image.ADAPTIVE, colors=256).convert('RGB')

    if max(img.size) > 500:
        img.thumbnail((500, 500))
    
    width, height = img.size
    pixels = img.load()
    cgo_data = []
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if r > 252 and g > 252 and b > 252: continue 
            
            # Use Auto-Adjusted values
            f = (259 * (auto_contrast + 255)) / (255 * (259 - auto_contrast))
            r, g, b = [max(0, min(255, int(f * (c - 128) + 128))) for c in (r, g, b)]

            r_c, g_c, b_c = [max(0, min(255, int(255 * (c/255)**auto_gamma))) for c in (r, g, b)]
            brightness = (r + g + b) / 3
            
            pos_x_base = (x - width/2) * 0.1 * args.scale
            pos_y_base = (height/2 - y) * 0.1 * args.scale
            z_val = (brightness / 255.0) * args.depth * args.scale
            
            z_range = [z_val] if args.mode == "project" else range(-int(z_val*3), int(z_val*3) + 1)

            for z_step in z_range:
                if args.mode == "voxel":
                    if args.hollow and len(z_range) > 2:
                        if z_step != z_range[0] and z_step != z_range[-1]: continue
                    pos_z = z_step * 0.1 * args.scale
                else: 
                    pos_z = z_val

                jx = pos_x_base + random.uniform(-args.jitter, args.jitter) * args.scale
                jy = pos_y_base + random.uniform(-args.jitter, args.jitter) * args.scale
                jz = pos_z + random.uniform(-args.jitter, args.jitter) * args.scale

                cgo_data.extend([cgo.COLOR, r_c/255.0, g_c/255.0, b_c/255.0, cgo.SPHERE, jx, jy, jz, 0.1 * args.scale])


    cmd.load_cgo(cgo_data, "photo2mae")
    cmd.save("photo.pse")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--img", required=True)
    parser.add_argument("--out", default="auto_art.mae")
    parser.add_argument("--mode", choices=["project", "voxel"], default="project")
    parser.add_argument("--auto", action="store_true", help="Auto-calculate best Gamma and Contrast")
    parser.add_argument("--hollow", action="store_true")
    parser.add_argument("--smart_color", action="store_true")
    parser.add_argument("--dither", action="store_true")
    parser.add_argument("--denoise", action="store_true")
    parser.add_argument("--depth", type=float, default=2.0)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=20.0)
    parser.add_argument("--jitter", type=float, default=0.01)
    
    args = parser.parse_args()
    print("--- Photo2MAE Auto Studio ---")
    generate_mae_from_img(args)
    print(f"-> Done! Saved to {args.out}")
