# AI Models API Keys Setup Guide

This guide explains how to set up API keys for all the AI models available in AI Team.

## Environment Variables

Add these environment variables to your `.env` file or system environment:

### Currently Active Models

```bash
# Anthropic (Claude)
ANTHROPIC_API_KEY=your_anthropic_key_here

# OpenAI (GPT)
OPENAI_API_KEY=your_openai_key_here

# Google (Gemini)
GOOGLE_AI_API_KEY=your_google_key_here
```

### New Models Added

```bash
# DeepSeek (Chinese AI - Very cost-effective)
DEEPSEEK_API_KEY=your_deepseek_key_here

# Perplexity (Real-time search)
PERPLEXITY_API_KEY=your_perplexity_key_here

# Grok (xAI - Elon Musk's company)
GROK_API_KEY=your_grok_key_here

# OpenRouter (Access to Llama and other open models)
OPENROUTER_API_KEY=your_openrouter_key_here

# Mistral (European AI)
MISTRAL_API_KEY=your_mistral_key_here
```

## How to Get API Keys

### DeepSeek
1. Visit: https://platform.deepseek.com/
2. Sign up for an account
3. Navigate to API Keys section
4. Create a new API key
5. **Pricing**: $0.27/1M tokens (V3), $0.55/1M tokens (R1)

### Perplexity
1. Visit: https://www.perplexity.ai/settings/api
2. Sign up for Perplexity Pro (required for API access)
3. Generate an API key
4. **Pricing**: $1/1M tokens (Sonar), $3/1M tokens (Sonar Pro)

### Grok (xAI)
1. Visit: https://x.ai/
2. Sign up for xAI API access
3. Get your API key from the dashboard
4. **Pricing**: $2/1M tokens
5. **Note**: Provides real-time access to X (Twitter) data

### OpenRouter
1. Visit: https://openrouter.ai/
2. Sign up for an account
3. Go to Keys section and create a new key
4. **Pricing**: Varies by model
   - Llama 3.3 70B: $0.18/1M tokens
   - Llama 3.1 405B: $2.70/1M tokens
5. **Note**: Access to 100+ models including Llama, Claude, GPT, and more

### Mistral
1. Visit: https://console.mistral.ai/
2. Create an account
3. Navigate to API Keys
4. Generate a new API key
5. **Pricing**: $2/1M tokens (Large), $0.20/1M tokens (Small)
6. **Note**: European-based AI with strong multilingual capabilities

## Available Models

### DeepSeek Models
- **DeepSeek V3** (`deepseek-v3`): Ultra cheap, great reasoning
- **DeepSeek R1** (`deepseek-r1`): Chain-of-thought, deep reasoning

### Perplexity Models
- **Perplexity Sonar** (`perplexity-sonar`): Real-time search, up-to-date info
- **Perplexity Sonar Pro** (`perplexity-sonar-pro`): Advanced search, best for research

### Grok Models
- **Grok 2** (`grok-2`): Latest Grok, real-time X/Twitter data
- **Grok 2 Vision** (`grok-2-vision`): Multimodal, image understanding

### Llama Models (via OpenRouter)
- **Llama 3.3 70B** (`llama-3.3-70b`): Meta's latest, open source power
- **Llama 3.1 405B** (`llama-3.1-405b`): Largest open model, top performance

### Mistral Models
- **Mistral Large** (`mistral-large`): European flagship, multilingual
- **Mistral Small** (`mistral-small`): Fast & efficient, cost-effective

## Cost Comparison

From cheapest to most expensive (per 1M tokens):

1. **Gemini 2.0 Flash**: FREE (15 req/min limit)
2. **GPT-4o Mini**: $0.15
3. **Llama 3.3 70B**: $0.18
4. **Mistral Small**: $0.20
5. **DeepSeek V3**: $0.27
6. **DeepSeek R1**: $0.55
7. **Claude Haiku 4.5**: $0.80
8. **Perplexity Sonar**: $1.00
9. **Gemini 1.5 Pro**: $1.25
10. **Grok 2**: $2.00
11. **Mistral Large**: $2.00
12. **GPT-4o**: $2.50
13. **Llama 3.1 405B**: $2.70
14. **Claude Sonnet 4.5**: $3.00
15. **Perplexity Sonar Pro**: $3.00
16. **GPT-4 Turbo**: $10.00
17. **Claude Opus 4**: $15.00

## Recommendations by Use Case

### Best for Budget (Free/Cheap):
- Gemini 2.0 Flash (FREE)
- Llama 3.3 70B ($0.18/1M)
- Mistral Small ($0.20/1M)
- DeepSeek V3 ($0.27/1M)

### Best for Coding:
- Claude Sonnet 4.5
- DeepSeek R1 (reasoning)
- GPT-4o

### Best for Research:
- Perplexity Sonar Pro (real-time search)
- Claude Opus 4 (deep reasoning)
- Grok 2 (X/Twitter data)

### Best for Multimodal (Images):
- GPT-4o
- Grok 2 Vision
- Gemini 2.0 Flash

### Best for Multilingual:
- Mistral Large
- GPT-4o
- Gemini 1.5 Pro

## Testing Your Setup

Once you've added the API keys, test each model:

1. Start the AI Team application
2. Select a new model from the model dropdown
3. Send a test message
4. If you get an error about missing API key, check your `.env` file
5. Restart the application after adding new keys

## Cost Monitoring

All models are integrated with the existing cost monitoring system:
- Daily cost tracking
- Automatic blocking of expensive models when limits reached
- Cost alerts at warning thresholds
- Per-user cost tracking in admin dashboard

## Fallback System

If a paid model fails or isn't configured, the system automatically falls back to:
- **Gemini 2.0 Flash** (free model)

This ensures uninterrupted service even if specific API keys are missing.

## Support

For issues with:
- **DeepSeek**: https://platform.deepseek.com/docs
- **Perplexity**: https://docs.perplexity.ai/
- **Grok**: https://docs.x.ai/
- **OpenRouter**: https://openrouter.ai/docs
- **Mistral**: https://docs.mistral.ai/

## Notes

- All API keys should be kept secret and never committed to version control
- Use `.env` file (which is in `.gitignore`) for local development
- For production, use environment variables in your hosting platform
- Monitor your API usage to avoid unexpected costs
- Some providers offer free trial credits for new users
