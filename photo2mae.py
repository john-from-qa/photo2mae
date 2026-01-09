import argparse
import random
import math
import os
from PIL import Image, ImageFilter, ImageStat

def generate_mae_from_img(args):
    try:
        img = Image.open(args.img).convert('RGB')
    except Exception as e:
        print(f"Error: {e}")
        return 0

    # 1. AUTO-ADJUST BASELINE
    applied_gamma = args.gamma
    applied_contrast = args.contrast
    if args.auto:
        stat = ImageStat.Stat(img.convert('L'))
        mean_v = stat.mean[0]
        applied_gamma = math.log(128/255) / math.log(max(1, mean_v)/255)
        applied_gamma = max(0.6, min(1.8, applied_gamma))
        applied_contrast = 25.0
        print(f"-> Auto-Pilot: G={applied_gamma:.2f}, C={applied_contrast:.1f}")

    if args.denoise:
        img = img.filter(ImageFilter.MedianFilter(size=3))

    # Keep resolution high but manageable
    img.thumbnail((450, 450))
    width, height = img.size
    pixels = img.load()
    atom_data = []
    atom_idx = 1
    
    print(f"-> Sculpting {width}x{height} image into .mae structure...")

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if r > 252 and g > 252 and b > 252: continue 

            # Color Math
            f = (259 * (applied_contrast + 255)) / (255 * (259 - applied_contrast))
            r, g, b = [max(0, min(255, int(f * (c - 128) + 128))) for c in (r, g, b)]
            r_n, g_n, b_n = [(max(0, min(255, int(255 * (c/255)**applied_gamma))) / 255.0) for c in (r, g, b)]
            hex_color = "{:02x}{:02x}{:02x}".format(int(r_n*255), int(g_n*255), int(b_n*255))
            
            brightness = (r_n + g_n + b_n) / 3.0
            pos_x_base = (x - width/2) * 0.1 * args.scale
            pos_y_base = (height/2 - y) * 0.1 * args.scale
            z_val = brightness * args.depth * args.scale

            # Hollow/Voxel logic
            z_range = [z_val] if args.mode == "project" else range(-int(z_val*3), int(z_val*3) + 1)

            for z_step in z_range:
                if args.mode == "voxel":
                    if args.hollow and len(z_range) > 2:
                        if z_step != z_range[0] and z_step != z_range[-1]: continue
                    pos_z = z_step * 0.1 * args.scale
                else:
                    pos_z = z_val

                jx, jy, jz = [p + random.uniform(-args.jitter, args.jitter) * args.scale for p in (pos_x_base, pos_y_base, pos_z)]

                # VALID ATOM LINE: Fixed-width for stability
                atom_line = (f" {atom_idx:>7}   3 {jx:10.4f} {jy:10.4f} {jz:10.4f}    1    1    6 "
                             f"{hex_color} {r_n:.4f} {g_n:.4f} {b_n:.4f} C IMG A C")
                atom_data.append(atom_line)
                atom_idx += 1

    metadata = f"M:{args.mode}|D:{args.depth}|G:{applied_gamma:.1f}|C:{applied_contrast:.0f}|H:{args.hollow}"
    header = f"""{{ \n s_m_m2io_version \n ::: \n 2.0.0 \n }} \nf_m_ct {{ \n s_m_title \n s_m_entry_id \n s_m_entry_name \n i_m_ct_format \n ::: \n "{metadata}" \n 1 \n "{metadata}" \n 2 \nm_atom[{len(atom_data)}] {{ \n i_m_mmod_type \nr_m_x_coord \nr_m_y_coord \nr_m_z_coord \ni_m_residue_number \ni_m_color \ni_m_atomic_number \ns_m_color_rgb \nr_m_color_red \nr_m_color_green \nr_m_color_blue \ns_m_atom_name \ns_m_residue_name \ns_m_chain_name \ns_m_pdb_atom_name \n::: \n"""
    
    with open(args.out, 'w') as f_out:
        f_out.write(header + "\n".join(atom_data) + "\n::: \n} \nm_bond[0] { \ni_m_from \ni_m_to \ni_m_order \n::: \n::: \n} \n}")
    return len(atom_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Photo2MAE Master Studio")
    parser.add_argument("--img", required=True, help="Input PNG/JPG")
    parser.add_argument("--out", default="render.mae", help="Output .mae file")
    parser.add_argument("--mode", choices=["project", "voxel"], default="project", help="Surface or Volume")
    parser.add_argument("--hollow", action="store_true", help="Voxel mode: Skin only")
    parser.add_argument("--auto", action="store_true", help="Auto-calculate Gamma/Contrast")
    parser.add_argument("--denoise", action="store_true", help="Median filter")
    parser.add_argument("--depth", type=float, default=2.0, help="Z-axis stretch (0.5-10.0)")
    parser.add_argument("--gamma", type=float, default=1.0, help="Brightness correction (0.1-3.0)")
    parser.add_argument("--contrast", type=float, default=20.0, help="Contrast (-255 to 255)")
    parser.add_argument("--scale", type=float, default=1.0, help="Total size scale")
    parser.add_argument("--jitter", type=float, default=0.01, help="Organic noise (0.0-0.1)")
    args = parser.parse_args()
    
    count = generate_mae_from_img(args)
    if count > 0: print(f"-> Success! {args.out} created with {count} atoms.")