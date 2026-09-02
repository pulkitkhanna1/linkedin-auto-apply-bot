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


def ensure_outreach_history_file() -> None:
    '''Ensure the cold outreach CSV file exists.'''
    os.makedirs(os.path.dirname(OUTREACH_HISTORY_FILE), exist_ok=True)
    if not os.path.exists(OUTREACH_HISTORY_FILE):
        with open(OUTREACH_HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Profile_URL", "Recruiter_Name", "Company", "Role_Targeted", "Type", "Status", "Message_Snippet"])


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


class LinkedInOutreach:
    '''Automates recruiter discovery and cold messaging.'''

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

            # Find profile cards in search results
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

                    # Extract name
                    title_elem = card.find_elements(By.CSS_SELECTOR, 'span[aria-hidden="true"], a.app-aware-link span')
                    name = title_elem[0].text.strip() if title_elem else "Recruiter"

                    # Extract headline
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

            # Look for hiring team section
            poster_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.hirer-card__hirer-information a, div.job-details-jobs-unified-top-card__hiring-team a')
            if not poster_elems:
                poster_elems = self.driver.find_elements(By.XPATH, "//h2[contains(text(), 'Meet the hiring team')]/following::a[contains(@href, '/in/')]")

            if poster_elems:
                profile_url = poster_elems[0].get_attribute("href").split("?")[0].rstrip("/")
                name_elem = poster_elems[0].find_elements(By.CSS_SELECTOR, 'span, strong')
                name = name_elem[0].text.strip() if name_elem else "Hiring Manager"

                # Extract Job title
                job_title_elem = self.driver.find_elements(By.CSS_SELECTOR, 'h1.job-details-jobs-unified-top-card__job-title, h1')
                job_title = job_title_elem[0].text.strip() if job_title_elem else ""

                # Extract Company name
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

    def send_connection_request(
        self,
        profile_url: str,
        recruiter_name: str = "",
        company: str = "",
        target_role: str = "Program / Growth Manager",
        pause_before_send: bool = True
    ) -> bool:
        '''
        Visit recruiter profile, generate personalized note, and send connection request.
        '''
        if is_recruiter_already_contacted(profile_url):
            print_lg(f"Skipping already contacted: {profile_url}")
            return False

        print_lg(f"\n{'='*60}")
        print_lg(f"Opening Profile for Outreach: {profile_url}")
        print_lg(f"{'='*60}")

        try:
            self.driver.get(profile_url)
            time.sleep(3)

            # Get name from profile if not provided
            if not recruiter_name:
                h1_elems = self.driver.find_elements(By.CSS_SELECTOR, 'h1.text-heading-xlarge, h1')
                if h1_elems:
                    recruiter_name = h1_elems[0].text.strip()

            # Get recruiter headline
            headline = ""
            hl_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div.text-body-medium')
            if hl_elems:
                headline = hl_elems[0].text.strip()

            print_lg(f"Recruiter: {recruiter_name} | {headline[:50]}")

            # 1. Generate Personalized Note via Groq AI
            note = self.generator.generate_connection_note(
                recruiter_name=recruiter_name,
                recruiter_title=headline,
                company=company,
                target_role=target_role
            )
            print_lg(f"\n📝 [Drafted Connection Note ({len(note)}/300 chars)]:\n{note}\n")

            # 2. Find Connect Button
            connect_btn = None

            # Primary action buttons
            buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Invite') or contains(@aria-label, 'Connect') or span[text()='Connect']]")
            for b in buttons:
                if b.is_displayed():
                    connect_btn = b
                    break

            # If not found directly, check "More" action menu
            if not connect_btn:
                more_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'More actions') or span[text()='More']]")
                if more_buttons and more_buttons[0].is_displayed():
                    print_lg("Checking 'More' menu for Connect button...")
                    more_buttons[0].click()
                    time.sleep(1)
                    connect_dropdown = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'artdeco-dropdown__content')]//span[text()='Connect']/ancestor::div[@role='button' or @role='menuitem' or @tabindex='0']")
                    if connect_dropdown:
                        connect_btn = connect_dropdown[0]

            if not connect_btn:
                print_lg("⚠️ 'Connect' button not available on this profile (might already be connected or locked).")
                log_recruiter_outreach(profile_url, recruiter_name, company, target_role, "Connection Note", note, "Skipped - No Connect Button")
                return False

            # Click Connect
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", connect_btn)
            time.sleep(0.5)
            connect_btn.click()
            time.sleep(1.5)

            # 3. Check for "Add a note" button in modal
            add_note_btn = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Add a note') or span[text()='Add a note']]")
            if add_note_btn:
                print_lg("Clicking 'Add a note'...")
                add_note_btn[0].click()
                time.sleep(1)

                # Find textarea for custom note
                textarea = self.driver.find_elements(By.CSS_SELECTOR, 'textarea[name="message"], textarea#custom-message')
                if textarea:
                    textarea[0].click()
                    time.sleep(0.3)
                    textarea[0].send_keys(Keys.COMMAND + "a")
                    textarea[0].send_keys(Keys.BACKSPACE)
                    textarea[0].send_keys(note)
                    time.sleep(0.5)
                    print_lg("Typed personalized note into connection request.")

            # 4. Review Confirmation Pause
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
                        # Close modal
                        close_btn = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Dismiss')]")
                        if close_btn:
                            close_btn[0].click()
                        return False
                except Exception:
                    input("Press Enter in terminal to confirm sending...")

            # 5. Click Send
            send_btn = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Send now') or contains(@aria-label, 'Send invitation') or span[text()='Send']]")
            if send_btn:
                send_btn[0].click()
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
