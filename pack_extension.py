import os
import argparse
import subprocess
import sys
import glob

def find_chrome_binary():
    """Attempts to locate the Google Chrome binary on the system."""
    platforms = {
        'darwin': [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ],
        'win32': [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
        ],
        'linux': [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser"
        ]
    }

    current_platform = sys.platform
    
    # Check explicitly defined paths
    if current_platform in platforms:
        for path in platforms[current_platform]:
            if os.path.exists(path):
                return path

    # Fallback: try 'which' command (shutil.which)
    import shutil
    for name in ["google-chrome", "chrome", "chromium", "google-chrome-stable"]:
        path = shutil.which(name)
        if path:
            return path
            
    return None

def pack_extension(extension_path, output_dir=".", key_path=None):
    """
    Packs a Chrome extension using the Chrome binary directly.
    """
    chrome_path = find_chrome_binary()
    if not chrome_path:
        print("Error: Could not locate Google Chrome binary.")
        return None

    print(f"Using Chrome binary at: {chrome_path}")
    
    abs_ext_path = os.path.abspath(extension_path)
    cmd = [
        chrome_path,
        f"--pack-extension={abs_ext_path}",
        "--no-message-box" # Suppress the success dialog
    ]

    # Automatic key detection logic
    if not key_path:
        parent_dir = os.path.dirname(abs_ext_path)
        base_name = os.path.basename(abs_ext_path)
        expected_pem_path = os.path.join(parent_dir, base_name + ".pem")
        
        if os.path.exists(expected_pem_path):
            key_path = expected_pem_path
            print(f"Found existing key file: {key_path}")

    if key_path:
        abs_key_path = os.path.abspath(key_path)
        if os.path.exists(abs_key_path):
            cmd.append(f"--pack-extension-key={abs_key_path}")
            print(f"Using key: {abs_key_path}")
        else:
            print(f"Warning: Key file not found at {abs_key_path}. Generating a new one.")
    
    # If output_dir is different, we need to move files later because 
    # Chrome generates .crx and .pem in the parent directory of the extension folder.
    # But wait, Chrome usually puts the .crx next to the source folder (parent dir).
    
    print(f"Packing extension from: {abs_ext_path}...")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("Chrome command executed successfully.")
        
        # Chrome creates 'CoupangScraperExtension.crx' in the SAME directory as the folder resides
        # e.g., if path is ./CoupangScraperExtension, it makes ./CoupangScraperExtension.crx
        
        parent_dir = os.path.dirname(abs_ext_path)
        base_name = os.path.basename(abs_ext_path)
        expected_crx = os.path.join(parent_dir, base_name + ".crx")
        expected_pem = os.path.join(parent_dir, base_name + ".pem")

        if os.path.exists(expected_crx):
            target_crx = os.path.join(output_dir, base_name + ".crx")
            
            # Move/Copy to output_dir if needed
            if os.path.abspath(expected_crx) != os.path.abspath(target_crx):
                import shutil
                shutil.move(expected_crx, target_crx)
                print(f"Moved CRX to: {target_crx}")
                return target_crx
            
            print(f"CRX created at: {expected_crx}")
            return expected_crx
        else:
            print("Error: .crx file was not found after running Chrome.")
            print(f"Expected location: {expected_crx}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"Error running Chrome command: {e}")
        print(f"Stderr: {e.stderr.decode()}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pack a Chrome extension.")
    parser.add_argument("extension_path", help="Path to extension directory")
    parser.add_argument("--output_dir", default=".", help="Output directory for .crx")
    parser.add_argument("--key_path", default=None, help="Private key (.pem) path")

    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    pack_extension(args.extension_path, args.output_dir, args.key_path)