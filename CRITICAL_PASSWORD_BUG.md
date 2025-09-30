# CRITICAL PASSWORD BUG - USER-WIDE ISSUE

## Status: CONFIRMED USER-WIDE AUTHENTICATION FAILURE

### Affected Users
- **CharlieB** - Cannot login (bcrypt hash)
- **TreH** - Cannot login (bcrypt hash)
- **Likely ALL 16 bcrypt users** except those who haven't tried since Sept 26

### Root Cause

The `check_password()` method in `database.py` has a **backwards compatibility bug**:

```python
def check_password(self, password: str) -> bool:
    """Check if provided password matches stored hash"""
    stored = self.password_hash or ""

    # Support accounts that were migrated to bcrypt during unauthorized changes
    if stored.startswith("$2"):
        try:
            return bcrypt_hash.verify(password, stored)
        except ValueError:
            pass  # ⚠️ BUG: This catches ALL exceptions including legitimate failures!

    # Fallback to original SHA256 hashing scheme
    return stored == self._legacy_hash(password)
```

**The Problem:**
1. When a bcrypt hash verification FAILS (wrong password), it raises `ValueError`
2. The `except ValueError: pass` silently swallows this and falls through
3. Then it tries SHA256 comparison which ALWAYS fails for bcrypt hashes
4. Result: **ALL bcrypt users with correct passwords are being rejected!**

### Why Some Users Worked Before

- TreH logged in successfully on Sept 26
- After Sept 26, something changed (possibly a passlib version update or code deployment)
- Now bcrypt.verify() is raising ValueError for failed matches instead of returning False

### Why Your Password (jcopp) Works

Your account uses SHA256 hash, so it never enters the bcrypt code path. It goes straight to the SHA256 comparison which works correctly.

### The Fix

Change line 59-61 in `database.py` from:

```python
if stored.startswith("$2"):
    try:
        return bcrypt_hash.verify(password, stored)
    except ValueError:
        pass
```

To:

```python
if stored.startswith("$2"):
    try:
        return bcrypt_hash.verify(password, stored)
    except Exception as e:
        print(f"Bcrypt verification error for user: {e}")
        return False  # ⚠️ CRITICAL: Return False instead of pass!
```

### Immediate Action Required

**Option 1: Quick Fix (RECOMMENDED)**
Deploy the fixed `database.py` with proper exception handling.

**Option 2: Emergency Workaround**
Have affected users use the password reset flow to regenerate their passwords.

### Testing the Fix

After deploying, test with CharlieB's account to verify bcrypt authentication works correctly.