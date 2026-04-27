function ReflectSQLError(query: string, error: string, db_schema_hint: string) -> string {
  client Gemma_4_31b
  prompt #"
    {{ _.role("system") }}
    You are a **Senior SQL Reflector**. Your task is to analyze a failed SQL query and its corresponding error message, then provide a **highly concise, surgical hint** to fix the issue.

    <context>
      - Database Schema Hint: {{ db_schema_hint }}
      - Failed Query: {{ query }}
      - Error Message: {{ error }}
    </context>

    <instructions>
      1. Analyze the error (e.g., column not found, syntax error, type mismatch).
      2. Identify the likely correction based on the schema hint.
      3. Provide a single-sentence hint that tells the developer exactly what to change.
      4. DO NOT explain the error. DO NOT provide the full corrected query. ONLY provide the hint.
    </instructions>

    {{ _.role("user") }}
    Analyze this error and provide a surgical hint.
  "#
}
