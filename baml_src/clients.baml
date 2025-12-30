// Learn more about clients at https://docs.boundaryml.com/docs/snippets/clients/overview

client<llm> CustomGPT4o {
  provider openai
  options {
    model "gpt-4o"
    api_key env.OPENAI_API_KEY
  }
}

client<llm> CustomGPT4oMini {
  provider openai
  retry_policy Exponential
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
  }
}

client<llm> CustomSonnet {
  provider anthropic
  options {
    model "claude-3-5-sonnet-20241022"
    api_key env.ANTHROPIC_API_KEY
  }
}


client<llm> CustomHaiku {
  provider anthropic
  retry_policy Constant
  options {
    model "claude-3-haiku-20240307"
    api_key env.ANTHROPIC_API_KEY
  }
}

client<llm> VisionModelQwen25_24b {
  provider "openai-generic"
  retry_policy Constant
  options {
    base_url "https://openrouter.ai/api/v1"
    model "qwen/qwen2.5-vl-32b-instruct"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

client<llm> Gemma327B {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "google/gemma-3-27b-it"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
    headers {
      "X-Title" "YOUR-TITLE" // Optional
  }
}}

client<llm> Gemini20FlashLite {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "google/gemini-2.0-flash-lite-001"
    api_key env.OPENROUTER_KEY_PROD
    retry_policy Constant
    temperature 0.8
    headers {
      "X-Title" "Ambarawa Book Info Retrieval" // Optional
  }
}}

client<llm> InternVL_78B {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "opengvlab/internvl3-78b"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

client<llm> THUDM_GLM_4_1V_9B_Thinking {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "thudm/glm-4.1v-9b-thinking"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

// Free models

client<llm> Grok4FastFree {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "x-ai/grok-4-fast:free"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

client<llm> MistralSmall3_24bFree {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "mistralai/mistral-small-3.2-24b-instruct:free"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

client<llm> LLama4MaverickFree {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "meta-llama/llama-4-maverick:free"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

client<llm> Qwen2532bFree {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "qwen/qwen2.5-vl-32b-instruct:free"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

client<llm> Mistral31_24bFree {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "mistralai/mistral-small-3.1-24b-instruct:free"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

client<llm> Qwen25272bFree {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "qwen/qwen2.5-vl-72b-instruct:free"
    api_key env.OPENROUTER_KEY_PROD
    temperature 0.8
  }
}

// Client with fallbacks to free models
client<llm> FreeLLMWithFallback {
  provider fallback
  options {
    strategy [Qwen2532bFree, Qwen25272bFree, VisionModelQwen25_24b]
  }
}

// https://docs.boundaryml.com/docs/snippets/clients/round-robin
client<llm> CustomFast {
  provider round-robin
  options {
    // This will alternate between the two clients
    strategy [CustomGPT4oMini, CustomHaiku]
  }
}

// https://docs.boundaryml.com/docs/snippets/clients/fallback
client<llm> OpenaiFallback {
  provider fallback
  options {
    // This will try the clients in order until one succeeds
    strategy [CustomGPT4oMini, CustomGPT4oMini]
  }
}

// https://docs.boundaryml.com/docs/snippets/clients/retry
retry_policy Constant {
  max_retries 5
  // Strategy is optional
  strategy {
    type constant_delay
    delay_ms 200
  }
}

retry_policy Exponential {
  max_retries 2
  // Strategy is optional
  strategy {
    type exponential_backoff
    delay_ms 300
    multiplier 1.5
    max_delay_ms 10000
  }
}