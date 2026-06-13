"""
Train Studio — Mac Calendar Sync
Διαβάζει εκδηλώσεις από το Mac Calendar και τις στέλνει στη Supabase.
Τρέξε: python3 sync_calendar.py
"""

import subprocess
import json
import urllib.request
import urllib.parse
from datetime import date, datetime
import hashlib

# ══ ΡΥΘΜΙΣΕΙΣ ══════════════════════════════════════════════════════
SUPABASE_URL = "https://dhignagzgufqkhizgqrl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRoaWduYWd6Z3VmcWtoaXpncXJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyOTUzOTEsImV4cCI6MjA5NDg3MTM5MX0.j6oNTTiPZCFEhIqwkDLBfba7ouNkOEPPnHwk4WVI8Xg"
CALENDAR_NAME = "Train 22 ΔΜΓΚ cloud"
TODAY = date.today().strftime("%Y-%m-%d")
# ═══════════════════════════════════════════════════════════════════

def get_events_from_calendar():
    """Διαβάζει εκδηλώσεις από το Mac Calendar μέσω EventKit (Python)"""
    try:
        import EventKit
        import objc
        from Foundation import NSDate, NSCalendar, NSDateComponents
        from datetime import timezone
    except ImportError:
        print("⚠️  Δεν βρέθηκε EventKit, χρήση AppleScript...")
        return get_events_applescript()

    store = EventKit.EKEventStore.alloc().init()

    # Ζήτα πρόσβαση
    granted = [None]
    def handler(g, e):
        granted[0] = g
    store.requestAccessToEntityType_completion_(EventKit.EKEntityTypeEvent, handler)

    import time
    for _ in range(30):
        if granted[0] is not None:
            break
        time.sleep(0.1)

    if not granted[0]:
        print("❌ Δεν δόθηκε πρόσβαση στο Calendar — χρήση AppleScript...")
        return get_events_applescript()

    # Βρες το ημερολόγιο
    target_cal = None
    for cal in store.calendars():
        if cal.title() == CALENDAR_NAME:
            target_cal = cal
            break

    if not target_cal:
        print(f"❌ Δεν βρέθηκε ημερολόγιο: {CALENDAR_NAME}")
        return []

    # Εύρος ημερομηνιών: σήμερα → +2 χρόνια
    now = NSDate.date()
    future = NSDate.dateWithTimeIntervalSinceNow_(2 * 365 * 24 * 3600)
    pred = store.predicateForEventsWithStartDate_endDate_calendars_(now, future, [target_cal])
    ek_events = store.eventsMatchingPredicate_(pred)

    events = []
    seen_ids = set()

    for ev in ek_events:
        try:
            title = str(ev.title() or '').replace('"', '').replace("'", '').strip()
            if not title:
                continue

            start = ev.startDate()
            end = ev.endDate()

            # Μετατροπή σε Python datetime
            import datetime as dt
            ts_start = start.timeIntervalSince1970()
            ts_end = end.timeIntervalSince1970()

            import time
            local_start = dt.datetime.fromtimestamp(ts_start)
            local_end = dt.datetime.fromtimestamp(ts_end)

            date_str = local_start.strftime("%Y-%m-%d")
            time_str = local_start.strftime("%H:%M") + "-" + local_end.strftime("%H:%M")

            if date_str < TODAY:
                continue

            s = title.lower()
            if any(x in s for x in ["μεγαρ", "καψ", "kappa", "art box"]):
                cat = "megaro"
            elif "στουντ" in s or "studio" in s:
                cat = "studio"
            elif "δσ" in s or "δ.σ" in s:
                cat = "ds"
            elif any(x in s for x in ["εγκατ", "setup", "εγκαταστ"]):
                cat = "setup"
            elif "presetup" in s or "pre setup" in s or "pre-setup" in s:
                cat = "presetup"
            else:
                cat = "other"

            # Χρησιμοποίησε το σταθερό Calendar UID
            cal_uid = str(ev.eventIdentifier() or '')
            if cal_uid:
                ev_id = __import__("hashlib").md5(cal_uid.encode()).hexdigest()[:12]
            else:
                ev_id = __import__("hashlib").md5((title + date_str + time_str).encode()).hexdigest()[:12]

            if ev_id in seen_ids:
                print(f"⚠️  Duplicate παραλείφθηκε: {title} ({date_str})")
                continue
            seen_ids.add(ev_id)

            events.append({"id": ev_id, "title": title, "date": date_str, "time": time_str, "cat": cat})
            print(f"  📌 {date_str} | {title} | {time_str}")
        except Exception as ex:
            print(f"  ⚠️  Σφάλμα event: {ex}")
            continue

    return events


