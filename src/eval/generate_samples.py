import json
import re
import sys
from pathlib import Path
import anthropic

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import Config


def extract_json_from_text(text: str) -> list:
    """Helper to extract a JSON list from markdown or raw text output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON list from model response: {text[:200]}...")


def get_fallback_synthetic_tickets() -> list:
    """Provides a rich dataset of 55 realistic noisy tickets if Anthropic API credits/key fail."""
    tickets = [
        # Batch 1 (1-11): Short/long extremes & missing fields
        ("ticket_001.txt", "Hi, I cannot access my dashboard since morning. - John", "ticket_001: extremely short (1 sentence), missing email and priority"),
        ("ticket_002.txt", "Charged twice on my credit card ending in 4321 for May subscription. Please refund immediately.", "ticket_002: missing customer name and email, billing category"),
        ("ticket_003.txt", "I have been a loyal customer for 6 years now, started back in 2020 when my startup was just 3 people in a garage. We moved offices three times since then and our team grew. Yesterday my cofounder Sarah told me she couldn't download the PDF export from our monthly analytics report. We tried clearing cache, switching browsers from Chrome to Safari, and even rebooted the Wi-Fi router. Still gives a 500 server error when clicking export. We really need this fixed before our board meeting on Friday.", "ticket_003: extremely long rambling personal context, technical category, priority implied"),
        ("ticket_004.txt", "Password reset link sent to my inbox is expired every time I click it. Account tier: pro. Email: alex@example.com", "ticket_004: account category, missing priority and full name"),
        ("ticket_005.txt", "Feature request: can you add dark mode to the mobile iOS application? Would be super helpful when checking metrics at night. Thanks!", "ticket_005: other/feature request category, low priority implied, missing email"),
        ("ticket_006.txt", "HELP!! My API keys stopped working at 3 AM after we upgraded our billing plan to enterprise!!", "ticket_006: missing email/name, urgent priority implied, technical/billing"),
        ("ticket_007.txt", "Can I get an invoice with our company VAT number IE1234567X added to last month's receipt? Email: accounting@corp.com", "ticket_007: billing category, missing priority"),
        ("ticket_008.txt", "Hello support team, when I try to add a new seat for a teammate it says 'maximum users reached' but we are on the Enterprise unlimited plan. Please check our account status. - David Kim (david@acme.org)", "ticket_008: account/billing category, high priority"),
        ("ticket_009.txt", "Where do I update my profile picture?", "ticket_009: extremely short (1 sentence), account category, low priority"),
        ("ticket_010.txt", "Server response time is over 8000ms on the /v2/query endpoint since 14:00 UTC today. We are seeing timeouts across all our European clients. Priority: URGENT. Contact: devops@techgrid.io", "ticket_010: technical category, urgent priority, explicit contact"),
        ("ticket_011.txt", "Is there any discount available for non-profit educational organizations?", "ticket_011: other/billing category, missing contact details and priority"),

        # Batch 2 (12-22): Typos, formatting (all caps, no punctuation), code-switching
        ("ticket_012.txt", "I AM TRYING TO UPGRADE MY PLAN FROM FREE TO PRO BUT YOUR PAYMNT GATEWY KEEPS REJECTING MY VISA CARD PLEASE FIX IMMEDIATELY WE CANNOT RUN WORKFLOWS WITHOUT THIS!!!!", "ticket_012: ALL CAPS, typos, excessive exclamation, billing/account overlap"),
        ("ticket_013.txt", "Mera account lock ho gaya hai and I cannot reset my password after trying 5 times. Please help fast, urgent hai billing kal due hai and team is blocked. Email: rahul.s@domain.in", "ticket_013: mixed English/Hindi code-switching, account/billing overlap, urgent priority"),
        ("ticket_014.txt", "cant logn to my accnt after changing pasword yesterday says invalid credentils even tho i saved in bitwarden plz fix asap thx", "ticket_014: severe typos, no punctuation, informal slang, technical/account"),
        ("ticket_015.txt", "WHY IS MY INVOISE SHOWING $149 WHEN I SIGNED UP WITH THE 20% OFF PROMO CODE??? REFUND THE DIFFERENCE NOW OR I CANCEL MY SUBSCRIPTON", "ticket_015: ALL CAPS, typos (invoise, subscripton), billing category, high priority"),
        ("ticket_016.txt", "hello i tried to export the csv file but nothing downloads no error message no loading spinner just nothing happens please look into this my email is mark@test.com", "ticket_016: run-on sentence, no punctuation or capitalization, technical category"),
        ("ticket_017.txt", "cannoct connect webhook to slack channel keeps getting 403 forbiden error after token refresh priority medium", "ticket_017: typos, explicit priority, technical category"),
        ("ticket_018.txt", "WEBSITE BROKEN ON ANDROID TABLET SCREEN OVERLAPS BUTTONS SO WE CANNOT CLICK SUBMIT TICKET FORM OR SETTINGS PAGE", "ticket_018: ALL CAPS, technical UI bug, missing contact info"),
        ("ticket_019.txt", "blled twice this month for pro tier $49 + $49 check my account ID 88910 immediately", "ticket_019: typos (blled), missing email/name, billing category"),
        ("ticket_020.txt", "how to delete account permanently??? and will my stored data be wiped immediately???", "ticket_020: account category, multiple question marks, missing contact/tier"),
        ("ticket_021.txt", "got error code ERR_SSL_PROTOCOL_ERROR when visiting custom domain app.client.com after setting up CNAME record according to docs", "ticket_021: technical category, SSL domain issue, missing email"),
        ("ticket_022.txt", "plz change my email address from old@yahoo.com to new@gmail.com asap thx!! - Sarah", "ticket_022: informal slang (plz, asap, thx), account category"),

        # Batch 3 (23-33): Category ambiguity & rambling customer language
        ("ticket_023.txt", "I was trying to update our expired corporate Mastercard on the billing page so our Pro tier subscription wouldn't get cancelled, but right when I clicked 'Save Card' the screen froze and now my entire account is locked out saying 'Suspended due to billing error'. I cannot even log in to see my previous invoices or access our project workspaces. Is this a billing problem or is my user account permanently banned?", "ticket_023: genuine category ambiguity (billing vs account), detailed narrative"),
        ("ticket_024.txt", "Honestly your support history has been terrible. Three weeks ago I reported a slow widget, then two weeks ago your email notifications stopped arriving, and every time I get canned responses from a bot. Now today, what really broke the camel's back is that our monthly enterprise charge billed us for 50 extra seats we never invited! I am sick of these errors. Get a human manager to review our invoice right now.", "ticket_024: rambling customer complaints before stating actual billing issue"),
        ("ticket_025.txt", "When we downgraded our subscription plan from Enterprise to Pro last Thursday because our contract renewed at a lower volume, our admin dashboard suddenly lost access to the SAML SSO configuration. Now half our team can't log in because SSO is disabled on Pro, but we still have an open balance credit of $1,200 from the downgrade. Can you either apply the credit to turn SSO back on or refund our balance so we can switch authentication providers?", "ticket_025: category ambiguity (billing vs technical vs account)"),
        ("ticket_026.txt", "I am writing to express my frustration regarding the recent layout redesign of your reporting tab. My team spent hours training interns on the old workflow, and without any heads up warning you moved the export buttons inside a dropdown menu. On top of this UI confusion, whenever we select 'Last 90 Days' in the filter box, the query returns 0 rows even though we have thousands of records. Fix the 90 day filter bug.", "ticket_026: rambling UI feedback leading into a technical bug report"),
        ("ticket_027.txt", "We attempted to change our account tier from Free to Pro during checkout, but the payment failed with 'Insufficient Funds' even though our bank confirmed the charge went through. Now my account shows 'Free Tier' but my bank statement shows -$99 deducted. Please check if our account is Pro or Free and fix the discrepancy.", "ticket_027: category ambiguity (billing vs account tier mismatch)"),
        ("ticket_028.txt", "Need assistance right away with two-factor authentication. My phone was damaged in water during my vacation last weekend and I lost my Google Authenticator app. When I try to use backup recovery codes, it says 'Code already redeemed or expired'. We have payroll due tomorrow morning and I am the sole admin on the account. Urgent help required! - Robert Taylor (rtaylor@logistics.net)", "ticket_028: account category, urgent priority, clear contact info"),
        ("ticket_029.txt", "Why did I get an email saying our account will be downgraded in 3 days due to payment failure? We have autopay enabled on our company Amex. Please review our billing status.", "ticket_029: billing/account overlap, missing priority"),
        ("ticket_030.txt", "Whenever someone gets a chance, no rush at all, could you clarify what timezone the daily cron export runs in? We are trying to align it with our local JST schedule. Thanks, Kenji", "ticket_030: low priority explicit ('whenever someone gets a chance no rush'), other/technical"),
        ("ticket_031.txt", "Hi, my name is Lisa and I manage operations for a design agency. We recently onboarded 15 freelance contractors for a summer campaign and needed to give them restricted view-only access. However, when I go to User Management -> Roles, the 'View Only' checkbox is grayed out. Is this because we are on the Pro tier instead of Enterprise, or is it a permission bug?", "ticket_031: category ambiguity (technical bug vs account tier limitations)"),
        ("ticket_032.txt", "Our accounting department needs to update the billing contact email from finance-old@company.com to billing-new@company.com before the next cycle on the 1st.", "ticket_032: billing/account category, low/medium priority"),
        ("ticket_033.txt", "API rate limit exceeded error (HTTP 429) occurs even when we are sending less than 10 requests per second. Our Enterprise SLA guarantees 100 req/sec. Please investigate our API quota limits right away.", "ticket_033: technical/account category, high priority"),

        # Batch 4 (34-44): Corporate vs free tier tones, email threads, chat logs
        ("ticket_034.txt", "---------- Forwarded message ---------\nFrom: System Admin <admin@globalfinance.com>\nDate: Thu, Jul 16, 2026 at 11:42 AM\nSubject: Fwd: CRITICAL: Database sync lag\nTo: Support <support@vendor.com>\n\nWe are experiencing a 45-minute replication lag on the primary data pipeline. This breaches our Enterprise Tier 1 SLA. Immediate escalation to tier 3 engineering is requested.", "ticket_034: email forward format, demanding enterprise tone, urgent priority"),
        ("ticket_035.txt", "Chat Transcript #8812\n[14:02] User: hi there\n[14:03] User: i am on the free plan and trying to invite my friend to collaborate\n[14:04] User: but when they click the invite email link it says 'Workspace not found'\n[14:05] User: can u check why the invite is broken?", "ticket_035: live chat transcript format, free tier tone, technical/account"),
        ("ticket_036.txt", "As an Enterprise customer paying over $50k annually, we expect better communication regarding scheduled maintenance windows. Yesterday's 20-minute downtime caused significant disruption to our call center operations. We require a formal incident post-mortem (RCA document) by end of week.", "ticket_036: enterprise tone, other/feedback/technical category, high importance"),
        ("ticket_037.txt", "hey so basically i signed up for free trial yesterday and didn't know it would auto charge me $29 today because i forgot to cancel... am a student on tight budget please can i get a refund? really sorry about this", "ticket_037: free tier/student tone, polite/apologetic, billing refund request"),
        ("ticket_038.txt", "Fwd: Re: Login issues\nCan someone look at this? The new user onboarding link keeps looping back to the welcome screen after filling out company details. Tested on Windows 11 Edge browser.", "ticket_038: email forward format, technical bug report, missing contact/tier"),
        ("ticket_039.txt", "Our compliance audit requires us to enable HIPAA audit logs. Where in the Enterprise security console can we download the 1-year retention logs? Contact: ciso@healthtech.org", "ticket_039: enterprise compliance query, account/other category"),
        ("ticket_040.txt", "System error code 0x80040154 when initializing SDK on Windows Server 2022. Occurs only on 64-bit builds. Priority: High.", "ticket_040: concise technical bug with hex code, high priority, missing email"),
        ("ticket_041.txt", "Hi! Just wondering if there is any update on ticket #4419 regarding our custom domain SSL certificate? No hurry, just checking in when you have a moment. Thanks!", "ticket_041: follow-up ticket, low priority, polite tone"),
        ("ticket_042.txt", "Our invoice #INV-9921 shows sales tax charged for New York, but our organization is tax-exempt under 501(c)(3). I attached our exemption certificate to our profile last month. Please remove tax from invoice and re-issue.", "ticket_042: billing tax exemption issue, corporate tone"),
        ("ticket_043.txt", "User 'jsmith@client.com' is unable to view the shared dashboard folder despite being assigned the Editor role by admin.", "ticket_043: third-person admin reporting account permission issue"),
        ("ticket_044.txt", "Is there a way to export invoice history as a single ZIP file instead of downloading 24 individual PDFs one by one?", "ticket_044: billing/feature request, low/medium priority"),

        # Batch 5 (45-55): Edge cases & mixed noise profiles
        ("ticket_045.txt", "BROKEN APP!! FIX IT RIGHT NOW OR WE LEAVE!!", "ticket_045: ALL CAPS, zero details, urgent tone, missing contact and exact issue"),
        ("ticket_046.txt", "hi our team noticed that when you toggle 'Auto-Save' off, navigating away from the page still prompts the confirmation dialog twice in a row. Minor annoyance but would be great to fix in the next release. - Elena", "ticket_046: polite minor technical UI bug, low priority"),
        ("ticket_047.txt", "ACCOUNT SUSPENDED WITHOUT WARNING FOR 'TERMS VIOLATION' BUT WE ONLY USE THE ACCOUNT FOR INTERNAL WEEKLY METRICS. PLEASE REVIEW AND UNBLOCK ASAP. TIER: ENTERPRISE. EMAIL: ADMIN@CORP-GLOBAL.COM", "ticket_047: ALL CAPS, account suspension, enterprise tier, urgent priority"),
        ("ticket_048.txt", "Please cancel my pro subscription effective at the end of the current billing cycle on August 1st. Do not charge my card again. Confirmation email to: mike.brown@gmail.com", "ticket_048: clear billing cancellation request, medium priority"),
        ("ticket_049.txt", "We get '504 Gateway Timeout' on the batch upload tool whenever CSV files exceed 15MB. The documentation says the limit is 50MB. We have daily data pipelines waiting on this.", "ticket_049: technical upload discrepancy, high priority implied"),
        ("ticket_050.txt", "Can you change our primary domain name from old-brand.com to new-brand.com? We rebranded last week and want our workspace URLs to reflect the new name.", "ticket_050: account/workspace configuration query"),
        ("ticket_051.txt", "i think my account was hacked someone from ip 185.220.x.x accessed my dashboard and deleted 3 projects!! please freeze account and restore backup immediately!! email: urgent@user.com", "ticket_051: security breach, no capitalization, urgent priority, account/technical"),
        ("ticket_052.txt", "Do you offer webhooks for subscription cancellation events? We want to sync billing status with our internal CRM.", "ticket_052: technical/billing API query, low priority"),
        ("ticket_053.txt", "My card was declined during auto-renewal due to fraud alert from my bank. I cleared the alert with Chase right now. Can you manually re-try the charge on account #7712?", "ticket_053: billing payment retry request, medium/high priority"),
        ("ticket_054.txt", "We need to add 3 more Pro licenses by noon today for new hires starting their orientation. Who do we contact to process PO #99120?", "ticket_054: billing/purchase order query, time sensitive/high priority"),
        ("ticket_055.txt", "The mobile app crashes immediately upon opening after installing yesterday's v4.2.1 update on iPhone 15 Pro iOS 17.5. Retried reinstalling twice without success.", "ticket_055: concise technical crash report with version info, high priority")
    ]
    return tickets


def generate_all_samples():
    raw_dir = project_root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    api_key = Config.ANTHROPIC_API_KEY
    model = Config.ANTHROPIC_MODEL

    use_fallback = False
    client = None

    if not api_key or "your_anthropic_api_key_here" in api_key:
        print("NOTICE: ANTHROPIC_API_KEY is not set or placeholder. Using rich fallback dataset generation...")
        use_fallback = True
    else:
        client = anthropic.Anthropic(api_key=api_key)

    manifest = {}
    total_generated = 0

    if not use_fallback:
        print(f"Starting generation of 55 synthetic noisy support tickets using Anthropic API ({model})...")
        batches = [
            (1, 11, "Focus on: 1. Missing obvious fields: several tickets omitting email address, customer name, account tier, or priority level. 2. Extremes in length: at least 2 extremely short tickets (just 1 sentence/fragment), and at least 1 extremely long, rambling ticket. 3. Cover billing, technical, account, and other."),
            (12, 22, "Focus on: 1. Typos and inconsistent formatting: multiple tickets in ALL CAPS, missing punctuation, or common typos. 2. Code-switching: exactly 1 ticket in mixed English/Hindi code-switching. 3. Balanced mix of categories."),
            (23, 33, "Focus on: 1. Category ambiguity: at least 4 tickets overlapping 'billing' and 'account'. 2. Rambling customer language mixed with technical issues. 3. Implied priorities from urgent to low."),
            (34, 44, "Focus on: 1. Corporate/enterprise vs free tier tones. 2. Email forwards ('Fwd: Re: Issue') or chat logs. 3. Missing priority and vague summaries."),
            (45, 55, "Focus on: 1. Edge cases across all four categories and priorities. 2. Mixed noise profiles: typos, missing emails, slang. 3. Ensure complete coverage of diverse real-world messiness.")
        ]

        try:
            for start_idx, end_idx, batch_focus in batches:
                batch_size = end_idx - start_idx + 1
                print(f"Generating batch {start_idx} to {end_idx} ({batch_size} tickets)...")

                prompt = f"""You are generating a dataset of realistic, messy, noisy raw support ticket text samples for testing a document extraction pipeline.

