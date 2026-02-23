# Bootcamp Day 2

[see main repo for all days](https://wwwin-github.cisco.com/GenAI-Bootcamp/GenAI-Bootcamp)

## Environment Setup

For the bootcamp we recommend using CX AI Playground or BridgeIT APIs. Below are the steps to set up your environment
for both options. You will set `CISCO_API_TYPE` environment variable to choose between the two APIs and this will take
care of what APIs to talk to.

Configure your environment variables in a `.env` file based on your chosen API:

### CXAI Playground

```env
CISCO_API_TYPE=cxai
OPENAI_API_BASE="https://cxai-playground.cisco.com/"
OPENAI_API_KEY=your-cxai-playground-key
```

### BridgeIT

```env
CISCO_API_TYPE=bridgeit
BRIDGEIT_CLIENT_ID=your-client-id
BRIDGEIT_CLIENT_SECRET=your-client-secret
BRIDGEIT_APP_KEY=your-app-key
BRIDGEIT_BRAIN_USER_ID=your-brain-user-id
```
For `BRIDGEIT_BRAIN_USER_ID` use your CEC ID.

## Token Caching

For BridgeIT authentication, the system implements local token caching:

- Tokens are cached in `auth_token_cache.json` (automatically gitignored)
- Cache includes the token and its expiration time
- Cached tokens are reused if still valid (1-hour expiration)
- New tokens are automatically generated when cache expires or is invalid
- To clear the cache, delete the `auth_token_cache.json` file.