def get_events_applescript():
    """Fallback: AppleScript με αυξημένο timeout"""
    cal_name = CALENDAR_NAME
    script = f"""
    with timeout of 60 seconds
    tell application "Calendar"
        set output to ""
        set targetCal to calendar "{cal_name}"
        set today to current date
        set hours of today to 0
        set minutes of today to 0
        set seconds of today to 0
        set evList to (every event of targetCal whose start date >= today)
        repeat with ev in evList
            set evTitle to summary of ev
            set evStart to start date of ev
            set evEnd to end date of ev
            set y to year of evStart as string
            set m to month of evStart as integer
            set d to day of evStart as integer
            set h to hours of evStart as integer
            set mi to minutes of evStart as integer
            set eh to hours of evEnd as integer
            set emi to minutes of evEnd as integer
            if m < 10 then set m to "0" & m
            if d < 10 then set d to "0" & d
            if h < 10 then set h to "0" & h
            if mi < 10 then set mi to "0" & mi
            if eh < 10 then set eh to "0" & eh
            if emi < 10 then set emi to "0" & emi
            set dateStr to y & "-" & m & "-" & d
            set timeStr to h & ":" & mi & "-" & eh & ":" & emi
            set evUID to uid of ev
            set output to output & evTitle & "|" & dateStr & "|" & timeStr & "|" & evUID & "\n"
        end repeat
        return output
    end tell
    end timeout
    """

    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"❌ Σφάλμα AppleScript: {result.stderr}")
        print("⚠️  Παράλειψη διαγραφής — δεν επιβεβαιώθηκε η ανάγνωση Calendar")
        return None  # None = αποτυχία, όχι άδεια λίστα

    events = []
    seen_ids = set()  # για αποφυγή duplicates

    for i, line in enumerate(result.stdout.strip().split('\n')):
        if '|' not in line:
            continue
        parts = line.split('|')
        if len(parts) < 3:
            continue

        title = parts[0].strip().replace('"', '').replace("'", '')
        date_str = parts[1].strip()
        time_str = parts[2].strip()
        uid = parts[3].strip() if len(parts) > 3 else ''

        if date_str < TODAY:
            continue

        s = title.lower()
        if any(x in s for x in ['μεγαρ', 'καψ', 'kappa', 'art box']):
            cat = 'megaro'
        elif 'στουντ' in s or 'studio' in s:
            cat = 'studio'
        elif 'δσ' in s or 'δ.σ' in s:
            cat = 'ds'
        elif any(x in s for x in ['εγκατ', 'setup', 'εγκαταστ']):
            cat = 'setup'
        elif 'presetup' in s or 'pre setup' in s or 'pre-setup' in s:
            cat = 'presetup'
        else:
            cat = 'other'

        # ID: από Calendar UID (σταθερό — δεν αλλάζει με αλλαγή ώρας/τίτλου)
        if uid:
            ev_id = hashlib.md5(uid.encode()).hexdigest()[:12]
        else:
            ev_id = hashlib.md5((title + date_str + time_str).encode()).hexdigest()[:12]

        # Αποφυγή duplicates
        if ev_id in seen_ids:
            print(f"⚠️  Duplicate παραλείφθηκε: {title} ({date_str})")
            continue
        seen_ids.add(ev_id)

        events.append({
            "id": ev_id,
            "title": title,
            "date": date_str,
            "time": time_str,
            "cat": cat
        })
        print(f"  📌 {date_str} | {title} | {time_str}")

    return events

