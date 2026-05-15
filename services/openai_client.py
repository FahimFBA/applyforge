"""
services/openai_client.py
=========================
Reusable OpenAI chat-completion client for the applyforge project.

Design decisions
----------------
* Uses the official ``openai`` Python SDK (v1+).
* Wraps every call in a retry loop with exponential backoff to handle transient
  rate-limit and network errors without crashing the entire run.
* Never sends raw PDF bytes — only compact optimized resume profiles are passed
  as context to keep token usage and cost low.
* Model and temperature are read from Config so they can be changed via env vars
  without touching this file.

Usage
-----
    from services.openai_client import OpenAIClient
    from services.config import get_config

    client = OpenAIClient(get_config())
    text = client.generate(system_prompt="You are ...", user_prompt="Write ...")
"""
from __future__ import annotations
from openai import OpenAI, APIConnectionError, APIError, RateLimitError
from services.config import Config
from services.logger import setup_logger
from typing import Optional
import time

logger = setup_logger(__name__)


class OpenAIClient:
    """
    Thin wrapper around the OpenAI chat-completions endpoint.

    All generation goes through ``generate()`` so retry logic, logging, and
    model/temperature defaults are applied consistently across the project.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialise the client.

        Parameters
        ----------
        config:
            Project config - reads openai_api_key, openai_model, openai_temperature,
            and openai_retries from here.
        """
        self.config = config
        # The SDK reads OPENAI_API_KEY from the environment by default, but we
        # pass it explicitly so the source is always obvious.
        self._client = OpenAI(api_key=config.openai_api_key)

    def generate(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None,
                 max_tokens: int = 2000) -> str:
        """
        Send a chat-completion request and return the assistant's reply.

        Retries on rate-limit (longer wait) and generic API errors (exponential
        backoff).  Raises after exhausting all retry attempts.

        Parameters
        ----------
        system_prompt:
            Instruction prompt that defines the assistant's persona and task.
        user_prompt:
            The actual content / request — resume profile + job description.
        temperature:
            Override the config default for this specific call.
            Lower values (0.2–0.4) → more deterministic output.
            Higher values (0.7–0.9) → more creative output.
        max_tokens:
            Hard ceiling on response length.  Tune per call site to control cost.

        Returns
        -------
        str
            The trimmed text content of the first choice.

        Raises
        ------
        RuntimeError
            If all retry attempts are exhausted.
        """
        temp = temperature if temperature is not None else self.config.openai_temperature
        retries = self.config.openai_retries

        for attempt in range(retries):
            try:
                response = self._client.chat.completions.create(
                    model=self.config.openai_model,
                    temperature=temp,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )

                content = response.choices[0].message.content or ""
                content = content.strip()

                # Log token usage to help monitor cost
                if response.usage:
                    logger.debug(
                        f"Tokens used - prompt: {response.usage.prompt_tokens}, "
                        f"completion: {response.usage.completion_tokens}, "
                        f"total: {response.usage.total_tokens}"
                    )

                return content

            except RateLimitError as exc:
                # Rate-limit errors need a longer pause than generic errors
                wait = 15 * (attempt + 1)
                logger.warning(
                    f"OpenAI rate limit hit (attempt {attempt + 1}/{retries}), "
                    f"waiting {wait}s: {exc}"
                )
                time.sleep(wait)

            except (APIError, APIConnectionError) as exc:
                if attempt < retries - 1:
                    wait = 2 ** attempt  # 1 s, 2 s, 4 s
                    logger.warning(
                        f"OpenAI API error (attempt {attempt + 1}/{retries}), "
                        f"retrying in {wait}s: {exc}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"OpenAI API call failed after {retries} attempts: {exc}"
                    )
                    raise

        raise RuntimeError(
            f"OpenAI generation failed after {retries} attempts — "
            "check API key, model name, and network connectivity"
        )
