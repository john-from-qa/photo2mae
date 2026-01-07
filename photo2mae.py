import argparse
import math
from PIL import Image

def generate_mae_from_img(input_png, output_mae, depth_scale, mode, hollow, gamma, scale):
    # Load image and convert to RGB
    try:
        img = Image.open(input_png).convert('RGB')
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    # Safety resize: Millions of atoms are fine, but let's stay under "crash" limits
    if max(img.size) > 400:
        print("Image is large, resizing for better performance...")
        img.thumbnail((400, 400))
    
    width, height = img.size
    pixels = img.load()
    
    atom_data = []
    atom_idx = 1
    
    print(f"Analyzing {width}x{height} pixels...")

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            
            # Skip white background pixels (Threshold at 245)
            if r > 245 and g > 245 and b > 245:
                continue
            
            # APPLY GAMMA CORRECTION 
            # This helps match the "feel" of the photo in 3D lighting
            r_corr = int(255 * (r/255)**gamma)
            g_corr = int(255 * (g/255)**gamma)
            b_corr = int(255 * (b/255)**gamma)
            
            # Ensure values stay in 0-255 range
            r_corr = max(0, min(255, r_corr))
            g_corr = max(0, min(255, g_corr))
            b_corr = max(0, min(255, b_corr))
                
            hex_color = "{:02x}{:02x}{:02x}".format(r_corr, g_corr, b_corr)
            
            # Center and scale coordinates
            pos_x = (x - width/2) * 0.1 * scale
            pos_y = (height/2 - y) * 0.1 * scale
            brightness = (r + g + b) / 3

            if mode == "project":
                # Depth based on pixel brightness
                pos_z = (brightness / 255.0) * depth_scale * scale
                atom_data.append(f"  {atom_idx} 3 {pos_x:.4f} {pos_y:.4f} {pos_z:.4f} 1 24 6 {hex_color} A{atom_idx}")
                atom_idx += 1
            
            else: # VOXEL MODE
                thickness_val = (brightness / 255.0) * depth_scale * 3
                thickness_range = range(-int(thickness_val), int(thickness_val) + 1)
                
                for z_layer in thickness_range:
                    # HOLLOW LOGIC: Only draw surface layers
                    if hollow and len(thickness_range) > 2:
                        if z_layer != thickness_range[0] and z_layer != thickness_range[-1]:
                            continue
                        
                    pos_z = z_layer * 0.1 * scale
                    atom_data.append(f"  {atom_idx} 3 {pos_x:.4f} {pos_y:.4f} {pos_z:.4f} 1 24 6 {hex_color} V{atom_idx}")
                    atom_idx += 1

    # .mae format headers
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
 {output_mae.replace('.mae','')} 
 1 
 {output_mae.replace('.mae','')} 
  2
 m_atom[{len(atom_data)}] {{ 
  i_m_mmod_type
  r_m_x_coord
  r_m_y_coord
  r_m_z_coord
  i_m_residue_number
  i_m_color
  i_m_atomic_number
  s_m_color_rgb
  s_m_atom_name
  :::
"""

    with open(output_mae, 'w') as f:
        f.write(header)
        for row in atom_data:
            f.write(row + "\n")
        f.write("  :::\n }\n m_bond[0] {\n  i_m_from\n  i_m_to\n  i_m_order\n  :::\n  :::\n }\n}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PNG to Molecular .mae Artwork")
    parser.add_argument("--img", type=str, required=True, help="Input PNG file")
    parser.add_argument("--out", type=str, default="art_dog.mae", help="Output .mae file")
    parser.add_argument("--depth", type=float, default=2.0, help="Z-axis thickness")
    parser.add_argument("--mode", choices=["project", "voxel"], default="project", help="Surface projection or 3D volume")
    parser.add_argument("--hollow", action="store_true", help="Only render the skin in voxel mode")
    parser.add_argument("--gamma", type=float, default=1.0, help="Color vibrancy (1.0 is neutral, >1.0 is punchier)")
    parser.add_argument("--scale", type=float, default=1.0, help="Overall size of the model")
    
    args = parser.parse_args()
    
    print(f"Generating {args.out} using {args.mode} mode...")
    generate_mae_from_img(args.img, args.out, args.depth, args.mode, args.hollow, args.gamma, args.scale)
    print("Success! Load the file into your viewer.")
