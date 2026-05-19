import random
import time

# In-memory OTP store: {phone: {"otp": "...", "expires": timestamp}}
otp_store = {}

# Forgot-password attempt tracking: {identifier: {"attempts": int, "locked_until": timestamp}}
fp_attempts = {}

OTP_EXPIRY_SECONDS  = 300   # 5 minutes
MAX_FP_ATTEMPTS     = 2
FP_LOCKOUT_SECONDS  = 86400  # 24 hours


def generate_otp(phone):
    """Generate a 6-digit OTP and store it with an expiry time."""
    otp = str(random.randint(100000, 999999))
    otp_store[phone] = {
        "otp":     otp,
        "expires": time.time() + OTP_EXPIRY_SECONDS
    }
    print(f"[OTP] Code for {phone}: {otp}  (valid 5 min)")
    return otp


def verify_otp(phone, entered_otp):
    """Verify the OTP. Returns True if valid and not expired."""
    record = otp_store.get(phone)
    if not record:
        return False
    if time.time() > record["expires"]:
        del otp_store[phone]
        return False
    if record["otp"] == str(entered_otp).strip():
        del otp_store[phone]
        return True
    return False


def get_otp_for_display(phone):
    """Returns current OTP for display purposes (dev/demo mode only)."""
    record = otp_store.get(phone)
    if record and time.time() <= record["expires"]:
        return record["otp"]
    return None


# ──────────────────────────────────────────────
#  FORGOT PASSWORD ATTEMPT TRACKING
# ──────────────────────────────────────────────

def is_fp_locked(identifier):
    """Return (locked: bool, seconds_remaining: int)."""
    rec = fp_attempts.get(identifier)
    if not rec:
        return False, 0
    if rec["attempts"] >= MAX_FP_ATTEMPTS:
        remaining = rec.get("locked_until", 0) - time.time()
        if remaining > 0:
            return True, int(remaining)
        else:
            # Lock expired — reset
            del fp_attempts[identifier]
            return False, 0
    return False, 0


def record_fp_failure(identifier):
    """Record a failed forgot-password attempt. Returns attempts used."""
    if identifier not in fp_attempts:
        fp_attempts[identifier] = {"attempts": 0, "locked_until": 0}
    fp_attempts[identifier]["attempts"] += 1
    attempts = fp_attempts[identifier]["attempts"]
    if attempts >= MAX_FP_ATTEMPTS:
        fp_attempts[identifier]["locked_until"] = time.time() + FP_LOCKOUT_SECONDS
    return attempts


def reset_fp_attempts(identifier):
    """Clear attempt counter after successful reset."""
    if identifier in fp_attempts:
        del fp_attempts[identifier]


def fp_attempts_left(identifier):
    """How many attempts remain before lockout."""
    rec = fp_attempts.get(identifier)
    if not rec:
        return MAX_FP_ATTEMPTS
    return max(0, MAX_FP_ATTEMPTS - rec["attempts"])