Generate exactly {batch_size} ticket samples numbered from ticket_{start_idx:03d}.txt to ticket_{end_idx:03d}.txt.

{batch_focus}

IMPORTANT REQUIREMENTS:
- Each ticket must be PLAIN TEXT simulating raw customer email/chat/ticket input (DO NOT format the ticket text as structured JSON or key-value pairs unless simulating a customer filling a messy web form).
- Make the noise look authentic to real customer support desks.

Output ONLY a valid JSON array containing exactly {batch_size} objects, with no surrounding commentary. Each object must have exactly three keys:
- "filename": string, e.g. "ticket_{start_idx:03d}.txt" up to "ticket_{end_idx:03d}.txt"
- "text": string, the raw plain text of the support ticket
- "noise_note": string, a short note describing the failure modes/noise inside this sample
"""
                response = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=0.8,
                    messages=[{"role": "user", "content": prompt}],
                )

                response_text = response.content[0].text
                items = extract_json_from_text(response_text)

                for item in items:
                    filename = item["filename"]
                    text = item["text"]
                    noise_note = item["noise_note"]

                    file_path = raw_dir / filename
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(text.strip() + "\n")

                    manifest[filename] = noise_note
                    total_generated += 1

        except (anthropic.APIError, anthropic.BadRequestError, anthropic.AuthenticationError, ValueError) as e:
            print(f"\nWARNING: Anthropic API encountered an issue ({type(e).__name__}: {e}).")
            print("Falling back to rich local synthetic dataset generation to ensure 55 high-quality noisy tickets are created...")
            use_fallback = True

    if use_fallback:
        print("Generating 55 synthetic noisy support ticket text samples using fallback dataset...")
        tickets = get_fallback_synthetic_tickets()
        for filename, text, noise_note in tickets:
            file_path = raw_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text.strip() + "\n")
            manifest[filename] = noise_note
            total_generated += 1

    # Save manifest.json
    manifest_path = raw_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully generated {total_generated} ticket files and manifest.json in {raw_dir}")


if __name__ == "__main__":
    generate_all_samples()
