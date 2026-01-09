import requests
import time
import sys
import os

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/"

def test_health():
    print(f"Checking server health at {HEALTH_URL}...")
    try:
        response = requests.get(HEALTH_URL)
        if response.status_code == 200:
            print("Server is UP!")
            print(response.json())
            return True
        else:
            print(f"Server returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Is it running?")
        print("Run: uvicorn app.main:app --reload")
        return False

def test_upload_broll(broll_paths):
    print(f"\nTesting /upload-broll with {len(broll_paths)} files...")
    url = f"{BASE_URL}/upload-broll"
    
    files = []
    opened_files = []
    
    try:
        for path in broll_paths:
            if not os.path.exists(path):
                print(f"Skipping missing file: {path}")
                continue
            f = open(path, "rb")
            opened_files.append(f)
            files.append(("files", (os.path.basename(path), f, "video/mp4")))
        
        if not files:
            print("No valid files to upload.")
            return

        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            print("Upload Successful!")
            print(response.json())
        else:
            print(f"Upload Failed: {response.text}")
            
    finally:
        for f in opened_files:
            f.close()

def test_process_timeline(a_roll_path):
    print(f"\nTesting /process-timeline with {a_roll_path}...")
    url = f"{BASE_URL}/process-timeline"
    
    if not os.path.exists(a_roll_path):
        print(f"A-roll file not found: {a_roll_path}")
        return None

    with open(a_roll_path, "rb") as f:
        files = {"file": (os.path.basename(a_roll_path), f, "video/mp4")}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        data = response.json()
        task_id = data.get("task_id")
        print(f"Processing started! Task ID: {task_id}")
        return task_id
    else:
        print(f"Processing Failed: {response.text}")
        return None

def poll_status(task_id):
    print(f"\nPolling status for task {task_id}...")
    url = f"{BASE_URL}/status/{task_id}"
    
    while True:
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error checking status: {response.status_code}")
                break
            
            data = response.json()
            status = data.get("status")
            step = data.get("step", "unknown")
            
            sys.stdout.write(f"\rCurrent Status: {status} (Step: {step})   ")
            sys.stdout.flush()
            
            if status in ["completed", "failed"]:
                print("\n")
                print("Final Result:")
                print(data)
                break
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\nPolling stopped.")
            break

if __name__ == "__main__":
    # Create some dummy or use real video paths
    BROLL_FILES = [
        r"c:\Users\karan\OneDrive\Desktop\Projects\ContextCut\data\uploads\broll_1.mp4",
        r"c:\Users\karan\OneDrive\Desktop\Projects\ContextCut\data\uploads\broll_2.mp4",
        r"c:\Users\karan\OneDrive\Desktop\Projects\ContextCut\data\uploads\broll_3.mp4",
        r"c:\Users\karan\OneDrive\Desktop\Projects\ContextCut\data\uploads\broll_4.mp4",
        r"c:\Users\karan\OneDrive\Desktop\Projects\ContextCut\data\uploads\broll_5.mp4",
        r"c:\Users\karan\OneDrive\Desktop\Projects\ContextCut\data\uploads\broll_6.mp4"
    ]
    
    AROLL_FILE = r"c:\Users\karan\OneDrive\Desktop\Projects\ContextCut\data\uploads\a_roll.mp4" 
    
    print("--- ContextCut API Test ---")
    
    if not test_health():
        sys.exit(1)
        
    if not BROLL_FILES and not os.path.exists(AROLL_FILE):
        print("\nPLEASE EDIT THIS SCRIPT to set valid 'BROLL_FILES' and 'AROLL_FILE' paths.")
        print(f"Script location: {os.path.abspath(__file__)}")
        sys.exit(0)

    if BROLL_FILES:
        test_upload_broll(BROLL_FILES)
    
    if os.path.exists(AROLL_FILE):
        task_id = test_process_timeline(AROLL_FILE)
        if task_id:
            poll_status(task_id)
