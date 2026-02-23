import os
import base64
import requests
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, AzureChatOpenAI
import json
from datetime import datetime, timedelta
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when there is a configuration error with environment variables."""

    pass


def validate_environment(api_type: str) -> None:
    """Validate that all required environment variables are set for the specified API."""
    if api_type == "bridgeit":
        required_vars = {
            "BRIDGEIT_CLIENT_ID": os.environ.get("BRIDGEIT_CLIENT_ID"),
            "BRIDGEIT_CLIENT_SECRET": os.environ.get("BRIDGEIT_CLIENT_SECRET"),
            "BRIDGEIT_APP_KEY": os.environ.get("BRIDGEIT_APP_KEY"),
            "BRIDGEIT_BRAIN_USER_ID": os.environ.get("BRIDGEIT_BRAIN_USER_ID"),
        }
    else:  # cxai
        required_vars = {
            "OPENAI_API_BASE": os.environ.get("OPENAI_API_BASE"),
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        }

    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise ConfigurationError(
            f"Missing required environment variables for {api_type}: {', '.join(missing_vars)}"
        )


def get_azure_auth_token() -> Optional[str]:
    """Get Azure authentication token for BridgeIt with local file caching"""
    cache_file = Path("auth_token_cache.json")

    # Try to load cached token
    if cache_file.exists():
        with open(cache_file) as f:
            try:
                cache = json.load(f)
                expiration = datetime.fromisoformat(cache["expiration"])
                if datetime.now() < expiration:
                    print("Using cached token")
                    return cache["token"]
            except (json.JSONDecodeError, KeyError):
                # Invalid cache file, ignore it
                print("Invalid cache file, fetching new token")
                pass

    # Get new token if cache missing or expired
    client_id = os.environ.get("BRIDGEIT_CLIENT_ID")
    client_secret = os.environ.get("BRIDGEIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    url = "https://id.cisco.com/oauth2/default/v1/token"
    payload = "grant_type=client_credentials"
    value = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode(
        "utf-8"
    )
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {value}",
    }

    token_response = requests.request("POST", url, headers=headers, data=payload)
    if token_response.status_code == 200:
        token = token_response.json()["access_token"]
        # Cache the token with 1 hour expiration (adjust as needed)
        cache = {
            "token": token,
            "expiration": (datetime.now() + timedelta(hours=1)).isoformat(),
        }
        with open(cache_file, "w") as f:
            json.dump(cache, f)
        return token
    return None


def get_llm(
    model_name: str = "gpt-4o-mini", temperature=0
) -> ChatOpenAI | AzureChatOpenAI:
    """Initialize the LLM based on the configured API type."""
    load_dotenv()

    # Get the API type from environment variable, default to cxai if not set
    api_type = os.environ.get("CISCO_API_TYPE", "").lower()
    if api_type not in ["cxai", "bridgeit"]:
        raise ConfigurationError(
            "CISCO_API_TYPE must be either 'cxai' or 'bridgeit'. Please see the README.md for more information."
        )

    print(f"Using API type: {api_type}")

    # Validate environment variables
    validate_environment(api_type)

    if api_type == "bridgeit":
        azure_token = get_azure_auth_token()
        if not azure_token:
            raise ConfigurationError("Failed to obtain Azure authentication token")

        return AzureChatOpenAI(
            model=model_name,
            azure_endpoint="https://chat-ai.cisco.com",
            api_key=azure_token,
            temperature=temperature,
            api_version="2024-08-01-preview",
            model_kwargs={
                "user": f'{{"appkey": "{os.environ["BRIDGEIT_APP_KEY"]}", "user": "{os.environ["BRIDGEIT_BRAIN_USER_ID"]}"}}'
            },
        )
    else:  # cxai
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            base_url=os.environ["OPENAI_API_BASE"],
        )
