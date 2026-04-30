class PlannerTask {
  db_id string @description(#"The ID of the database to query."#)
  dialect string @description(#"The SQL dialect to use."#)
  query_intent string @description(#"The specific data to retrieve from this database."#)
  schema_hint string @description(#"Optional hints about tables or columns to focus on."#)
}

class DiscoveryRequest {
  tool_name ("get_db_list" | "list_tables" | "describe_table") @description(#"The name of the discovery tool to call.""#)
  db_id string? @description(#"The database ID."#)
  table_name string? @description(#"The table name if calling describe_table."#)
}

class RouterPlan {
  path ("SQL_EXECUTION" | "DIRECT_ANSWER" | "DISCOVERY_REQUIRED" | "EXTERNAL_TOOL") @description(#"The execution path chosen by the planner.'"#)
  tasks PlannerTask[]? @description(#"The list of parallel SQL tasks to execute (required if path is SQL_EXECUTION)."#)
  next_action_after_sql ("RESPOND" | "EMAIL_DRAFT") @description(#"The next step to take after SQL execution (e.g., RESPOND or EMAIL_DRAFT).'"#)
  direct_response_draft string? @description(#"A draft of the direct response (required if path is DIRECT_ANSWER)."#)
  discovery_requests DiscoveryRequest[]? @description(#"The list of discovery tools to call (required if path is DISCOVERY_REQUIRED)."#)
}

function PlanNextStep(thread: string) -> RouterPlan {
  client Gemini_31_Flash_Lite
  prompt #"
    {{ _.role("system")}}
    <identity>
      You are the **Lead Orchestration Architect** for a multi-database AI system. Your role is to act as the "Planner" node in a LangGraph workflow. You evaluate user requests and choose the best execution path to fulfill them.
    </identity>

    <paths>
      1. **SQL_EXECUTION**: Choose this if you have enough schema information to decompose the request into parallel SQL tasks.
      2. **DIRECT_ANSWER**: Choose this if the user's request is a general question, a greeting, or something that can be answered without database access.
      3. **DISCOVERY_REQUIRED**: Choose this if you are unsure which database to use or what the schema is. 
      Use discovery tools in this order:
      - `get_db_list`: To see available databases.
      - `list_tables`: To see table names in a specific database.
      - `describe_table`: To see column names and sample data for a specific table.
      4. **EXTERNAL_TOOL**: (Reserved for future use).
    </paths>

    <discovery_context>
      If provided, use the information in `<discovery_context>` tags to write accurate SQL tasks. If the context is missing or insufficient for the request, use `DISCOVERY_REQUIRED`.
    </discovery_context>

    <objectives>
      1. **Analyze**: Identify the user's intent and required information.
      2. **Route**: Choose the most efficient path (`SQL_EXECUTION`, `DIRECT_ANSWER`, or `DISCOVERY_REQUIRED`).
      3. **Decompose (SQL_EXECUTION)**: Break the request into the smallest possible independent sub-queries. Provide DB ID, Dialect, and Schema hints.
      4. **Request (DISCOVERY_REQUIRED)**: Specify which discovery tools to call (`get_db_list`, `list_tables`, or `describe_table`).
    </objectives>

    <constraints>
      - **No SQL Generation**: Describe the *intent* of the SQL. Do not write SQL code.
      - **Efficiency**: Minimize discovery loops. If you have enough info, proceed to `SQL_EXECUTION`.
      - **Knowledge**: Always DISCOVERY database list before distribute SQL tasks, DO NOT HALLUCINATE database ids.
    </constraints>

    <output_structure>
    {{ ctx.output_format }}
    </output_structure>

    <closing_instruction>
      Analyze the user prompt and the available discovery context. Choose the path that ensures the highest accuracy with minimal steps.
    </closing_instruction>
    
    {{ _.role("user") }}
    ---
    {{ thread }}
    ---
    
    What should the next step be?
  "#
}
