import os
import time
import uuid
import threading
from datetime import datetime
import queue
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if Firebase is enabled
FIREBASE_ENABLED = os.getenv("ENABLE_FIREBASE", "false").lower() == "true"

# Only import Firebase if enabled
if FIREBASE_ENABLED:
    try:
        import firebase_admin
        from firebase_admin import credentials, db
    except ImportError:
        print("⚠️  Firebase is enabled but firebase-admin is not installed.")
        print("   Install it with: pip install firebase-admin")
        FIREBASE_ENABLED = False


# ------------------ Firebase Initialization ------------------
def initialize_firebase():
    """
    Initialize Firebase using environment variables.
    Returns True if successfully initialized, False otherwise.
    """
    if not FIREBASE_ENABLED:
        print("ℹ️  Firebase is disabled. Using local storage only.")
        return False
    
    if not firebase_admin._apps:
        try:
            creds_file = os.getenv("FIREBASE_CREDENTIALS_FILE", "firebase_credentials.json")
            database_url = os.getenv("FIREBASE_DATABASE_URL")
            
            if not os.path.exists(creds_file):
                print(f"⚠️  Firebase credentials file '{creds_file}' not found.")
                print("   Set ENABLE_FIREBASE=false in .env to disable Firebase.")
                return False
            
            if not database_url:
                print("⚠️  FIREBASE_DATABASE_URL not set in environment variables.")
                return False
            
            cred = credentials.Certificate(creds_file)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            print("✅ Firebase successfully initialized.")
            return True
        except Exception as e:
            print(f"❌ Firebase initialization error: {e}")
            return False
    return True


# ------------------ Device Code Management ------------------
def get_device_code():
    """
    Returns this device's unique pairing code.
    - First time: generates a new code (e.g., ABC123)
    - Subsequent runs: reads the same code from device_code.txt
    """
    file_path = "device_code.txt"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read().strip()
    else:
        # Generate a new code on first run
        new_code = str(uuid.uuid4())[:6].upper()  # Example: "A1B2C3"
        with open(file_path, "w") as f:
            f.write(new_code)
        print(f"📌 Generated new device code: {new_code}")
        return new_code


# ------------------ Firebase Writer Thread ------------------
class FirebaseWriterThread(threading.Thread):
    """
    Writes passenger counts to Firebase Realtime Database.
    - Real-time count -> kisi_sayimi/{device_code}/anlik_sayi
    - Daily total -> kisi_sayimi/{device_code}/daily_totals/{date}
    
    If Firebase is disabled, this thread will consume queue items without writing.
    """
    def __init__(self, in_q, stop, device_code, enabled=True):
        super().__init__()
        self.in_q = in_q
        self.stop = stop
        self.enabled = enabled
        self.device_code = device_code
        
        if self.enabled and FIREBASE_ENABLED:
            try:
                self.device_ref = db.reference(f"kisi_sayimi/{device_code}")
            except Exception as e:
                print(f"⚠️  Could not create Firebase reference: {e}")
                self.enabled = False
        else:
            self.device_ref = None
            
        self.last_sync_time = time.time()
        self.current_date = datetime.now().strftime("%Y-%m-%d")

    def run(self):
        status = "enabled" if self.enabled else "disabled"
        print(f"Firebase Writer Thread starting ({status})...")
        
        while not self.stop.is_set():
            try:
                data = self.in_q.get(timeout=0.1)
                
                # Always consume queue items even if Firebase is disabled
                if not self.enabled or not self.device_ref:
                    continue
                    
                if isinstance(data, dict) and "total_count" in data:
                    count = data["total_count"]

                    try:
                        # Update real-time count
                        self.device_ref.child("anlik_sayi").set(count)

                        # Update daily total every 5 seconds
                        if time.time() - self.last_sync_time > 5:
                            self.sync_daily_total(count)
                            self.last_sync_time = time.time()

                        # Reset if day changed
                        if datetime.now().strftime("%Y-%m-%d") != self.current_date:
                            self.sync_daily_total(count, final_sync=True)
                            self.current_date = datetime.now().strftime("%Y-%m-%d")
                    except Exception as e:
                        print(f"❌ Firebase write error: {e}")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Firebase thread error: {e}")

        print("Firebase Writer Thread stopped.")

    def sync_daily_total(self, count, final_sync=False):
        """Sync daily total to Firebase"""
        if not self.enabled or not self.device_ref:
            return
            
        try:
            daily_ref = self.device_ref.child("daily_totals").child(self.current_date)
            daily_ref.set(count)
            if final_sync:
                print(f"[SYNC] Daily total updated for {self.current_date}: {count}")
        except Exception as e:
            print(f"❌ Daily sync error: {e}")
