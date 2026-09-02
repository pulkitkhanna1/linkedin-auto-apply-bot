'''
Author:     Pulkit Khanna / Antigravity
License:    MIT License

Google Forms Auto-Filler Module
Automates parsing, answering (via Deterministic Rules & Groq AI), and submitting Google Forms.
'''

import os
import re
import csv
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

import config.personals as personals
import config.questions as questions
import config.secrets as secrets
from modules.helpers import print_lg, critical_error_log
from modules.ai.connections import create_ai_client, _msg_text

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "all excels", "applied_google_forms.csv")


def ensure_history_file() -> None:
    '''Ensure the applied Google Forms history CSV file exists.'''
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Form_URL", "Form_Title", "Status", "Notes"])


def is_form_already_applied(url: str) -> bool:
    '''Check if this Google Form was previously submitted.'''
    if not os.path.exists(HISTORY_FILE):
        return False
    clean_url = url.split("?")[0].strip().lower()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 2 and clean_url in row[1].lower():
                    return True
    except Exception:
        pass
    return False


def log_form_application(url: str, title: str, status: str = "Applied", notes: str = "") -> None:
    '''Record form submission in CSV history.'''
    ensure_history_file()
    try:
        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url,
                title,
                status,
                notes
            ])
    except Exception as e:
        print_lg(f"Could not log form application: {e}")


