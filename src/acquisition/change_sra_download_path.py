import os 
import sys

def update_sra_download_path(input_path, output_path, target_path):
    if not os.path.exists(target_path):
        os.makedirs(target_path)
    new_lines = ["#!/usr/bin/env bash"]
    with open(input_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("curl"):
                source_path = line.split('-o')[0].strip()
                file_name = source_path.split("/")[-1]
                new_line = f"{source_path} -o {target_path}/{file_name}"
                new_lines.append(new_line)
    with open(output_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python change_sra_download_path.py <input_path> <target_path>")
        sys.exit(1)
    input_path = sys.argv[1]
    target_path = sys.argv[2]
    base, ext = os.path.splitext(input_path)
    output_path = base + "_new" + ext
    update_sra_download_path(input_path, output_path, target_path)