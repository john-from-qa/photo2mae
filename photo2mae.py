import argparse
import random
import math
from PIL import Image, ImageFilter

def generate_mae_from_img(input_png, output_mae, depth_scale, mode, hollow, gamma, scale, contrast, jitter, smart_color, dither, denoise):
    try:
        img = Image.open(input_png).convert('RGB')
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    if denoise:
        img = img.filter(ImageFilter.MedianFilter(size=3))
    if dither:
        img = img.convert('P', palette=Image.ADAPTIVE, colors=256).convert('RGB')

    if max(img.size) > 400:
        img.thumbnail((400, 400))
    
    width, height = img.size
    pixels = img.load()
    atom_data = []
    atom_idx = 1
    
    # Element Spectrum Map: (Min Brightness, Atomic Num, Name, Mmod Type)
    # This covers the range from black to white across common molecular colors
    spectrum = [
        (0,   6,  "C", 3),   # Darkest: Carbon (Grey/Black)
        (30,  7,  "N", 31),  # Nitrogen (Blue)
        (60,  8,  "O", 16),  # Oxygen (Red)
        (90,  15, "P", 43),  # Phosphorus (Orange)
        (120, 16, "S", 15),  # Sulfur (Yellow)
        (150, 17, "Cl", 11), # Chlorine (Green)
        (180, 35, "Br", 13), # Bromine (Dark Red/Brown)
        (210, 53, "I", 12),  # Iodine (Purple)
        (230, 2,  "He", 42), # Helium (Cyan)
        (250, 1,  "H", 41)   # Brightest: Hydrogen (White)
    ]

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if r > 248 and g > 248 and b > 248: continue
            
            f = (259 * (contrast + 255)) / (255 * (259 - contrast))
            r, g, b = [max(0, min(255, int(f * (c - 128) + 128))) for c in (r, g, b)]

            r_c, g_c, b_c = [max(0, min(255, int(255 * (c/255)**gamma))) for c in (r, g, b)]
            hex_color = "{:02x}{:02x}{:02x}".format(r_c, g_c, b_c)
            brightness = (r + g + b) / 3
            
            # DEFAULT
            atomic_num, atom_name, mmod_type = 6, "C", 3
            
            if smart_color:
                # Find the best element fit in the spectrum
                for threshold, a_num, a_name, m_type in reversed(spectrum):
                    if brightness >= threshold:
                        atomic_num, atom_name, mmod_type = a_num, a_name, m_type
                        break

            pos_x_base = (x - width/2) * 0.1 * scale
            pos_y_base = (height/2 - y) * 0.1 * scale
            z_val = (brightness / 255.0) * depth_scale * scale
            z_range = [z_val] if mode == "project" else range(-int(z_val*3), int(z_val*3) + 1)

            for z_step in z_range:
                if mode == "voxel":
                    if hollow and len(z_range) > 2:
                        if z_step != z_range[0] and z_step != z_range[-1]: continue
                    pos_z = z_step * 0.1 * scale
                else: pos_z = z_val

                jx, jy, jz = [pos + random.uniform(-jitter, jitter) * scale for pos in (pos_x_base, pos_y_base, pos_z)]
                atom_data.append(f"  {atom_idx} {mmod_type} {jx:.4f} {jy:.4f} {jz:.4f} 1 24 {atomic_num} {hex_color} {atom_name}{atom_idx}")
                atom_idx += 1

    title = output_mae.replace('.mae','')
    header = f"{{ \n s_m_m2io_version \n ::: \n 2.0.0 \n }} \n f_m_ct {{ \n s_m_title \n s_m_entry_id \n s_m_entry_name \n i_m_ct_format \n ::: \n {title} \n 1 \n {title} \n  2 \n m_atom[{len(atom_data)}] {{ \n  i_m_mmod_type \n  r_m_x_coord \n  r_m_y_coord \n  r_m_z_coord \n  i_m_residue_number \n  i_m_color \n  i_m_atomic_number \n  s_m_color_rgb \n  s_m_atom_name \n  ::: \n"
    with open(output_mae, 'w') as f_out:
        f_out.write(header + "\n".join(atom_data) + "\n  ::: \n } \n m_bond[0] { \n  i_m_from \n  i_m_to \n  i_m_order \n  ::: \n  ::: \n } \n }")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--img", required=True)
    parser.add_argument("--out", default="photo-out.mae")
    parser.add_argument("--mode", choices=["project", "voxel"], default="project")
    parser.add_argument("--hollow", action="store_true")
    parser.add_argument("--dither", action="store_true")
    parser.add_argument("--denoise", action="store_true")
    parser.add_argument("--depth", type=float, default=2.0)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=30.0)
    parser.add_argument("--jitter", type=float, default=0.01)
    parser.add_argument("--smart_color", action="store_true", help="Maps brightness to a 10-element color spectrum")
    args = parser.parse_args()
    generate_mae_from_img(args.img, args.out, args.depth, args.mode, args.hollow, args.gamma, args.scale, args.contrast, args.jitter, args.smart_color, args.dither, args.denoise)
    print("Success!")