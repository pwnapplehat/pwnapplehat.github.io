import os
import hashlib
import subprocess
import tarfile
import lzma
import shutil
import tempfile

import io
import struct

def extract_ar_members(path):
    members = {}
    with open(path, "rb") as f:
        if f.read(8) != b"!<arch>\n":
            raise ValueError("Not a valid ar archive")

        while True:
            header = f.read(60)
            if len(header) < 60:
                break

            name = header[:16].decode().strip()
            size = int(header[48:58].decode().strip())
            data = f.read(size)

            if size % 2 == 1:
                f.read(1)  # padding byte

            members[name] = data

    return members


def get_deb_info(deb_file):
    deb_info = {}

    members = extract_ar_members(deb_file)

    control_tar = None
    for key in members:
        if key.startswith("control.tar"):
            control_tar = key
            break

    if not control_tar:
        raise ValueError("No control archive found in .deb")

    control_bytes = members[control_tar]

    mode = "r:gz" if control_tar.endswith(".gz") else "r:xz"
    with tarfile.open(fileobj=io.BytesIO(control_bytes), mode=mode) as tar:
        control_member = None
        for member in tar.getmembers():
            if member.name.endswith("/control") or member.name == "control":
               control_member = member
               break

        if not control_member:
            raise ValueError("control file not found inside control.tar")

        control = tar.extractfile(control_member).read().decode("utf-8")

    for line in control.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            deb_info[k.strip()] = v.strip()

    deb_info["Size"] = os.path.getsize(deb_file)

    with open(deb_file, "rb") as f:
        data = f.read()
        deb_info["MD5"] = hashlib.md5(data).hexdigest()
        deb_info["SHA1"] = hashlib.sha1(data).hexdigest()
        deb_info["SHA256"] = hashlib.sha256(data).hexdigest()

    return deb_info

