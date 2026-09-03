'''
Author:     Pulkit Khanna / Antigravity
License:    MIT License

LinkedIn Outreach Automation Module
Automates discovering recruiters, extracting hiring managers from job postings, and sending personalized connection notes or InMails.
'''

import os
import csv
import time
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config.search as search_cfg
from modules.helpers import print_lg, critical_error_log
from modules.cold_message_generator import ColdMessageGenerator

OUTREACH_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all excels", "sent_cold_messages.csv")
EMAIL_OUTREACH_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all excels", "recruiter_emails_to_send.csv")


def ensure_outreach_history_file() -> None:
    '''Ensure the cold outreach CSV files exist.'''
    os.makedirs(os.path.dirname(OUTREACH_HISTORY_FILE), exist_ok=True)
    if not os.path.exists(OUTREACH_HISTORY_FILE):
        with open(OUTREACH_HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Profile_URL", "Recruiter_Name", "Company", "Role_Targeted", "Type", "Status", "Message_Snippet"])

    if not os.path.exists(EMAIL_OUTREACH_FILE):
        with open(EMAIL_OUTREACH_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Recruiter_Name", "Company", "Role", "Recruiter_Email", "Subject", "Body", "Profile_URL", "Status"])


def is_recruiter_already_contacted(profile_url: str) -> bool:
    '''Check if this recruiter profile was previously contacted.'''
    if not os.path.exists(OUTREACH_HISTORY_FILE):
        return False
    norm_url = profile_url.split("?")[0].rstrip("/").lower()
    try:
        with open(OUTREACH_HISTORY_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 2 and norm_url in row[1].lower():
                    return True
    except Exception:
        pass
    return False


def log_recruiter_outreach(profile_url: str, name: str, company: str, role: str, msg_type: str, message: str, status: str = "Sent") -> None:
    '''Log outreach action to CSV.'''
    ensure_outreach_history_file()
    try:
        with open(OUTREACH_HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                profile_url,
                name,
                company,
                role,
                msg_type,
                status,
                message[:120].replace("\n", " ")
            ])
    except Exception as e:
        print_lg(f"Could not log recruiter outreach: {e}")


def log_recruiter_email(name: str, company: str, role: str, email: str, subject: str, body: str, profile_url: str, status: str = "Drafted") -> None:
    '''Log extracted recruiter email and drafted message to CSV.'''
    ensure_outreach_history_file()
    try:
        with open(EMAIL_OUTREACH_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name,
                company,
                role,
                email,
                subject,
                body.replace("\n", " \\n "),
                profile_url,
                status
            ])
        print_lg(f"💾 Logged drafted email for {name} ({email}) to 'all excels/recruiter_emails_to_send.csv'")
    except Exception as e:
        print_lg(f"Could not log recruiter email: {e}")


class LinkedInOutreach:
    '''Automates recruiter discovery, direct messaging, InMail protection, email scraping, and connection requests.'''

    def __init__(self, driver: WebDriver, message_generator: Optional[ColdMessageGenerator] = None):
        self.driver = driver
        self.generator = message_generator or ColdMessageGenerator()

    def search_recruiters(self, company: str = "", target_role: str = "Program Manager", max_results: int = 10) -> List[Dict[str, str]]:
        '''
        Search LinkedIn People for recruiters/hiring managers matching target company and role.
        '''
        query_terms = ['("Recruiter" OR "Talent Acquisition" OR "Hiring Manager" OR "Head of Talent" OR "Engineering Recruiter")']
        if company:
            query_terms.append(f'("{company}")')
        if target_role:
            query_terms.append(f'("{target_role}")')

        raw_query = " AND ".join(query_terms)
        encoded = urllib.parse.quote(raw_query)
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER"

        print_lg(f"\n[Recruiter Search]: Searching recruiters with query: {raw_query}")
        print_lg(f"Search URL: {search_url}")

        recruiters: List[Dict[str, str]] = []
        try:
            self.driver.get(search_url)
            time.sleep(4)

            # Scroll to load results
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1.5)

            cards = self.driver.find_elements(By.CSS_SELECTOR, 'li.reusable-search__result-container, div.entity-result__item')
            for card in cards[:max_results]:
                try:
                    link_elem = card.find_elements(By.CSS_SELECTOR, 'a.app-aware-link[href*="/in/"]')
                    if not link_elem:
                        continue
                    url = link_elem[0].get_attribute("href") or ""
                    url = url.split("?")[0].rstrip("/")

                    if is_recruiter_already_contacted(url):
                        print_lg(f"  ↪ Skipping already contacted recruiter: {url}")
                        continue

                    title_elem = card.find_elements(By.CSS_SELECTOR, 'span[aria-hidden="true"], a.app-aware-link span')
                    name = title_elem[0].text.strip() if title_elem else "Recruiter"

                    headline_elem = card.find_elements(By.CSS_SELECTOR, 'div.entity-result__primary-subtitle')
                    headline = headline_elem[0].text.strip() if headline_elem else ""

                    recruiters.append({
                        "name": name,
                        "url": url,
                        "headline": headline,
                        "company": company or "Target Company",
                        "target_role": target_role
                    })
                    print_lg(f"  ✨ Found Recruiter: {name} ({headline[:40]}...) -> {url}")
                except Exception:
                    continue

        except Exception as e:
            print_lg(f"Error during recruiter search: {e}")

        print_lg(f"Found {len(recruiters)} potential recruiter(s) to contact.")
        return recruiters

    def extract_job_poster_from_job(self, job_url: str) -> Optional[Dict[str, str]]:
        '''
        Visit a job page and extract the Hiring Manager / Job Poster profile if listed.
        '''
        try:
            self.driver.get(job_url)
            time.sleep(3)

            poster_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.hirer-card__hirer-information a, div.job-details-jobs-unified-top-card__hiring-team a')
            if not poster_elems:
                poster_elems = self.driver.find_elements(By.XPATH, "//h2[contains(text(), 'Meet the hiring team')]/following::a[contains(@href, '/in/')]")

            if poster_elems:
                profile_url = poster_elems[0].get_attribute("href").split("?")[0].rstrip("/")
                name_elem = poster_elems[0].find_elements(By.CSS_SELECTOR, 'span, strong')
                name = name_elem[0].text.strip() if name_elem else "Hiring Manager"

                job_title_elem = self.driver.find_elements(By.CSS_SELECTOR, 'h1.job-details-jobs-unified-top-card__job-title, h1')
                job_title = job_title_elem[0].text.strip() if job_title_elem else ""

                company_elem = self.driver.find_elements(By.CSS_SELECTOR, 'div.job-details-jobs-unified-top-card__company-name a, a.topcard__org-name-link')
                company = company_elem[0].text.strip() if company_elem else ""

                print_lg(f"  🎯 Found Job Poster for '{job_title}' at '{company}': {name} ({profile_url})")
                return {
                    "name": name,
                    "url": profile_url,
                    "company": company,
                    "job_title": job_title,
                    "target_role": job_title
                }
        except Exception as e:
            print_lg(f"Error extracting job poster: {e}")
        return None

    def extract_contact_info_email(self) -> Optional[str]:
        '''
        Open recruiter Contact Info overlay and scrape direct email address if available.
        '''
        try:
            contact_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'overlay/contact-info') or contains(@id, 'contact-info') or text()='Contact info' or contains(text(), 'Contact info')]")
            if not contact_links:
                return None

            print_lg("🔍 Checking Contact Info for direct email address...")
            contact_links[0].click()
            time.sleep(2)

            # Check inside modal
            modals = self.driver.find_elements(By.CSS_SELECTOR, 'div.artdeco-modal, div[role="dialog"]')
            if not modals:
                return None

            modal_text = modals[0].text

            # 1. Search for mailto links
            mailto_links = modals[0].find_elements(By.XPATH, ".//a[starts-with(@href, 'mailto:')]")
            if mailto_links:
                email = mailto_links[0].get_attribute("href").replace("mailto:", "").split("?")[0].strip()
                if email and "@" in email:
                    self._close_modal()
                    return email

            # 2. Regex search modal text
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', modal_text)
            self._close_modal()

            for em in emails:
                if not em.lower().endswith("linkedin.com") and not em.lower().endswith("example.com"):
                    return em.strip()

        except Exception as e:
            print_lg(f"Could not extract contact info email: {e}")
            self._close_modal()
        return None

    def _close_modal(self) -> None:
        '''Close open modal dialogs.'''
        try:
            close_buttons = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//button[contains(@aria-label, 'Dismiss') or contains(@aria-label, 'Close') or contains(@class, 'artdeco-modal__dismiss')]")
            if close_buttons:
                close_buttons[0].click()
                time.sleep(0.5)
        except Exception:
            pass

    def try_direct_message(
        self,
        recruiter_name: str,
        company: str,
        target_role: str,
        job_title: str = "",
        pause_before_send: bool = True
    ) -> Tuple[bool, str]:
        '''
        Attempt to send a direct message via the Message button.
        Protects against using paid InMail credits.
        Returns (success: bool, reason: str).
        '''
        try:
            # 1. Look for Message button on profile
            msg_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Message') or .//span[normalize-space()='Message']]")
            msg_btn = None
            for b in msg_buttons:
                if b.is_displayed():
                    msg_btn = b
                    break

            if not msg_btn:
                return False, "No Message button"

            print_lg("Clicking 'Message' button...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", msg_btn)
            time.sleep(0.5)
            msg_btn.click()
            time.sleep(2)

            # 2. Check for message popup
            message_popups = self.driver.find_elements(By.CSS_SELECTOR, 'div.msg-overlay-conversation-bubble, div.msg-convo-wrapper, form.msg-form, div[data-control-name="overlay.close"]')
            if not message_popups:
                # Also check full dialog
                message_popups = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="dialog"], div.msg-form')

            popup_text = message_popups[0].text if message_popups else self.driver.page_source

            # 3. Check for InMail credit consumption warning
            import config.settings as current_settings
            protect_credits = getattr(current_settings, "protect_inmail_credits", True)

            inmail_keywords = ["InMail credits", "Use 1 of", "Use your InMail", "InMail credit", "Use InMail credits"]
            requires_inmail = any(kw.lower() in popup_text.lower() for kw in inmail_keywords)

            if requires_inmail and protect_credits:
                print_lg("⚠️ InMail credits required for this recruiter (Found 'Use InMail credits' indicator).")
                print_lg("🛡️ Protecting your InMail credits: Closing message window to use free connection note / direct email instead.")

                # Close message overlay
                close_msg_btns = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Close message window') or contains(@data-control-name, 'overlay.close') or contains(@class, 'msg-overlay-bubble-header__control--close') or @aria-label='Dismiss']")
                if close_msg_btns:
                    close_msg_btns[0].click()
                    time.sleep(1)
                return False, "Requires InMail Credits"

            # 4. Generate AI Message & Subject
            direct_msg = self.generator.generate_direct_message(
                recruiter_name=recruiter_name,
                company=company,
                target_role=target_role,
                job_title=job_title
            )

            role_display = job_title or target_role
            subject_line = f"Application & Interest: {role_display} @ {company} - Pulkit Khanna" if company else f"Application & Interest: {role_display} - Pulkit Khanna"

            # 5. Fill Subject if Subject field exists
            subject_fields = self.driver.find_elements(By.XPATH, "//input[@placeholder='Subject (optional)' or @name='subject' or contains(@placeholder, 'Subject')]")
            if subject_fields and subject_fields[0].is_displayed():
                subject_fields[0].clear()
                subject_fields[0].send_keys(subject_line)
                print_lg(f"Entered Subject: {subject_line}")
                time.sleep(0.5)

            # 6. Fill Message Body
            text_boxes = self.driver.find_elements(By.XPATH, "//div[@role='textbox' or @aria-label='Write a message…' or contains(@class, 'msg-form__contenteditable')]")
            if not text_boxes:
                text_boxes = self.driver.find_elements(By.CSS_SELECTOR, 'div.msg-form__contenteditable p, textarea[name="message"]')

            if not text_boxes:
                print_lg("Could not find message text input area.")
                return False, "Message input area not found"

            msg_box = text_boxes[0]
            msg_box.click()
            time.sleep(0.3)
            msg_box.send_keys(direct_msg)
            print_lg(f"\n📝 [Drafted Direct Message]:\n{direct_msg}\n")
            time.sleep(1)

            # 7. Pause Before Send Review
            if pause_before_send:
                print_lg("🔔 [REVIEW PAUSE]: Review the direct message in your browser.")
                try:
                    from pyautogui import confirm
                    choice = confirm(
                        f"Send Direct Message to {recruiter_name}?\n\nSubject: {subject_line}\n\nMessage:\n{direct_msg[:300]}...\n\nClick 'Send' to dispatch or 'Cancel' to skip.",
                        "Direct Message Review",
                        ["Send", "Cancel"]
                    )
                    if choice != "Send":
                        print_lg("Direct message cancelled by user.")
                        return False, "Cancelled by user"
                except Exception:
                    input("Press Enter in terminal to confirm sending direct message...")

            # 8. Click Send Button
            send_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'msg-form__send-button') or @type='submit' or contains(@aria-label, 'Send') or .//span[normalize-space()='Send']]")
            send_btn = None
            for sb in send_buttons:
                if sb.is_displayed():
                    send_btn = sb
                    break

            if send_btn:
                send_btn.click()
                time.sleep(2)
                print_lg(f"🎉 Successfully sent Free Direct Message to {recruiter_name}!")
                return True, "Sent Free Direct Message"
            else:
                print_lg("Could not locate message Send button.")
                return False, "Send button not found"

        except Exception as e:
            print_lg(f"Direct message error: {e}")
            return False, str(e)

    def send_connection_request(
        self,
        profile_url: str,
        recruiter_name: str = "",
        company: str = "",
        target_role: str = "Program / Growth Manager",
        pause_before_send: bool = True
    ) -> bool:
        '''
        Visit recruiter profile, prioritize Free Direct Message -> Email extraction -> Connection Request with note.
        '''
        if is_recruiter_already_contacted(profile_url):
            print_lg(f"Skipping already contacted: {profile_url}")
            return False

        print_lg(f"\n{'='*65}")
        print_lg(f"🤝 Initiating Outreach for: {profile_url}")
        print_lg(f"{'='*65}")

        try:
            self.driver.get(profile_url)
            time.sleep(3)

            # Get name from profile if not provided
            if not recruiter_name:
                h1_elems = self.driver.find_elements(By.CSS_SELECTOR, 'h1.text-heading-xlarge, h1')
                if h1_elems:
                    recruiter_name = h1_elems[0].text.strip()

            headline = ""
            hl_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.text-body-medium')
            if hl_elems:
                headline = hl_elems[0].text.strip()

            print_lg(f"👤 Recruiter: {recruiter_name} | {headline[:50]}")

            # -------------------------------------------------------------
            # STEP 1: Attempt Free Direct Message (1st connection / Open Profile)
            # -------------------------------------------------------------
            dm_success, dm_reason = self.try_direct_message(
                recruiter_name=recruiter_name,
                company=company,
                target_role=target_role,
                pause_before_send=pause_before_send
            )

            if dm_success:
                log_recruiter_outreach(profile_url, recruiter_name, company, target_role, "Direct Message", "Sent direct message", "Sent")
                return True

            # -------------------------------------------------------------
            # STEP 2: Extract Recruiter's Direct Email from Contact Info
            # -------------------------------------------------------------
            import config.settings as current_settings
            if getattr(current_settings, "extract_recruiter_email", True):
                email = self.extract_contact_info_email()
                if email:
                    print_lg(f"📧 [FOUND RECRUITER EMAIL]: {recruiter_name} -> {email}")
                    subj, body = self.generator.generate_email_draft(
                        recruiter_name=recruiter_name,
                        company=company,
                        target_role=target_role
                    )
                    log_recruiter_email(recruiter_name, company, target_role, email, subj, body, profile_url, "Ready to Send")

            # -------------------------------------------------------------
            # STEP 3: Fallback to Free Connection Request with 300-char AI Note
            # -------------------------------------------------------------
            print_lg("\n🤝 Proceeding to send Connection Request with AI Note...")

            # Generate Personalized Note via Groq AI
            note = self.generator.generate_connection_note(
                recruiter_name=recruiter_name,
                recruiter_title=headline,
                company=company,
                target_role=target_role
            )
            print_lg(f"📝 [Drafted Connection Note ({len(note)}/300 chars)]:\n{note}\n")

            # Find Connect Button
            connect_btn = None
            buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Invite') or contains(@aria-label, 'Connect') or .//span[text()='Connect']]")
            for b in buttons:
                if b.is_displayed():
                    connect_btn = b
                    break

            # If not found directly, check "More" action menu
            if not connect_btn:
                more_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'More actions') or .//span[text()='More']]")
                if more_buttons and more_buttons[0].is_displayed():
                    print_lg("Checking 'More' menu for Connect button...")
                    more_buttons[0].click()
                    time.sleep(1)
                    connect_dropdown = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'artdeco-dropdown__content')]//span[text()='Connect']/ancestor::div[@role='button' or @role='menuitem' or @tabindex='0' or @role='option']")
                    if not connect_dropdown:
                        connect_dropdown = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'artdeco-dropdown__content')]//span[contains(text(), 'Connect')]")
                    if connect_dropdown:
                        connect_btn = connect_dropdown[0]

            if not connect_btn:
                print_lg("⚠️ 'Connect' button not available on this profile (might already be connected or locked).")
                log_recruiter_outreach(profile_url, recruiter_name, company, target_role, "Connection Note", note, "Skipped - No Connect Button")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", connect_btn)
            time.sleep(0.5)
            connect_btn.click()
            time.sleep(1.5)

            # Check for "Add a note" button in modal
            add_note_btn = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Add a note') or .//span[text()='Add a note']]")
            if add_note_btn:
                print_lg("Clicking 'Add a note'...")
                add_note_btn[0].click()
                time.sleep(1)

                textarea = self.driver.find_elements(By.CSS_SELECTOR, 'textarea[name="message"], textarea#custom-message')
                if textarea:
                    textarea[0].click()
                    time.sleep(0.3)
                    textarea[0].send_keys(Keys.COMMAND + "a")
                    textarea[0].send_keys(Keys.BACKSPACE)
                    textarea[0].send_keys(note)
                    time.sleep(0.5)
                    print_lg("Typed personalized note into connection request.")

            # Review Confirmation Pause
            if pause_before_send:
                print_lg("🔔 [REVIEW PAUSE]: Review the connection note in your browser.")
                try:
                    from pyautogui import confirm
                    choice = confirm(
                        f"Send connection request to {recruiter_name}?\n\nNote ({len(note)} chars):\n{note}\n\nClick 'Send' to proceed or 'Cancel' to skip.",
                        "Cold Outreach Review",
                        ["Send", "Cancel"]
                    )
                    if choice != "Send":
                        print_lg("Outreach cancelled by user.")
                        log_recruiter_outreach(profile_url, recruiter_name, company, target_role, "Connection Note", note, "Cancelled by user")
                        self._close_modal()
                        return False
                except Exception:
                    input("Press Enter in terminal to confirm sending...")

            # Click Send Button in Dialog (Multi-selector fallback for modern LinkedIn UI)
            send_btn = None
            dialog_send_selectors = [
                "//div[@role='dialog']//button[contains(@class, 'artdeco-button--primary') and not(@disabled)]",
                "//button[contains(@aria-label, 'Send now') or contains(@aria-label, 'Send invitation') or contains(@aria-label, 'Send')]",
                "//button[.//span[normalize-space()='Send'] or .//span[normalize-space()='Send invitation'] or .//span[normalize-space()='Send now']]"
            ]
            for sel in dialog_send_selectors:
                cand = self.driver.find_elements(By.XPATH, sel)
                for c in cand:
                    if c.is_displayed() and c.is_enabled():
                        send_btn = c
                        break
                if send_btn:
                    break

            if send_btn:
                send_btn.click()
                time.sleep(2)
                print_lg(f"🎉 Successfully sent connection request with note to {recruiter_name}!")
                log_recruiter_outreach(profile_url, recruiter_name, company, target_role, "Connection Note", note, "Sent")
                return True
            else:
                print_lg("Could not locate final Send button.")
                return False

        except Exception as e:
            critical_error_log(f"Error during connection outreach to {profile_url}", e)
            log_recruiter_outreach(profile_url, recruiter_name, company, target_role, "Connection Note", "", f"Error: {e}")
            return False