def delete_removed_events(current_ids):
    """Διαγράφει από τη Supabase εκδηλώσεις που δεν υπάρχουν πλέον στο Calendar"""
    # Πάρε όλα τα future events από Supabase
    url = f"{SUPABASE_URL}/rest/v1/events?select=id,date&date=gte.{TODAY}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req) as resp:
            sb_events = json.loads(resp.read())
    except Exception as e:
        print(f"❌ Σφάλμα ανάγνωσης Supabase: {e}")
        return

    # Βρες IDs που υπάρχουν στη Supabase αλλά ΌΧΙ στο Calendar
    sb_ids = {e['id'] for e in sb_events}
    to_delete = sb_ids - set(current_ids)

    if not to_delete:
        print("✅ Δεν υπάρχουν διαγραμμένες εκδηλώσεις.")
        return

    print(f"🗑️  Διαγραφή {len(to_delete)} εκδηλώσεων που αφαιρέθηκαν από το Calendar...")
    for ev_id in to_delete:
        del_url = f"{SUPABASE_URL}/rest/v1/events?id=eq.{ev_id}"
        del_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Prefer": "return=minimal"
        }
        del_req = urllib.request.Request(del_url, headers=del_headers, method='DELETE')
        try:
            with urllib.request.urlopen(del_req) as r:
                print(f"  🗑️  Διαγράφηκε: {ev_id}")
        except Exception as e:
            print(f"  ❌ Σφάλμα διαγραφής {ev_id}: {e}")

def sync_to_supabase(events):
    """Στέλνει εκδηλώσεις στη Supabase με upsert (ενημέρωση ή δημιουργία)"""
    url = f"{SUPABASE_URL}/rest/v1/events"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        # upsert: αν υπάρχει το ID, ενημέρωσε μόνο title/date/time/cat
        # ΔΕΝ αγγίζει assigned/roles/responses
        "Prefer": "resolution=merge-duplicates,return=minimal"
    }
    data = json.dumps(events).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"✅ {len(events)} εκδηλώσεις συγχρονίστηκαν!")
    except Exception as e:
        print(f"❌ Σφάλμα Supabase: {e}")

def cleanup_duplicates():
    """Διαγράφει εγγραφές με μακρύ ID (παλιές λανθασμένες εγγραφές)"""
    url = f"{SUPABASE_URL}/rest/v1/events?select=id"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req) as resp:
            all_events = json.loads(resp.read())
        
        # Βρες IDs που είναι πάνω από 12 χαρακτήρες (λανθασμένα)
        bad_ids = [e['id'] for e in all_events if len(str(e['id'])) > 12]
        
        if not bad_ids:
            print("✅ Δεν βρέθηκαν λανθασμένα IDs.")
            return
            
        print(f"🧹 Βρέθηκαν {len(bad_ids)} λανθασμένες εγγραφές — διαγραφή...")
        
        for bad_id in bad_ids:
            del_url = f"{SUPABASE_URL}/rest/v1/events?id=eq.{bad_id}"
            del_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Prefer": "return=minimal"
            }
            del_req = urllib.request.Request(del_url, headers=del_headers, method='DELETE')
            try:
                with urllib.request.urlopen(del_req) as r:
                    pass
            except Exception as e:
                print(f"  ❌ Σφάλμα διαγραφής {bad_id}: {e}")
        
        print(f"✅ Διαγράφηκαν {len(bad_ids)} λανθασμένες εγγραφές.")
    except Exception as e:
        print(f"❌ Σφάλμα cleanup: {e}")

if __name__ == "__main__":
    print(f"🔄 Συγχρονισμός Calendar → Supabase ({datetime.now().strftime('%H:%M %d/%m/%Y')})")
    print(f"🧹 Καθαρισμός λανθασμένων εγγραφών...")
    cleanup_duplicates()
    print(f"📅 Ανάγνωση εκδηλώσεων από το Calendar...")
    events = get_events_from_calendar()
    print(f"📊 Βρέθηκαν {len(events)} εκδηλώσεις από σήμερα")
    if events is None:
        print("⛔ Αποτυχία ανάγνωσης Calendar — δεν γίνεται καμία αλλαγή στη Supabase.")
    elif len(events) == 0:
        print("⚠️  Δεν βρέθηκαν εκδηλώσεις — παράλειψη διαγραφής για ασφάλεια.")
    else:
        current_ids = [e['id'] for e in events]
        print(f"🗑️  Έλεγχος για διαγραμμένες εκδηλώσεις...")
        delete_removed_events(current_ids)
        sync_to_supabase(events)