def update_packages_file():
    script_folder = os.path.dirname(os.path.realpath(__file__))
    packages_file = os.path.join(script_folder, "Packages")
    processed_packages = set()  # Keep track of processed package bundle IDs
    # Read the existing Packages file
    with open(packages_file, 'r') as f:
        packages_content = f.read()
    # Iterate through all .deb files in the script's folder
    for filename in os.listdir(script_folder):
        if filename.endswith(".deb"):
            deb_file = os.path.join(script_folder, filename)
            deb_info = get_deb_info(deb_file)
            package_id = deb_info.get('Package', '')
            # Check if the package bundle ID has already been processed
            if package_id in processed_packages:
                continue
            # Mark the package bundle ID as processed
            processed_packages.add(package_id)
            # Construct the package entry string
            package_entry = f"Package: {deb_info.get('Package', '')}\n"
            package_entry += f"Name: {deb_info.get('Name', '')}\n"
            package_entry += f"Version: {deb_info.get('Version', '')}\n"
            package_entry += f"Architecture: {deb_info.get('Architecture', '')}\n"
            package_entry += f"Depends: {deb_info.get('Depends', '')}\n"
            package_entry += f"Author: {deb_info.get('Author', '')}\n"
            package_entry += f"Maintainer: {deb_info.get('Maintainer', '')}\n"
            package_entry += f"Description: {deb_info.get('Description', '')}\n"
            package_entry += f"Size: {deb_info.get('Size', '')}\n"
            package_entry += f"MD5sum: {deb_info.get('MD5', '')}\n"
            package_entry += f"SHA1: {deb_info.get('SHA1', '')}\n"
            package_entry += f"SHA256: {deb_info.get('SHA256', '')}\n"
            package_entry += f"Section: {deb_info.get('Section', '')}\n"  # Add Section field
            # Add Icon and SileoDepiction if they exist in the control file
            if 'Icon' in deb_info:
                package_entry += f"Icon: {deb_info.get('Icon', '')}\n"
            if 'SileoDepiction' in deb_info:
                package_entry += f"SileoDepiction: {deb_info.get('SileoDepiction', '')}\n"
            # Check architecture and set the Filename path accordingly
            if deb_info.get('Architecture', '') == 'iphoneos-arm64':
                package_entry += f"Filename: ./debs/rootless/{filename}\n"
            elif deb_info.get('Architecture', '') == 'iphoneos-arm':
                package_entry += f"Filename: ./debs/rootfull/{filename}\n"
            elif deb_info.get('Architecture', '') == 'iphoneos-arm64e':
                package_entry += f"Filename: ./debs/roothide/{filename}\n"
            else:
                package_entry += f"Filename: ./debs/{filename}\n"
            # Find all occurrences of the package bundle ID in the Packages file
            start_index = 0
            while True:
                start_index = packages_content.find(f"Package: {deb_info.get('Package', '')}\n", start_index)
                if start_index == -1:
                    break
                # Find the end index of the current entry
                end_index = packages_content.find("\n\n", start_index)
                if end_index == -1:
                    end_index = len(packages_content)
                # Extract the architecture from the Packages file entry
                package_architecture = packages_content[start_index:end_index].split("Architecture: ")[1].split("\n")[0]
                # If architecture matches, replace the entry with the new package entry
                if package_architecture == deb_info.get('Architecture', ''):
                    # Preserve the spaces before and after the entry
                    start_index_with_spaces = packages_content.rfind("\n", 0, start_index) + 1
                    end_index_with_spaces = end_index + 1 if packages_content[end_index - 1] != '\n' else end_index
                    # Replace the existing entry with the new package entry
                    packages_content = packages_content[:start_index_with_spaces] + package_entry + packages_content[end_index_with_spaces:]
                    break
                # Move to the next occurrence
                start_index += len(package_entry)
    # Look for new .deb files and add entries for them
    for filename in os.listdir(script_folder):
        if filename.endswith(".deb"):
            deb_file = os.path.join(script_folder, filename)
            deb_info = get_deb_info(deb_file)
            package_id = deb_info.get('Package', '')
            # If the package bundle ID has not been processed, add a new entry
            if package_id not in processed_packages:
                package_entry = f"Package: {deb_info.get('Package', '')}\n"
                package_entry += f"Name: {deb_info.get('Name', '')}\n"
                package_entry += f"Version: {deb_info.get('Version', '')}\n"
                package_entry += f"Architecture: {deb_info.get('Architecture', '')}\n"
                package_entry += f"Depends: {deb_info.get('Depends', '')}\n"
                package_entry += f"Author: {deb_info.get('Author', '')}\n"
                package_entry += f"Maintainer: {deb_info.get('Maintainer', '')}\n"
                package_entry += f"Description: {deb_info.get('Description', '')}\n"
                package_entry += f"Size: {deb_info.get('Size', '')}\n"
                package_entry += f"MD5sum: {deb_info.get('MD5', '')}\n"
                package_entry += f"SHA1: {deb_info.get('SHA1', '')}\n"
                package_entry += f"SHA256: {deb_info.get('SHA256', '')}\n"
                package_entry += f"Section: {deb_info.get('Section', '')}\n"  # Add Section field
                # Add Icon and SileoDepiction if they exist in the control file
                if 'Icon' in deb_info:
                    package_entry += f"Icon: {deb_info.get('Icon', '')}\n"
                if 'SileoDepiction' in deb_info:
                    package_entry += f"SileoDepiction: {deb_info.get('SileoDepiction', '')}\n"
                # Check architecture and set the Filename path accordingly
                if deb_info.get('Architecture', '') == 'iphoneos-arm64':
                    package_entry += f"Filename: ./debs/rootless/{filename}\n"
                elif deb_info.get('Architecture', '') == 'iphoneos-arm':
                    package_entry += f"Filename: ./debs/rootfull/{filename}\n"
                elif deb_info.get('Architecture', '') == 'iphoneos-arm64e':
                    package_entry += f"Filename: ./debs/roothide/{filename}\n"
                else:
                    package_entry += f"Filename: ./debs/{filename}\n"
                # Append the new package entry to the Packages file content
                packages_content += f"\n{package_entry}"
    # Replace occurrences of double line breaks with a single line break
    packages_content = packages_content.replace("\n\n\n", "\n\n")
    # Write the updated content back to the Packages file
    with open(packages_file, 'w') as f:
        f.write(packages_content)

if __name__ == "__main__":
    update_packages_file()
