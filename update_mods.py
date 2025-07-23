import os
import shutil
import requests
import zipfile
import tempfile

GITHUB_ZIP_URL = 'https://github.com/XDSenDX/enhanced-vanilla-client'

unwanted_mods = ['BridgingMod-2.5.1+1.20.1.forge-release.jar', 'firstperson-forge-2.4.9-mc1.20.1.jar']
choosen_unwanted_mods = []

def get_local_version(directory):
    # Always use sensmp_version.txt in the same folder as this script
    import sys
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    version_path = os.path.join(script_dir, 'sensmp_version.txt')
    if not os.path.exists(version_path):
        with open(version_path, 'w') as f:
            f.write('0.0.0\n')
        return '0.0.0', None
    with open(version_path, 'r') as f:
        lines = f.readlines()
        version = lines[0].strip() if lines else '0.0.0'
        folder = lines[1].strip() if len(lines) > 1 else None
        return version, folder


def get_remote_version():
    if not GITHUB_ZIP_URL:
        raise ValueError("GITHUB_ZIP_URL is not set.")
    # Assume main branch and standard repo structure
    if GITHUB_ZIP_URL.endswith('/'):
        repo_url = GITHUB_ZIP_URL[:-1]
    else:
        repo_url = GITHUB_ZIP_URL
    raw_url = repo_url.replace('github.com', 'raw.githubusercontent.com') + '/main/sensmp_version.txt'
    r = requests.get(raw_url)
    if r.status_code == 200:
        return r.text.strip()
    else:
        raise FileNotFoundError(f"sensmp_version.txt not found at {raw_url}")


def replace_mods(local_dir, remote_repo_dir):
    import sys
    import time
    print("\n[1/4] Preparing to sync mods folder...")


    # Parse owner/repo from GITHUB_ZIP_URL
    try:
        parts = GITHUB_ZIP_URL.rstrip('/').split('/')
        owner, repo = parts[-2], parts[-1]
    except Exception:
        print("Error: Could not parse GitHub repo URL.")
        return


    # Fetch mods
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/mods?ref=main"
    print(f"[2/4] Fetching mod list from GitHub API: {api_url}")
    r = requests.get(api_url)
    if r.status_code != 200:
        print("Error: Failed to fetch mod list from GitHub API.")
        return
    
    remote_mods_data = r.json()
    remote_mod_files = set([item['name'] for item in remote_mods_data if item['type'] == 'file' and item['name'] not in choosen_unwanted_mods])

    local_mods = os.path.join(local_dir, 'mods')
    if not os.path.exists(local_mods):
        os.makedirs(local_mods)
    local_mod_files = set(os.listdir(local_mods))


    # Download missing mods with progress bar
    missing_mods = [f for f in remote_mod_files if f not in local_mod_files]
    print(f"[3/4] Downloading {len(missing_mods)} new mods (excluding {len(choosen_unwanted_mods)} unwanted mods)...")
    for idx, mod_file in enumerate(missing_mods, 1):
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/mods/{mod_file}"
        dest_path = os.path.join(local_mods, mod_file)
        resp = requests.get(raw_url, stream=True)
        total = int(resp.headers.get('content-length', 0))
        with open(dest_path, 'wb') as f:
            downloaded = 0
            for data in resp.iter_content(chunk_size=8192):
                f.write(data)
                downloaded += len(data)
                done = int(30 * downloaded / total) if total else 0
                sys.stdout.write(f"\r    [{mod_file}] [{'#' * done}{'.' * (30 - done)}] {downloaded // 1024}KB/{total // 1024 if total else '?'}KB")
                sys.stdout.flush()
            sys.stdout.write("\n")
        time.sleep(0.1)


    # Delete local mods not present in remote
    to_delete = [f for f in local_mod_files if f not in remote_mod_files]
    print(f"[4/4] Deleting {len(to_delete)} outdated mods...")
    for mod_file in to_delete:
        print(f"    Deleting: {mod_file}")
        os.remove(os.path.join(local_mods, mod_file))
    print("\nMods folder sync complete!\n")



def update_version_file(local_dir, new_version):
    # Always update sensmp_version.txt in the same folder as this script
    import sys
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    version_path = os.path.join(script_dir, 'sensmp_version.txt')
    # Try to preserve the folder path if it exists
    folder = None
    if os.path.exists(version_path):
        with open(version_path, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                folder = lines[1].strip()
    with open(version_path, 'w') as f:
        f.write(new_version + '\n')
        if folder:
            f.write(folder + '\n')
    print(f"Updated sensmp_version.txt to {new_version} in {script_dir}")

def update_version_file_with_folder(new_version, folder_path):
    import sys
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    version_path = os.path.join(script_dir, 'sensmp_version.txt')
    with open(version_path, 'w') as f:
        f.write(new_version + '\n')
        f.write(folder_path + '\n')
    print(f"Updated sensmp_version.txt to {new_version} and saved folder path in {script_dir}")


def main():
    import sys
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    print("==== Enhanced Vanilla Client Updater ====")
    local_version, saved_mods_dir = get_local_version(script_dir)
    print(f"Current version: {local_version}")
    remote_version = get_remote_version()
    print(f"Latest version: {remote_version}")
    if local_version != remote_version:
        if saved_mods_dir and os.path.isdir(saved_mods_dir):
            mods_dir = saved_mods_dir
            print(f"Using saved mods folder: {mods_dir}")
        else:
            mods_dir = input("Enter Minecraft instance path: ").strip()
            while not os.path.isdir(mods_dir):
                print(f"Directory '{mods_dir}' does not exist. Please try again.")
                mods_dir = input("Enter Minecraft instance path: ").strip()
        
        global choosen_unwanted_mods
        # Ask if user wants not to install unwanted mods
        user_unwanted_mods = input("""
        Would you like to install these following mods [y/n/1/2]:
        1. BridgingMod
        2. First Person Viewmodel

        y - yes
        n - no
        1 - only install the 1st one
        2 - only install the 2nd one

        """)

        if user_unwanted_mods.lower() == "y":
            print("All mods will be installed.")
        elif user_unwanted_mods.lower() == "n":
            choosen_unwanted_mods = unwanted_mods.copy()
            print(f"Those {len(unwanted_mods)} mods won't be installed.")
        elif user_unwanted_mods.lower() == "1":
            # Unintuitive list method because of the inversed order - may change later
            choosen_unwanted_mods.append(unwanted_mods[1])
            print("BridgingMod chosen for installation (First Person Viewmodel won't be installed)")
        elif user_unwanted_mods.lower() == "2":
            choosen_unwanted_mods.append(unwanted_mods[0])
            print("First Person Viewmodel chosen for installation (BridgingMod won't be installed)")            
        else:
            print("Invalid syntax. Default installation will be chosen")


        print("Newer version found. Attempting to update mods...")
        replace_mods(mods_dir, None)
        print("Mods are now up-to-date.")
        update_version_file_with_folder(remote_version, mods_dir)
    else:
        print("Versions match. No action taken.")
    tmp = input("Press Enter to exit...")  # Keep the console open until user presses Enter
    
if __name__ == "__main__":
    main()
