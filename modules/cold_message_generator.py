'''
Author:     Pulkit Khanna / Antigravity
License:    MIT License

Cold Message Generator Module
Generates personalized, high-converting connection notes and cold messages using Groq AI.
'''

import re
from typing import Optional
import config.personals as personals
import config.questions as questions
import config.secrets as secrets
from modules.ai.connections import create_ai_client, _msg_text
from modules.helpers import print_lg


class ColdMessageGenerator:
    '''Generates tailored cold outreach messages and connection notes.'''

    def __init__(self, ai_client=None, use_ai: bool = True):
        if not use_ai:
            self.ai_client = None
        else:
            self.ai_client = ai_client if ai_client is not None else create_ai_client()
        self.user_summary = self._build_candidate_summary()

    def _build_candidate_summary(self) -> str:
        first_name = getattr(personals, "first_name", "Pulkit")
        last_name = getattr(personals, "last_name", "Khanna")
        full_name = f"{first_name} {last_name}".strip()
        headline = getattr(questions, "linkedin_headline", "Program Manager @ Pocket FM | ex-Bain & Co | Growth Strategy & Product")
        experience = getattr(questions, "years_of_experience", "2")
        recent_employer = getattr(questions, "recent_employer", "Pocket FM")

        summary = f"""
Candidate: {full_name}
Current Role: Program Manager, US Fantasy Growth at {recent_employer}
Highlights: Scaled US vertical from $80M to $120M ARR; independently managed $1.5M+ monthly ad spend; ex-Bain & Company Analyst Intern; B.Tech from DTU (8.4/10 CGPA); Reherb.in D2C founder.
Core Skills: Program Management, Growth Strategy, Funnel Optimization, Performance Marketing, A/B Testing, SQL/Python analytics.
Total Experience: {experience} years
"""
        return summary.strip()

    def _clean_ai_output(self, text: str) -> str:
        '''Clean reasoning tags, preambles, and enclosing quotes.'''
        if not text:
            return ""
        # Remove Qwen reasoning tags if present
        text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.DOTALL).strip()
        if "<think>" in text:
            text = text.split("<think>")[0].strip()

        # Remove surrounding quotes
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()

        # Remove introductory fluff like "Here is a note:"
        text = re.sub(r'^(Here is|Here\'s|Subject:|Note:|Message:)\s*.*?\n+', '', text, flags=re.IGNORECASE)
        return text.strip()

    def generate_connection_note(
        self,
        recruiter_name: str = "",
        recruiter_title: str = "",
        company: str = "",
        target_role: str = "Program / Growth Manager",
        job_title: str = ""
    ) -> str:
        '''
        Generate a concise connection request note.
        STRICT REQUIREMENT: Must be under 300 characters (LinkedIn hard limit).
        '''
        first_name = recruiter_name.split()[0] if recruiter_name else "there"
        company_mention = f" at {company}" if company else ""
        role_mention = job_title or target_role

        if not self.ai_client:
            return self._fallback_connection_note(first_name, company, role_mention)

        system_prompt = f"""
You are an expert career strategist drafting a personalized LinkedIn Connection Request Note for Pulkit Khanna.

Candidate Context:
{self.user_summary}

CRITICAL RULES:
1. STRICT CHARACTER LIMIT: The total note MUST be 200 to 280 characters maximum (LinkedIn has a strict 300-character hard limit).
2. Tone: Professional, warm, high-signal, direct. Mention Pulkit's background (Growth/Program Manager, $80M->$120M ARR at Pocket FM / ex-Bain) and genuine interest in opportunities{company_mention}.
3. Include greeting (e.g. "Hi {first_name},") and signoff ("- Pulkit").
4. Output ONLY the raw message text. No explanations or quotes.
"""
        user_prompt = f"Write a connection note to {first_name} ({recruiter_title}{company_mention}) for {role_mention} roles."

        try:
            model = getattr(self.ai_client, "model", None)
            if model is not None:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = model.invoke(messages)
                raw_text = _msg_text(response)
                cleaned = self._clean_ai_output(raw_text)

                # Ensure strict <= 300 chars limit
                if len(cleaned) <= 300:
                    return cleaned
                else:
                    # Truncate politely if AI exceeded length
                    return cleaned[:280].rstrip() + "... - Pulkit"
        except Exception as e:
            print_lg(f"Error generating AI connection note: {e}")

        return self._fallback_connection_note(first_name, company, role_mention)

    def _fallback_connection_note(self, first_name: str, company: str, target_role: str) -> str:
        company_str = f" at {company}" if company else ""
        note = f"Hi {first_name}, I'm a Program & Growth Manager at Pocket FM (scaled vertical from $80M→$120M ARR, ex-Bain). Admiring the work{company_str} and would love to connect regarding {target_role} roles! - Pulkit"
        if len(note) > 295:
            note = f"Hi {first_name}, I'm a Program & Growth Manager (scaled $80M→$120M ARR, ex-Bain). Would love to connect regarding {target_role} opportunities{company_str}! - Pulkit"
        return note

    def generate_direct_message(
        self,
        recruiter_name: str = "",
        recruiter_title: str = "",
        company: str = "",
        target_role: str = "Program / Growth Manager",
        job_title: str = "",
        job_details: str = ""
    ) -> str:
        '''
        Generate a full personalized cold message / InMail (3-5 sentences).
        '''
        first_name = recruiter_name.split()[0] if recruiter_name else "there"
        company_mention = f" at {company}" if company else ""
        role_mention = job_title or target_role

        if not self.ai_client:
            return self._fallback_direct_message(first_name, company, role_mention)

        system_prompt = f"""
You are an expert career strategist drafting a high-converting cold InMail / message on LinkedIn for Pulkit Khanna.

Candidate Context:
{self.user_summary}

CRITICAL RULES:
1. Length: 3 to 5 concise sentences (around 80-120 words).
2. Structure:
   - Greeting: "Hi {first_name},"
   - Hook: Reach out regarding {role_mention}{company_mention}.
   - Value Proposition: Highlight scaling US Fantasy at Pocket FM from $80M to $120M ARR ($1.5M/mo ad spend) + Bain consulting rigor & DTU engineering background.
   - Call to Action: Brief 10-minute chat or open to sharing resume.
   - Sign-off: "Best regards,\nPulkit Khanna\n+91 7042680055 | linkedin.com/in/pulkit-khanna"
3. Output ONLY the raw message. No subject line prefixes, no explanations.
"""
        user_prompt = f"Draft a cold message to {first_name} ({recruiter_title}{company_mention}) expressing interest in {role_mention} opportunities."

        try:
            model = getattr(self.ai_client, "model", None)
            if model is not None:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = model.invoke(messages)
                raw_text = _msg_text(response)
                return self._clean_ai_output(raw_text)
        except Exception as e:
            print_lg(f"Error generating AI direct message: {e}")

        return self._fallback_direct_message(first_name, company, role_mention)

    def _fallback_direct_message(self, first_name: str, company: str, target_role: str) -> str:
        company_str = f" at {company}" if company else ""
        return f"""Hi {first_name},

I hope you're having a great week. I'm reaching out to express my strong interest in {target_role} opportunities{company_str}.

Currently, I serve as a Program Manager at Pocket FM, where I scaled our U.S. vertical from $80M to $120M ARR while independently managing $1.5M+ in monthly ad spend. Prior to this, I worked at Bain & Company as an Analyst Intern conducting strategic CEO diagnostic frameworks.

Given my background in data-driven growth funnels and cross-functional leadership, I'd love to connect and explore how I could contribute to your team. Would you be open to a brief conversation or reviewing my resume?

Best regards,
Pulkit Khanna
+91 7042680055 | https://www.linkedin.com/in/pulkit-khanna"""
