# Initial prototype - superseded by src/ pipeline, kept for reference.
import json
import sys
from pathlib import Path
from groq import Groq

# Ensure project root is in sys.path for Config import
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import Config

client = Groq(api_key=Config.GROQ_API_KEY)
GROQ_MODEL = Config.GROQ_MODEL

def call_groq_json(prompt):
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise data extraction assistant. Return ONLY valid JSON string without markdown formatting or code fences."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


# ============================================
# YOUR 55 TICKETS
# ============================================

tickets = [
    "Can't login, urgent! - John from NYC, premium user",
    "Billing issue: charged twice. Plz refund. - Sarah",
    "System down since 2pm. Critical! - Mike",
    "Need help with account - Emma, basic user",
    "Payment failed - David from London",
    "Can't access dashboard - premium user, urgent",
    "Subscription not working - Maria",
    "Error 404 on login - James",
    "Need refund for order #1234 - Lisa",
    "Account locked - Alex from Tokyo",
    "Password reset not working - Rachel",
    "Can't upload files - Tom, enterprise user",
    "Invoice not generated - Priya",
    "API key expired - Chris",
    "Two-factor auth not working - Kim",
    "Profile update failed - Steve",
    "Credit card declined - Anna",
    "Can't cancel subscription - Robert",
    "Missing data in reports - Laura",
    "Slow loading times - Mark, premium user",
    "Can't change email - Helen",
    "Order not delivered - Peter",
    "Support ticket not updating - Nancy",
    "Mobile app crashing - Frank",
    "Can't view invoices - Julia",
    "Dashboard showing wrong data - Kevin",
    "Export to CSV failing - Amy",
    "Search not working - Brian",
    "Can't delete account - Diana",
    "Live chat disconnected - George",
    "Webhook not receiving - Olivia",
    "SSO login failing - Liam",
    "Email verification not sent - Emma",
    "Can't mute notifications - Ava",
    "Profile picture not uploading - Noah",
    "Team invite not working - Isabella",
    "Billing address update failed - Mason",
    "Can't see team members - Sophia",
    "Integration with Slack broken - Logan",
    "Audit logs not showing - Mia",
    "Can't create new project - Ethan",
    "Task assignment not working - Charlotte",
    "Timeline view not loading - Lucas",
    "Can't add comments - Amelia",
    "File sharing permissions - Oliver",
    "Can't change timezone - Harper",
    "Export report failing - Elijah",
    "Can't view shared folder - Evelyn",
    "Notification settings reset - James",
    "Can't invite new user - Abigail",
    "Admin panel not loading - Daniel",
    "Can't edit profile - Victoria",
    "API rate limit exceeded - Ryan",
    "Can't reset password - Madison",
    "System maintenance issue - Tyler"
]

# ============================================
# EXTRACT FUNCTION
# ============================================

def extract_json(ticket):
    prompt = f"""
    Extract JSON from this support ticket:
    
    Ticket: {ticket}
    
    Return ONLY valid JSON with these fields:
    {{
      "customer_name": "string or null",
      "location": "string or null",
      "subscription_tier": "basic or premium or enterprise or null",
      "severity": "low or medium or high or critical or null",
      "issue_type": "string or null"
    }}
    """
    return call_groq_json(prompt)

def verify_json(ticket, data):
    prompt = f"""
    Check if this extraction is honest.
    
    Original ticket: {ticket}
    
    Extracted JSON:
    {json.dumps(data, indent=2)}
    
    For each field, if the value is NOT explicitly in the original text, set it to null.
    Return ONLY the corrected JSON.
    """
    return call_groq_json(prompt)

# ============================================
# PROCESS ALL TICKETS
# ============================================

print(f"🚀 Processing {len(tickets)} tickets...\n")

valid_count = 0
invalid_tickets = []

for i, ticket in enumerate(tickets):
    try:
        print(f"Ticket {i+1}/{len(tickets)}...", end=" ")
        
        # Extract
        extraction = extract_json(ticket)
        
        # Verify
        verified = verify_json(ticket, extraction)
        
        # Check if valid
        if verified.get("customer_name") is not None:
            valid_count += 1
            print("✅")
        else:
            invalid_tickets.append(i+1)
            print("❌")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        invalid_tickets.append(i+1)

# ============================================
# RESULTS
# ============================================

total = len(tickets)
rate = valid_count / total * 100

print("\n" + "=" * 50)
print("📊 YOUR RESULTS")
print("=" * 50)
print(f"Total tickets: {total}")
print(f"Valid extractions: {valid_count}")
print(f"Invalid extractions: {total - valid_count}")
print(f"Success rate: {rate:.1f}%")
print(f"Meets 90% requirement: {'✅ YES' if rate >= 90 else '❌ NO'}")

if invalid_tickets:
    print(f"\nFailed on tickets: {invalid_tickets}")

# ============================================
# SAVE REPORT
# ============================================

report = {
    "total_tickets": total,
    "valid_extractions": valid_count,
    "invalid_extractions": total - valid_count,
    "success_rate": round(rate, 1),
    "meets_90_percent_requirement": rate >= 90,
    "failed_ticket_numbers": invalid_tickets
}

with open("report.json", "w") as f:
    json.dump(report, f, indent=2)

print("\n✅ Report saved to report.json")
print("🎉 Done! Submit app.py and report.json")
