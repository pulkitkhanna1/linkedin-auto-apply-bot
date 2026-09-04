'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (c) 2024-2026 Sai Vignesh Golla

License:    MIT License
            https://opensource.org/license/mit
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

version:    24.12.3.10.30
'''


###################################################### CONFIGURE YOUR TOOLS HERE ######################################################


# Login Credentials for LinkedIn (Optional)
username = "pulkitkhanna1@gmail.com"    # Enter your username in the quotes
password = ""                           # Enter your password in the quotes (or leave empty to login in browser)


## Artificial Intelligence (optional)
# Master switch. Turn AI on to let the tool draft answers to application questions
# and pull the required skills out of job descriptions. It needs either a paid API
# key or a local model server, so it stays off by default.
use_AI = True                            # True or False (case-sensitive)

# Which AI service to use. The tool reaches all of them through LangChain, so this
# one setting is usually all you change:
#   "openai" - OpenAI, or ANY OpenAI-compatible server (Groq, Ollama, LM Studio, DeepSeek, vLLM, ...)
#   "gemini" - Google Gemini (uses your Google API key; llm_api_url is ignored).
ai_provider = "openai"                    # "openai", "gemini", or "deepseek"

# The model name to use. Type whatever your provider offers, for example:
#   Groq:    "qwen/qwen3.6-27b", "openai/gpt-oss-120b"
#   OpenAI:  "gpt-4o-mini", "gpt-4o"
llm_model = "qwen/qwen3.6-27b"

# Your API key.
llm_api_key = "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"

# Base URL of your AI server. Only used by the "openai" provider family.
#   Groq:      "https://api.groq.com/openai/v1"
#   OpenAI:    "https://api.openai.com/v1/"
llm_api_url = "https://api.groq.com/openai/v1"

# Sampling temperature. Leave as None to use the model's own default.
llm_temperature = 0.2




# --- Load user settings saved by the local control panel (user_config.json).
# --- No-op if that file is absent: values fall back to the defaults above.
from config import _overrides as _o
_o.apply(__name__, globals())
############################################################################################################