class GoogleFormFiller:
    '''Automates filling and submitting Google Forms with rule-based + Groq AI fallback.'''

    def __init__(self, driver: WebDriver, ai_client=None):
        self.driver = driver
        self.ai_client = ai_client or create_ai_client()
        self.user_profile = self._build_user_profile_context()

    def _build_user_profile_context(self) -> str:
        '''Build comprehensive user profile context for AI prompting.'''
        first_name = getattr(personals, "first_name", "Pulkit")
        last_name = getattr(personals, "last_name", "Khanna")
        full_name = f"{first_name} {last_name}".strip()
        phone = getattr(personals, "phone_number", "7042680055")
        city = getattr(personals, "current_city", "New Delhi")
        state = getattr(personals, "state", "Delhi")
        country = getattr(personals, "country", "India")
        email = getattr(secrets, "username", "pulkitkhanna1@gmail.com")
        linkedin = getattr(questions, "linkedIn", "https://www.linkedin.com/in/pulkit-khanna")
        website = getattr(questions, "website", "https://github.com/pulkitkhanna1")
        headline = getattr(questions, "linkedin_headline", "Program Manager @ Pocket FM | ex-Bain & Co | Growth Strategy & Product")
        experience_years = getattr(questions, "years_of_experience", "2")
        current_ctc = getattr(questions, "current_ctc", 1800000)
        desired_salary = getattr(questions, "desired_salary", 2500000)
        notice_period = getattr(questions, "notice_period", 30)
        recent_employer = getattr(questions, "recent_employer", "Pocket FM")
        user_info = getattr(questions, "user_information_all", "")

        context = f"""
Candidate Name: {full_name}
First Name: {first_name}
Last Name: {last_name}
Email: {email}
Phone: {phone} / +91 {phone}
Location: {city}, {state}, {country}
LinkedIn: {linkedin}
GitHub / Portfolio: {website}
Professional Headline: {headline}
Total Experience: {experience_years} years
Current CTC / Salary: {current_ctc} (approx 18 LPA INR)
Expected CTC / Salary: {desired_salary} (approx 25 LPA INR)
Notice Period: {notice_period} days (available in 15-30 days)
Current / Most Recent Employer: {recent_employer}
Education: B.Tech in Production Engineering, Delhi Technological University (DTU), 2021-2025, CGPA 8.40/10; Sardar Patel Vidyalaya (CBSE Class XII 93.6%)
Detailed Experience & Skills:
{user_info}
"""
        return context.strip()

    def get_deterministic_answer(self, question_text: str) -> Optional[str]:
        '''Match standard questions against saved profile details.'''
        q = question_text.lower().strip()

        first_name = getattr(personals, "first_name", "Pulkit")
        last_name = getattr(personals, "last_name", "Khanna")
        full_name = f"{first_name} {last_name}".strip()
        phone = getattr(personals, "phone_number", "7042680055")
        city = getattr(personals, "current_city", "New Delhi")
        state = getattr(personals, "state", "Delhi")
        country = getattr(personals, "country", "India")
        email = getattr(secrets, "username", "pulkitkhanna1@gmail.com")
        linkedin = getattr(questions, "linkedIn", "https://www.linkedin.com/in/pulkit-khanna")
        website = getattr(questions, "website", "https://github.com/pulkitkhanna1")
        headline = getattr(questions, "linkedin_headline", "")
        experience_years = str(getattr(questions, "years_of_experience", "2"))
        current_ctc = getattr(questions, "current_ctc", 1800000)
        desired_salary = getattr(questions, "desired_salary", 2500000)
        notice_period = str(getattr(questions, "notice_period", 30))
        recent_employer = getattr(questions, "recent_employer", "Pocket FM")

        # Name checks
        if re.search(r'\b(full\s*name|your\s*name|candidate\s*name|applicant\s*name)\b', q) or q in ["name", "name *", "full name *"]:
            return full_name
        if re.search(r'\b(first\s*name)\b', q):
            return first_name
        if re.search(r'\b(last\s*name|surname)\b', q):
            return last_name

        # Contact checks
        if re.search(r'\b(email|email\s*address|mail\s*id)\b', q):
            return email
        if re.search(r'\b(phone|mobile|contact|whatsapp|phone\s*number|mobile\s*number)\b', q):
            return phone

        # Social / Portfolio
        if re.search(r'\b(linkedin|linkedin\s*url|linkedin\s*profile|linkedin\s*link)\b', q):
            return linkedin
        if re.search(r'\b(github|portfolio|website|personal\s*website|work\s*samples)\b', q):
            return website

        # Location
        if re.search(r'\b(current\s*city|city|current\s*location|residence|where\s*are\s*you\s*located|current\s*address)\b', q):
            return f"{city}, {country}" if "country" in q else city

        # Experience & Companies
        if re.search(r'\b(years\s*of\s*experience|total\s*experience|relevant\s*experience|work\s*experience\s*in\s*years)\b', q):
            return experience_years
        if re.search(r'\b(current\s*company|current\s*organization|current\s*employer|present\s*company|last\s*company)\b', q):
            return recent_employer
        if re.search(r'\b(current\s*designation|current\s*role|current\s*job\s*title|designation)\b', q):
            return "Program Manager, US Fantasy Growth"
        if re.search(r'\b(college|university|institute|alma\s*mater)\b', q):
            return "Delhi Technological University (DTU)"
        if re.search(r'\b(degree|graduation|qualification|highest\s*qualification)\b', q):
            return "B.Tech in Production Engineering (DTU)"

        # CTC & Salaries
        if re.search(r'\b(current\s*ctc|current\s*salary|present\s*ctc|present\s*salary)\b', q):
            if "lakh" in q or "lpa" in q:
                return f"{current_ctc / 100000:.1f}"
            return str(current_ctc)
        if re.search(r'\b(expected\s*ctc|expected\s*salary|desired\s*ctc|desired\s*salary|salary\s*expectation)\b', q):
            if "lakh" in q or "lpa" in q:
                return f"{desired_salary / 100000:.1f}"
            return str(desired_salary)

        # Notice Period
        if re.search(r'\b(notice\s*period|how\s*soon\s*can\s*you\s*join|joining\s*time|availability)\b', q):
            if "month" in q:
                return "1"
            if "week" in q:
                return "4"
            if "day" in q:
                return notice_period
            return f"{notice_period} days"

        return None

    def ask_ai(self, question_text: str, options: Optional[List[str]] = None, is_multiline: bool = False) -> str:
        '''Generate answer using Groq AI client.'''
        if not self.ai_client:
            return ""

        options_prompt = ""
        if options:
            options_prompt = f"\nAvailable Options (You MUST choose the single best option or comma-separated options from this list):\n" + "\n".join(f"- {opt}" for opt in options)

        system_instruction = f"""
You are an intelligent job application assistant filling out a job application / Google Form on behalf of Pulkit Khanna.

User Profile:
{self.user_profile}

Rules:
1. Answer strictly based on the candidate's background. If answering an open-ended question (e.g. why should we hire you, project descriptions, skills), write a concise, compelling, professional response (2-4 sentences unless specified).
2. If given a list of options, return ONLY the exact text of the best matching option from the list.
3. Do NOT include greetings, preamble, quotes, or markdown explanations. Output only the direct answer text.
"""
        user_prompt = f"Question: {question_text}{options_prompt}\n\nProvide the exact answer:"

        try:
            model = getattr(self.ai_client, "model", None)
            if model is not None:
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ]
                response = model.invoke(messages)
                answer = _msg_text(response).strip()
                # Clean up thinking tags if present in Qwen output
                if "<think>" in answer and "</think>" in answer:
                    answer = answer.split("</think>")[-1].strip()
                return answer
        except Exception as e:
            print_lg(f"AI answer generation error: {e}")

        return ""

    def process_and_fill_page(self) -> int:
        '''Find all questions on the current Google Form page and answer them.'''
        # Find all question blocks in Google Form
        # Google forms usually group questions in div with class .geS5n or .Qr7Oae or role="listitem"
        question_containers = self.driver.find_elements(By.CSS_SELECTOR, 'div.geS5n, div.Qr7Oae, div[role="listitem"]')
        if not question_containers:
            # Fallback to general container search
            question_containers = self.driver.find_elements(By.CSS_SELECTOR, 'div[jsmodel="CP1oW"]')

        filled_count = 0

        for container in question_containers:
            try:
                # Extract question label / header
                header_elems = container.find_elements(By.CSS_SELECTOR, 'div[role="heading"], span.M7eMe, div.HoXoMd')
                if not header_elems:
                    continue
                question_text = header_elems[0].text.strip()
                if not question_text:
                    continue

                # Clean question text (remove required star symbol *)
                clean_question = re.sub(r'[\*\n\r]+', ' ', question_text).strip()
                print_lg(f"\n[Form Question]: {clean_question}")

                # 1. Check for single-line text inputs
                text_inputs = container.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="email"], input[type="tel"], input[type="url"], input[type="number"], input.whsOnd')
                if text_inputs:
                    inp = text_inputs[0]
                    # Check if already filled
                    existing_val = inp.get_attribute("value")
                    if existing_val and len(existing_val.strip()) > 0:
                        print_lg(f"  -> Already filled: '{existing_val}'")
                        filled_count += 1
                        continue

                    answer = self.get_deterministic_answer(clean_question)
                    if not answer:
                        answer = self.ask_ai(clean_question, is_multiline=False)

                    if answer:
                        print_lg(f"  -> Typing answer: {answer}")
                        inp.click()
                        time.sleep(0.3)
                        inp.send_keys(Keys.COMMAND + "a")
                        inp.send_keys(Keys.BACKSPACE)
                        inp.send_keys(answer)
                        filled_count += 1
                        time.sleep(0.4)
                    continue

                # 2. Check for multiline textareas
                textareas = container.find_elements(By.CSS_SELECTOR, 'textarea.KHxj8b, textarea')
                if textareas:
                    ta = textareas[0]
                    existing_val = ta.get_attribute("value")
                    if existing_val and len(existing_val.strip()) > 0:
                        print_lg(f"  -> Already filled: '{existing_val[:30]}...'")
                        filled_count += 1
                        continue

                    answer = self.get_deterministic_answer(clean_question)
                    if not answer:
                        answer = self.ask_ai(clean_question, is_multiline=True)

                    if answer:
                        print_lg(f"  -> Typing textarea answer: {answer[:60]}...")
                        ta.click()
                        time.sleep(0.3)
                        ta.send_keys(Keys.COMMAND + "a")
                        ta.send_keys(Keys.BACKSPACE)
                        ta.send_keys(answer)
                        filled_count += 1
                        time.sleep(0.4)
                    continue

                # 3. Check for Radio buttons (Single Choice)
                radios = container.find_elements(By.CSS_SELECTOR, 'div[role="radio"]')
                if radios:
                    options = []
                    for r in radios:
                        opt_label = r.get_attribute("aria-label") or r.get_attribute("data-value") or r.text
                        if opt_label:
                            options.append(opt_label.strip())

                    print_lg(f"  -> Radio options found: {options}")
                    # Pick best option
                    selected_opt = self.get_deterministic_answer(clean_question)
                    matched_radio = None

                    if selected_opt:
                        for idx, opt_text in enumerate(options):
                            if selected_opt.lower() in opt_text.lower() or opt_text.lower() in selected_opt.lower():
                                matched_radio = radios[idx]
                                break

                    if not matched_radio and options:
                        ai_choice = self.ask_ai(clean_question, options=options)
                        print_lg(f"  -> AI picked radio option: {ai_choice}")
                        for idx, opt_text in enumerate(options):
                            if ai_choice.lower() in opt_text.lower() or opt_text.lower() in ai_choice.lower():
                                matched_radio = radios[idx]
                                break

                    if matched_radio:
                        # Scroll into view and click
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", matched_radio)
                        time.sleep(0.3)
                        matched_radio.click()
                        print_lg("  -> Clicked radio option successfully.")
                        filled_count += 1
                    continue

                # 4. Check for Checkboxes (Multiple Choice)
                checkboxes = container.find_elements(By.CSS_SELECTOR, 'div[role="checkbox"]')
                if checkboxes:
                    options = []
                    for cb in checkboxes:
                        opt_label = cb.get_attribute("aria-label") or cb.get_attribute("data-value") or cb.text
                        if opt_label:
                            options.append(opt_label.strip())

                    print_lg(f"  -> Checkbox options found: {options}")
                    ai_choices_str = self.ask_ai(clean_question, options=options)
                    print_lg(f"  -> AI selected: {ai_choices_str}")

                    for idx, opt_text in enumerate(options):
                        if opt_text.lower() in ai_choices_str.lower():
                            cb_elem = checkboxes[idx]
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cb_elem)
                            time.sleep(0.3)
                            cb_elem.click()
                            print_lg(f"  -> Checked: {opt_text}")
                            filled_count += 1
                    continue

                # 5. Check for Dropdowns (Listbox)
                listboxes = container.find_elements(By.CSS_SELECTOR, 'div[role="listbox"]')
                if listboxes:
                    lb = listboxes[0]
                    lb.click()
                    time.sleep(0.5)
                    options_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="option"]')
                    opt_texts = [o.text.strip() for o in options_elems if o.text.strip() and o.text.strip() != "Choose"]
                    if opt_texts:
                        chosen_opt = self.get_deterministic_answer(clean_question) or self.ask_ai(clean_question, options=opt_texts)
                        for o_elem in options_elems:
                            if chosen_opt.lower() in o_elem.text.lower():
                                o_elem.click()
                                print_lg(f"  -> Selected dropdown option: {o_elem.text}")
                                filled_count += 1
                                break
                    time.sleep(0.3)
                    continue

            except Exception as e:
                print_lg(f"Error processing question container: {e}")

        return filled_count

    def apply_to_form(self, form_url: str, pause_before_submit: bool = True) -> bool:
        '''Open a Google Form URL, fill all pages, and submit.'''
        print_lg(f"\n{'='*60}")
        print_lg(f"Opening Google Form: {form_url}")
        print_lg(f"{'='*60}")

        try:
            self.driver.get(form_url)
            time.sleep(3)

            # Check if form requires sign in or is closed
            page_text = self.driver.page_source.lower()
            if "no longer accepting responses" in page_text:
                print_lg("❌ This Google Form is no longer accepting responses.")
                log_form_application(form_url, "Closed Form", "Skipped", "Form closed")
                return False

            form_title = self.driver.title or "Google Form"
            h_elems = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="heading"], div.F5R11d')
            if h_elems:
                form_title = h_elems[0].text.strip() or form_title

            print_lg(f"Form Title: {form_title}")

            page_number = 1
            max_pages = 8

            while page_number <= max_pages:
                print_lg(f"\n--- Processing Page {page_number} ---")
                time.sleep(1.5)
                filled = self.process_and_fill_page()
                print_lg(f"Filled {filled} fields on page {page_number}.")

                # Check if there is a 'Next' button
                next_buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[translate(text(), 'NEXT', 'next')='next' or translate(text(), 'SUIVANT', 'suivant')='suivant' or translate(text(), 'SIGUIENTE', 'siguiente')]/ancestor::div[@role='button']")
                if not next_buttons:
                    next_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="button"][jsname="OCpkoe"]')

                # Check for 'Submit' button
                submit_buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[translate(text(), 'SUBMIT', 'submit')='submit' or translate(text(), 'SOUMETTRE', 'soumettre')='soumettre' or translate(text(), 'ENVIAR', 'enviar')]/ancestor::div[@role='button']")
                if not submit_buttons:
                    submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="button"][jsname="M2vTWe"]')

                if next_buttons and not submit_buttons:
                    print_lg("Clicking 'Next' button to proceed to the next page...")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_buttons[0])
                    time.sleep(0.5)
                    next_buttons[0].click()
                    page_number += 1
                    time.sleep(2)
                    continue

                if submit_buttons:
                    print_lg("\n✅ Final submission screen reached!")
                    if pause_before_submit:
                        print_lg("🔔 [REVIEW PAUSE]: Form is filled! Please review the Chrome window.")
                        try:
                            from pyautogui import confirm
                            res = confirm(
                                f"Review the filled Google Form in your browser:\n\nTitle: {form_title}\n\nClick 'Submit Form' to submit or 'Cancel' to skip.",
                                "Google Form Review",
                                ["Submit Form", "Cancel"]
                            )
                            if res != "Submit Form":
                                print_lg("Submission cancelled by user.")
                                log_form_application(form_url, form_title, "Cancelled", "Cancelled during review")
                                return False
                        except Exception:
                            input("Press Enter in terminal to confirm submission...")

                    print_lg("Submitting Google Form...")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_buttons[0])
                    time.sleep(0.5)
                    submit_buttons[0].click()
                    time.sleep(3)

                    # Verify confirmation
                    print_lg(f"🎉 Successfully submitted Google Form: {form_title}")
                    log_form_application(form_url, form_title, "Applied", "Auto-submitted")
                    return True

                # If no next or submit button was detected, break
                print_lg("No further Next/Submit buttons found on page.")
                break

            return False

        except Exception as e:
            critical_error_log(f"Error while processing Google Form {form_url}", e)
            log_form_application(form_url, "Unknown Form", "Failed", str(e))
            return False
