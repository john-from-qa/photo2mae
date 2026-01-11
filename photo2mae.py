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

    img.thumbnail((450, 450))
    width, height = img.size
    pixels = img.load()
    atom_data = []
    atom_idx = 1
    
    print(f"-> Sculpting {width}x{height} image into High-Fidelity .mae structure...")

    f = (259 * (applied_contrast + 255)) / (255 * (259 - applied_contrast))

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if r > 252 and g > 252 and b > 252: continue 

            rc, gc, bc = [max(0, min(255, int(f * (c - 128) + 128))) for c in (r, g, b)]
            rn, gn, bn = [(max(0, min(255, int(255 * (c/255)**applied_gamma))) / 255.0) for c in (rc, gc, bc)]
            
            hex_color = "{:02x}{:02x}{:02x}".format(int(rn*255), int(gn*255), int(bn*255)).upper()
            
            brightness = (rn + gn + bn) / 3.0
            pos_x = (x - width/2) * 0.1 * args.scale
            pos_y = (height/2 - y) * 0.1 * args.scale
            z_val = brightness * args.depth * args.scale

            z_range = [z_val] if args.mode == "project" else range(-int(z_val*3), int(z_val*3) + 1)

            for z_step in z_range:
                if args.mode == "voxel" and args.hollow and 1 < z_step < len(z_range)-1: continue
                pos_z = z_step * 0.1 * args.scale if args.mode == "voxel" else z_val
                jx, jy, jz = [p + random.uniform(-args.jitter, args.jitter) * args.scale for p in (pos_x, pos_y, pos_z)]

                # --- NATIVE HIGH-FIDELITY SCHEMA (25 COLUMNS) ---
                serial = 50000 + atom_idx
                atom_line = (f" {atom_idx:>7} 3 {jx:10.4f} {jy:10.4f} {jz:10.4f} 1 \"A\" 1 \"    \" \" C  \" 6 3 "
                             f"{hex_color} C{serial} 0 3 \"\" 2 \"\" {serial} {bn:.4f} {gn:.4f} {rn:.4f} 1 1 IMG")
                atom_data.append(atom_line)
                atom_idx += 1

    # --- RESTORED METADATA FEATURE ---
    metadata = f"M:{args.mode}|D:{args.depth}|G:{applied_gamma:.1f}|C:{applied_contrast:.0f}|H:{args.hollow}"

    header = f"""{{ 
 s_m_m2io_version 
 ::: 
 2.0.0 
}} 
f_m_ct {{ 
 s_m_title 
 s_m_entry_id 
 s_m_entry_name 
 i_m_ct_format 
 ::: 
 "{metadata}" 
 1 
 "{metadata}" 
  2 
 m_atom[{len(atom_data)}] {{ 
  i_m_mmod_type 
  r_m_x_coord 
  r_m_y_coord 
  r_m_z_coord 
  i_m_residue_number 
  s_m_chain_name 
  i_m_color 
  s_m_pdb_residue_name 
  s_m_pdb_atom_name 
  i_m_atomic_number 
  i_m_representation 
  s_m_color_rgb 
  s_m_atom_name 
  i_m_secondary_structure 
  i_m_ribbon_color 
  s_m_label_format 
  i_m_label_color 
  s_m_label_user_text 
  i_pdb_PDB_serial 
  r_m_color_blue 
  r_m_color_green 
  r_m_color_red 
  r_m_pdb_occupancy 
  r_m_pdb_tfactor 
  s_m_residue_name 
  ::: 
"""
    footer = """
  ::: 
 } 
 m_bond[0] { 
  i_m_from 
  i_m_to 
  i_m_order 
  ::: 
  ::: 
 } 
}"""
    
    with open(args.out, 'w') as f_out:
        f_out.write(header + "\n".join(atom_data) + footer)
    return len(atom_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Photo2MAE Master Studio")
    parser.add_argument("--img", required=True)
    parser.add_argument("--out", default="render.mae")
    parser.add_argument("--mode", choices=["project", "voxel"], default="project")
    parser.add_argument("--hollow", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--denoise", action="store_true")
    parser.add_argument("--depth", type=float, default=2.0)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=20.0)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--jitter", type=float, default=0.01)
    args = parser.parse_args()
    
    count = generate_mae_from_img(args)
    if count > 0:
        print(f"-> Success! Created {args.out} with recipe title.")