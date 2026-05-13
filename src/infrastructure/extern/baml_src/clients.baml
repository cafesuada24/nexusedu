// Learn more about clients at https://docs.boundaryml.com/docs/snippets/clients/overview

retry_policy Constant {
  max_retries 3
  strategy {
    type constant_delay
    delay_ms 200
  }
}

retry_policy Exponential {
  max_retries 3
  strategy {
    type exponential_backoff
    delay_ms 300
    multiplier 1.5
    max_delay_ms 10000
  }
}
// Example Google AI client (uncomment to use)
client<llm> Gemini_31_Flash_Lite {
  provider google-ai
  retry_policy Exponential
  options {
    model "gemini-3.1-flash-lite-preview"
    api_key env.GOOGLE_API_KEY
  }
}

client<llm> Gemini_31_Flash_Lite_Health {
  provider google-ai
  retry_policy Exponential
  options {
    model "gemini-3.1-flash-lite-preview"
    api_key env.GOOGLE_API_KEY
    generationConfig {
      maxOutputTokens 1024
    }
  }
}

// Example Google AI client (uncomment to use)
client<llm> Gemma_4_31b {
  provider google-ai
  retry_policy Exponential
  options {
    model "gemma-4-31b-it"
    api_key env.GOOGLE_API_KEY
  }
}

// Example AWS Bedrock client (uncomment to use)
// client<llm> CustomBedrock {
//   provider aws-bedrock
//   options {
//     model "anthropic.claude-sonnet-4-20250514-v1:0"
//     region "us-east-1"
//     // AWS credentials are auto-detected from env vars
//   }
// }

// Example Azure OpenAI client (uncomment to use)
// client<llm> CustomAzure {
//   provider azure-openai
//   options {
//     model "gpt-5"
//     api_key env.AZURE_OPENAI_API_KEY
//     base_url "https://MY_RESOURCE_NAME.openai.azure.com/openai/deployments/MY_DEPLOYMENT_ID"
//     api_version "2024-10-01-preview"
//   }
// }

// Example Vertex AI client (uncomment to use)
// client<llm> CustomVertex {
//   provider vertex-ai
//   options {
//     model "gemini-2.5-pro"
//     location "us-central1"
//     // Uses Google Cloud Application Default Credentials
//   }
// }

// Example Ollama client for local models (uncomment to use)
// client<llm> CustomOllama {
//   provider openai-generic
//   options {
//     base_url "http://localhost:11434/v1"
//     model "llama4"
//     default_role "user" // Most local models prefer the user role
//     // No API key needed for local Ollama
//   }
// }

// https://docs.boundaryml.com/docs/snippets/clients/round-robin
// client<llm> CustomFast {
//  provider round-robin
//  options {
//    // This will alternate between the two clients
//    strategy [CustomGPT5Mini, CustomHaiku]
//  }
// }

// https://docs.boundaryml.com/docs/snippets/clients/retry
